import io
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from ModelFinderV2_6.comfyui_launcher_service import ComfyUILauncherService
from ModelFinderV2_6.comfyui_manager_api_service import ComfyUIManagerApiService
from ModelFinderV2_6.comfyui_runtime_api_service import ComfyUIRuntimeApiService
from ModelFinderV2_6.dependency_environment_service import DependencyEnvironmentService
from ModelFinderV2_6.dependency_install_planner import DependencyInstallPlanner
from ModelFinderV2_6.dependency_preflight_service import DependencyPreflightService
from ModelFinderV2_6.dependency_rule_service import DependencyRuleService
from ModelFinderV2_6.irregular_mapping_service import IrregularMappingService
from ModelFinderV2_6.missing_node_install_orchestrator import MissingNodeInstallOrchestrator
from ModelFinderV2_6.model_config_service import ModelConfigService
from ModelFinderV2_6.operation_result import OperationResult
from ModelFinderV2_6.plugin_repair_service import PluginRepairService
from ModelFinderV2_6.workflow_missing_node_service import WorkflowMissingNodeService


pytestmark = pytest.mark.unit


class _DummyIrregularNamesModel:
    def __init__(self, *, add_result=True, update_result=True, delete_result=True):
        self.add_result = add_result
        self.update_result = update_result
        self.delete_result = delete_result
        self.mappings = [{"id": "1", "original_name": "foo", "corrected_name": "bar", "notes": ""}]
        self.calls = []

    def get_all_mappings(self):
        return list(self.mappings)

    def add_mapping(self, original_name, corrected_name, notes):
        self.calls.append(("add", original_name, corrected_name, notes))
        return self.add_result

    def update_mapping(self, mapping_id, original_name, corrected_name, notes):
        self.calls.append(("update", mapping_id, original_name, corrected_name, notes))
        return self.update_result

    def delete_mapping(self, mapping_id):
        self.calls.append(("delete", mapping_id))
        return self.delete_result


class _DummyConfigManager:
    def __init__(self):
        self.node_types = ["CheckpointLoaderSimple"]
        self.node_indices = {"default": [0], "CheckpointLoaderSimple": [0, 1]}
        self.extensions = [".safetensors"]
        self.calls = []

    def get_model_node_types(self):
        return list(self.node_types)

    def get_node_model_indices(self):
        return dict(self.node_indices)

    def get_model_extensions(self):
        return list(self.extensions)

    def add_model_node_type(self, node_type):
        self.calls.append(("add_model_node_type", node_type))
        return True

    def remove_model_node_type(self, node_type):
        self.calls.append(("remove_model_node_type", node_type))
        return True

    def add_node_model_index(self, node_type, indices):
        self.calls.append(("add_node_model_index", node_type, indices))
        return True

    def remove_node_model_index(self, node_type, index=None):
        self.calls.append(("remove_node_model_index", node_type, index))
        return True

    def add_model_extension(self, extension):
        self.calls.append(("add_model_extension", extension))
        return True

    def remove_model_extension(self, extension):
        self.calls.append(("remove_model_extension", extension))
        return True


class _DummyPluginRepairModel:
    def __init__(self, *, plugins=None, need_repair=None):
        self.plugins = plugins or []
        self.need_repair = need_repair or []
        self.checked_paths = []

    def get_all_plugins(self):
        return list(self.plugins)

    def check_plugin_status(self, comfyui_path):
        self.checked_paths.append(comfyui_path)
        return list(self.need_repair)


class _FakeProcess:
    def __init__(self, *, pid=1234, stdout_text="", poll_result=None):
        self.pid = pid
        self.stdout = io.StringIO(stdout_text)
        self._poll_result = poll_result
        self.terminated = False
        self.killed = False
        self.wait_calls = []

    def poll(self):
        return self._poll_result

    def terminate(self):
        self.terminated = True
        self._poll_result = 0

    def kill(self):
        self.killed = True
        self._poll_result = -9

    def wait(self, timeout=None):
        self.wait_calls.append(timeout)
        return self._poll_result


def test_irregular_mapping_service_returns_operation_results() -> None:
    model = _DummyIrregularNamesModel()
    service = IrregularMappingService(model)

    result = service.list_mappings()

    assert result.success
    assert result.code == "mappings_loaded"
    assert result.data == model.mappings
    assert service.add_mapping("foo", "bar", "note").code == "mapping_added"
    assert service.update_mapping("1", "foo", "baz", "").code == "mapping_updated"
    assert service.delete_mapping("1").code == "mapping_deleted"
    assert model.calls == [
        ("add", "foo", "bar", "note"),
        ("update", "1", "foo", "baz", ""),
        ("delete", "1"),
    ]


def test_model_config_service_wraps_snapshot_and_normalizes_inputs() -> None:
    manager = _DummyConfigManager()
    service = ModelConfigService(manager)

    snapshot_result = service.get_snapshot()
    snapshot = snapshot_result.data

    assert snapshot_result.success
    assert snapshot_result.code == "snapshot_loaded"
    assert snapshot.node_types == ["CheckpointLoaderSimple"]
    assert snapshot.node_indices["CheckpointLoaderSimple"] == [0, 1]
    assert snapshot.extensions == [".safetensors"]

    assert service.add_model_node_type("  Sampler  ").code == "node_type_added"
    assert service.add_node_model_index("Sampler", "3").code == "node_index_added"
    assert service.add_model_extension("ckpt").code == "extension_added"
    assert service.delete_node_model_index("Sampler", "3").code == "node_index_deleted"

    assert manager.calls == [
        ("add_model_node_type", "Sampler"),
        ("add_node_model_index", "Sampler", [3]),
        ("add_model_extension", ".ckpt"),
        ("remove_node_model_index", "Sampler", 3),
    ]


def test_model_config_service_rejects_non_integer_index() -> None:
    service = ModelConfigService(_DummyConfigManager())

    result = service.add_node_model_index("Sampler", "abc")

    assert not result.success
    assert result.code == "invalid_index"


def test_plugin_repair_service_returns_operation_results_for_view_and_validation() -> None:
    plugins = [
        SimpleNamespace(name="Joy Caption Two", description="desc-a"),
        SimpleNamespace(name="Other Plugin", description="desc-b"),
    ]
    model = _DummyPluginRepairModel(plugins=plugins, need_repair=["Joy Caption Two"])
    service = PluginRepairService(model)

    view_result = service.get_plugins_for_view()

    assert view_result.success
    assert view_result.code == "plugins_loaded"
    assert view_result.data == [
        {"name": "Joy Caption Two", "description": "desc-a", "status": "未检查"},
        {"name": "Other Plugin", "description": "desc-b", "status": "未检查"},
    ]

    status_result = service.check_plugin_status("C:/ComfyUI")

    assert model.checked_paths == ["C:/ComfyUI"]
    assert status_result.success
    assert status_result.code == "plugin_status_checked"
    assert status_result.data["need_repair"] == ["Joy Caption Two"]
    assert status_result.data["plugin_statuses"] == [
        {"name": "Joy Caption Two", "status": "需要修复"},
        {"name": "Other Plugin", "status": "已安装正确"},
    ]


def test_plugin_repair_service_returns_success_message_when_everything_is_healthy() -> None:
    plugins = [SimpleNamespace(name="Joy Caption Two", description="desc-a")]
    service = PluginRepairService(_DummyPluginRepairModel(plugins=plugins))

    result = service.check_plugin_status("C:/ComfyUI")

    assert result.success
    assert "正确安装" in result.message


def test_plugin_repair_service_validates_comfyui_layout(tmp_path: Path) -> None:
    service = PluginRepairService(_DummyPluginRepairModel())
    comfyui_root = tmp_path / "ComfyUI"
    comfyui_root.mkdir()
    (comfyui_root / "main.py").write_text("", encoding="utf-8")
    (comfyui_root / "web").mkdir()

    valid_result = service.validate_comfyui_dir(str(comfyui_root))
    invalid_result = service.validate_comfyui_dir(str(tmp_path / "empty"))

    assert valid_result.success
    assert valid_result.code == "valid_comfyui_dir"
    assert not invalid_result.success
    assert invalid_result.code == "invalid_comfyui_dir"


def test_plugin_repair_service_launches_helper_with_injected_launcher(tmp_path: Path) -> None:
    script_path = tmp_path / "helper.py"
    script_path.write_text("print('ok')", encoding="utf-8")
    launcher_calls = []

    def _launcher(command, **kwargs):
        launcher_calls.append((command, kwargs))

    service = PluginRepairService(
        _DummyPluginRepairModel(),
        helper_script_path_provider=lambda: str(script_path),
        process_launcher=_launcher,
        platform_name="linux",
        python_executable="python-test",
    )

    result = service.launch_repair_helper()

    assert result.success
    assert result.code == "helper_launched"
    assert result.data["script_path"] == str(script_path)
    assert launcher_calls == [(["python-test", str(script_path)], {})]


def test_plugin_repair_service_returns_error_when_helper_script_is_missing(tmp_path: Path) -> None:
    missing_script = tmp_path / "missing_helper.py"
    launcher_calls = []
    service = PluginRepairService(
        _DummyPluginRepairModel(),
        helper_script_path_provider=lambda: str(missing_script),
        process_launcher=lambda command, **kwargs: launcher_calls.append((command, kwargs)),
    )

    result = service.launch_repair_helper()

    assert not result.success
    assert result.code == "helper_script_missing"
    assert str(missing_script) in result.message
    assert launcher_calls == []


def test_comfyui_launcher_service_validates_required_paths(tmp_path: Path) -> None:
    service = ComfyUILauncherService(port_checker=lambda host, port, timeout: False)
    comfyui_root = tmp_path / "ComfyUI"
    comfyui_root.mkdir()
    python_exe = tmp_path / "python.exe"
    python_exe.write_text("", encoding="utf-8")

    missing_main_result = service.validate_paths(str(comfyui_root), str(python_exe))

    assert not missing_main_result.success
    assert missing_main_result.code == "missing_main_py"

    (comfyui_root / "main.py").write_text("print('ok')", encoding="utf-8")
    success_result = service.validate_paths(str(comfyui_root), str(python_exe))

    assert success_result.success
    assert success_result.code == "paths_valid"
    assert success_result.data["command"] == [str(python_exe), "-u", "main.py", "--enable-manager"]


def test_comfyui_launcher_service_starts_with_expected_command_and_cwd(tmp_path: Path) -> None:
    comfyui_root = tmp_path / "ComfyUI"
    comfyui_root.mkdir()
    (comfyui_root / "main.py").write_text("print('ok')", encoding="utf-8")
    python_exe = tmp_path / "python.exe"
    python_exe.write_text("", encoding="utf-8")
    launcher_calls = []
    process = _FakeProcess(stdout_text="booting\n")

    def _launcher(command, **kwargs):
        launcher_calls.append((command, kwargs))
        return process

    service = ComfyUILauncherService(process_launcher=_launcher, port_checker=lambda host, port, timeout: False)

    result = service.start(str(comfyui_root), str(python_exe))

    assert result.success
    assert result.code == "launch_started"
    assert launcher_calls == [
        (
            [str(python_exe), "-u", "main.py", "--enable-manager"],
            {
                "cwd": str(comfyui_root),
                "stdout": subprocess.PIPE,
                "stderr": subprocess.STDOUT,
                "text": True,
                "bufsize": 1,
            },
        )
    ]


def test_comfyui_launcher_service_supports_manager_only_mode(tmp_path: Path) -> None:
    comfyui_root = tmp_path / "ComfyUI"
    comfyui_root.mkdir()
    (comfyui_root / "main.py").write_text("", encoding="utf-8")
    custom_nodes = comfyui_root / "custom_nodes"
    custom_nodes.mkdir()
    (custom_nodes / "ComfyUI-Manager").mkdir()
    python_exe = tmp_path / "python.exe"
    python_exe.write_text("", encoding="utf-8")

    service = ComfyUILauncherService(port_checker=lambda host, port, timeout: False)

    result = service.validate_paths(str(comfyui_root), str(python_exe), launch_mode=ComfyUILauncherService.MANAGER_ONLY_MODE)

    assert result.success
    assert result.data["command"] == [
        str(python_exe),
        "-u",
        "main.py",
        "--enable-manager",
        "--disable-all-custom-nodes",
        "--whitelist-custom-nodes",
        "ComfyUI-Manager",
    ]


def test_comfyui_launcher_service_adds_legacy_ui_flag_for_manager_v4(tmp_path: Path) -> None:
    comfyui_root = tmp_path / "ComfyUI"
    comfyui_root.mkdir()
    (comfyui_root / "main.py").write_text("", encoding="utf-8")
    python_home = tmp_path / "python_embeded"
    python_home.mkdir()
    python_exe = python_home / "python.exe"
    python_exe.write_text("", encoding="utf-8")
    site_packages = python_home / "Lib" / "site-packages" / "comfyui_manager-4.1.dist-info"
    site_packages.mkdir(parents=True)

    service = ComfyUILauncherService(port_checker=lambda host, port, timeout: False)

    result = service.validate_paths(str(comfyui_root), str(python_exe))

    assert result.success
    assert result.data["command"] == [
        str(python_exe),
        "-u",
        "main.py",
        "--enable-manager",
        "--enable-manager-legacy-ui",
    ]


def test_comfyui_launcher_service_rejects_duplicate_start(tmp_path: Path) -> None:
    comfyui_root = tmp_path / "ComfyUI"
    comfyui_root.mkdir()
    (comfyui_root / "main.py").write_text("", encoding="utf-8")
    python_exe = tmp_path / "python.exe"
    python_exe.write_text("", encoding="utf-8")
    process = _FakeProcess()
    service = ComfyUILauncherService(
        process_launcher=lambda command, **kwargs: process,
        port_checker=lambda host, port, timeout: False,
    )

    first_result = service.start(str(comfyui_root), str(python_exe))
    second_result = service.start(str(comfyui_root), str(python_exe))

    assert first_result.success
    assert not second_result.success
    assert second_result.code == "already_running"


def test_comfyui_launcher_service_stop_is_noop_without_running_process() -> None:
    service = ComfyUILauncherService()

    result = service.stop()

    assert result.success
    assert result.code == "stop_noop"


def test_comfyui_launcher_service_shutdown_joins_reader_thread() -> None:
    service = ComfyUILauncherService()
    join_calls = []

    class _FakeThread:
        def is_alive(self):
            return True

        def join(self, timeout=None):
            join_calls.append(timeout)

    class _FakeStdout:
        def close(self):
            join_calls.append("closed")

    service._reader_thread = _FakeThread()
    service._process = SimpleNamespace(stdout=_FakeStdout(), poll=lambda: 0)

    result = service.shutdown()

    assert result.success
    assert "closed" in join_calls


def test_comfyui_launcher_service_stops_windows_process_tree(tmp_path: Path) -> None:
    comfyui_root = tmp_path / "ComfyUI"
    comfyui_root.mkdir()
    (comfyui_root / "main.py").write_text("", encoding="utf-8")
    python_exe = tmp_path / "python.exe"
    python_exe.write_text("", encoding="utf-8")
    process = _FakeProcess(pid=4321)
    killed_pids = []

    service = ComfyUILauncherService(
        process_launcher=lambda command, **kwargs: process,
        process_tree_killer=lambda pid: killed_pids.append(pid),
        port_checker=lambda host, port, timeout: False,
        platform_name="win32",
    )
    service.start(str(comfyui_root), str(python_exe))

    result = service.stop()

    assert result.success
    assert result.code == "stop_completed"
    assert killed_pids == [4321]


def test_comfyui_launcher_service_rejects_start_when_port_is_in_use(tmp_path: Path) -> None:
    comfyui_root = tmp_path / "ComfyUI"
    comfyui_root.mkdir()
    (comfyui_root / "main.py").write_text("", encoding="utf-8")
    python_exe = tmp_path / "python.exe"
    python_exe.write_text("", encoding="utf-8")
    service = ComfyUILauncherService(port_checker=lambda host, port, timeout: True)

    result = service.validate_paths(str(comfyui_root), str(python_exe))

    assert not result.success
    assert result.code == "port_in_use"
    assert result.data["port"] == 8188


def test_dependency_rule_service_loads_aki_rules(tmp_path: Path) -> None:
    rule_root = tmp_path / "launcher_dependency_system_src"
    rule_root.mkdir()
    (rule_root / "data.json").write_text(
        json.dumps(
            {
                "mirrors": {
                    "additional_mirror_envs": [
                        {"env": "XFORMERS_WINDOWS_PACKAGE", "url": "https://example.com/xformers.whl"},
                        {"env": "INSIGHTFACE_WHEEL", "url": "insightface"},
                    ],
                    "extra_pip_index": ["https://pypi.example.com/ms"],
                    "pip_find_links": ["https://mirror.example.com/torch.html"],
                },
                "torch_versions": [{"name": "Torch 2.6.0", "steps": []}],
                "onnxruntime_releases": [{"engine_type": "cuda", "arguments": ["install", "onnxruntime-gpu==1.18.1"]}],
            }
        ),
        encoding="utf-8",
    )

    service = DependencyRuleService(rule_root_candidates=[str(rule_root)])

    result = service.load_rules()

    assert result.success
    assert result.data["additional_mirror_envs"]["XFORMERS_WINDOWS_PACKAGE"] == "https://example.com/xformers.whl"
    assert result.data["special_package_rules"]["xformers"]["strategy"] == "install_with_wheel"
    assert result.data["special_package_rules"]["insightface"]["strategy"] == "install_with_mirror"
    assert result.data["extra_pip_index"] == ["https://pypi.example.com/ms"]
    assert result.data["pip_find_links"] == ["https://mirror.example.com/torch.html"]


def test_dependency_rule_service_tolerates_invalid_utf8_and_trailing_bytes(tmp_path: Path) -> None:
    rule_root = tmp_path / "launcher_dependency_system_src"
    rule_root.mkdir()
    raw_json = (
        b'{"mirrors":{"additional_mirror_envs":[{"env":"INSIGHTFACE_WHEEL","url":"insightface"}],'
        b'"extra_pip_index":["https://pypi.example.com/ms"],"pip_find_links":[]},'
        b'"torch_versions":[],"onnxruntime_releases":[],"front_page_announcement":"bad'
        + bytes([0xC4])
        + b'"}'
        + b"\x00\x01garbage"
    )
    (rule_root / "data.json").write_bytes(raw_json)

    service = DependencyRuleService(rule_root_candidates=[str(rule_root)])

    result = service.load_rules()

    assert result.success
    assert result.data["special_package_rules"]["insightface"]["strategy"] == "install_with_mirror"


def test_dependency_rule_service_applies_skip_replace_and_remove_extra() -> None:
    service = DependencyRuleService(rule_root_candidates=[])

    result = service.apply_requirement_rules(
        "demo_pkg[vision]==1.0.0",
        skip_packages={"skip-me"},
        replace_packages={"demo-pkg": "demo-wheel"},
        replace_packages_pre={"==1.0.0": "==2.0.0"},
        remove_packages_extra={"demo-wheel"},
    )

    assert result.success
    assert result.data["name"] == "demo-wheel"
    assert result.data["specifier"] == "==2.0.0"
    assert result.data["removed_extras"] == ["vision"]
    assert not result.data["skipped"]


def test_dependency_environment_service_collects_snapshot_from_python_and_custom_nodes(tmp_path: Path) -> None:
    comfyui_root = tmp_path / "ComfyUI"
    custom_nodes = comfyui_root / "custom_nodes"
    (custom_nodes / "PluginA").mkdir(parents=True)
    (custom_nodes / "PluginB").mkdir()

    calls = []

    def _runner(command):
        calls.append(command)
        if command[-3:] == ["-m", "pip", "list"]:
            return {"success": False, "returncode": 0, "stdout": "", "stderr": ""}
        if command[1:4] == ["-m", "pip", "list"]:
            return {
                "success": True,
                "returncode": 0,
                "stdout": json.dumps([{"name": "numpy", "version": "1.26.4"}]),
                "stderr": "",
            }
        return {
            "success": True,
            "returncode": 0,
            "stdout": json.dumps({"python_version": "3.11.6", "platform": "win32", "torch_version": "2.6.0", "torch_cuda": "12.4"}),
            "stderr": "",
        }

    service = DependencyEnvironmentService(
        python_path_provider=lambda: sys.executable,
        comfyui_path_provider=lambda: str(comfyui_root),
        command_runner=_runner,
    )

    result = service.collect_environment_snapshot()

    assert result.success
    assert result.data["pip_packages"] == {"numpy": "1.26.4"}
    assert result.data["installed_plugins"] == ["PluginA", "PluginB"]
    assert result.data["torch_version"] == "2.6.0"
    assert len(calls) == 2


def test_dependency_preflight_service_detects_conflicts_and_special_policy(tmp_path: Path) -> None:
    comfyui_root = tmp_path / "ComfyUI"
    custom_nodes = comfyui_root / "custom_nodes"
    plugin_a = custom_nodes / "PluginA"
    plugin_b = custom_nodes / "PluginB"
    plugin_c = custom_nodes / "PluginC"
    plugin_a.mkdir(parents=True)
    plugin_b.mkdir()
    plugin_c.mkdir()
    (plugin_a / "requirements.txt").write_text("xformers==0.0.29.post3\nshared-lib==1.0.0\n", encoding="utf-8")
    (plugin_b / "requirements.txt").write_text("shared-lib==2.0.0\n", encoding="utf-8")

    rule_root = tmp_path / "rules"
    rule_root.mkdir()
    (rule_root / "data.json").write_text(
        json.dumps(
            {
                "mirrors": {
                    "additional_mirror_envs": [
                        {"env": "XFORMERS_WINDOWS_PACKAGE", "url": "https://example.com/xformers.whl"},
                    ]
                }
            }
        ),
        encoding="utf-8",
    )

    environment_service = SimpleNamespace(
        collect_environment_snapshot=lambda: OperationResult(
            True,
            data={
                "python_path": sys.executable,
                "python_version": "3.11.6",
                "platform": "win32",
                "torch_version": "2.6.0",
                "torch_cuda": "12.4",
                "pip_packages": {"shared-lib": "1.0.0"},
                "installed_plugins": ["PluginA", "PluginB"],
                "comfyui_path": str(comfyui_root),
            },
        )
    )
    preflight_service = DependencyPreflightService(
        environment_service=environment_service,
        rule_service=DependencyRuleService(rule_root_candidates=[str(rule_root)]),
    )

    packages = [
        {"id": "PluginA", "title": "PluginA", "metadata": {}, "queue_action": "install"},
        {"id": "PluginB", "title": "PluginB", "metadata": {}, "queue_action": "install"},
        {"id": "PluginC", "title": "PluginC", "metadata": {}, "queue_action": "install"},
    ]

    result = preflight_service.evaluate(packages)

    assert result.success
    rows = {item["id"]: item for item in result.data["rows"]}
    assert rows["PluginA"]["conclusion"] == "blocked"
    assert rows["PluginA"]["strategy"] == "defer_manual"
    assert rows["PluginB"]["conclusion"] == "blocked"
    assert rows["PluginC"]["conclusion"] == "warning"
    assert result.data["summary"]["blocked"] == 2


def test_dependency_install_planner_blocks_or_filters_based_on_preflight() -> None:
    planner = DependencyInstallPlanner()
    packages = [
        {"id": "safe-pack", "title": "Safe Pack", "queue_action": "install"},
        {"id": "blocked-pack", "title": "Blocked Pack", "queue_action": "install"},
        {"id": "warn-pack", "title": "Warn Pack", "queue_action": "install"},
    ]
    preflight = {
        "rows": [
            {"id": "safe-pack", "conclusion": "safe", "strategy": "install"},
            {"id": "blocked-pack", "conclusion": "blocked", "strategy": "defer_manual", "reasons": ["conflict"]},
            {"id": "warn-pack", "conclusion": "warning", "strategy": "install"},
        ]
    }

    blocked_result = planner.build_execution_plan(packages, preflight)
    safe_only_result = planner.build_execution_plan(packages, preflight, safe_only=True)

    assert not blocked_result.success
    assert blocked_result.code == "dependency_execution_blocked"
    assert [item["id"] for item in safe_only_result.data["executable_packages"]] == ["safe-pack"]


def test_comfyui_runtime_api_service_reads_registered_node_types() -> None:
    service = ComfyUIRuntimeApiService(
        base_url_provider=lambda: "http://127.0.0.1:8188",
        http_requester=lambda **kwargs: (
            200,
            json.dumps(
                {
                    "KSampler": {"input": {}},
                    "CheckpointLoaderSimple": {"input": {}},
                }
            ),
        ),
    )

    result = service.get_registered_node_types()

    assert result.success
    assert result.code == "registered_node_types_loaded"
    assert result.data["count"] == 2
    assert "KSampler" in result.data["node_types"]


def test_comfyui_manager_api_service_queues_install_and_starts_queue() -> None:
    calls = []

    def _requester(**kwargs):
        calls.append(kwargs)
        return 200, "{}"

    service = ComfyUIManagerApiService(
        base_url_provider=lambda: "http://127.0.0.1:8188",
        http_requester=_requester,
    )

    metadata = {"id": "impact-pack", "title": "Impact Pack", "version": "unknown", "files": ["https://repo"], "channel": "default", "mode": "default"}
    queue_result = service.queue_install(metadata)
    start_result = service.start_queue()

    assert queue_result.success
    assert start_result.success
    assert calls[0]["method"] == "POST"
    assert calls[0]["payload"]["id"] == "impact-pack"
    assert calls[1]["url"].endswith("/manager/queue/start")


def test_comfyui_manager_api_service_supports_import_fail_bulk_and_fix_queue() -> None:
    calls = []

    def _requester(**kwargs):
        calls.append(kwargs)
        if kwargs["url"].endswith("/v2/customnode/import_fail_info_bulk"):
            return 200, json.dumps({"impact-pack": {"error": "ImportError"}})
        return 200, "{}"

    service = ComfyUIManagerApiService(
        base_url_provider=lambda: "http://127.0.0.1:8188",
        http_requester=_requester,
    )

    import_fail_result = service.get_import_fail_info_bulk(cnr_ids=["impact-pack"])
    fix_result = service.queue_fix({"id": "impact-pack", "version": "1.0.0"})

    assert import_fail_result.success
    assert import_fail_result.data["impact-pack"]["error"] == "ImportError"
    assert fix_result.success
    assert calls[1]["url"].endswith("/manager/queue/fix")


def test_comfyui_manager_api_service_detects_v4_prefix_and_uses_v2_endpoints() -> None:
    calls = []

    def _requester(**kwargs):
        calls.append(kwargs)
        url = kwargs["url"]
        if url.endswith("/v2/manager/version"):
            return 200, "V4.1"
        if url.endswith("/manager/version"):
            return 404, ""
        if url.endswith("/v2/manager/db_mode"):
            return 200, "cache"
        if url.endswith("/v2/customnode/getmappings?mode=cache"):
            return 200, json.dumps({})
        if url.endswith("/v2/manager/queue/start"):
            return 200, "{}"
        return 404, ""

    service = ComfyUIManagerApiService(
        base_url_provider=lambda: "http://127.0.0.1:8188",
        http_requester=_requester,
    )

    version_result = service.get_version()
    db_mode_result = service.get_db_mode()
    mappings_result = service.get_node_mappings("cache")
    start_result = service.start_queue()

    assert version_result.success
    assert version_result.data["value"] == "V4.1"
    assert db_mode_result.success
    assert mappings_result.success
    assert start_result.success
    assert any(call["url"].endswith("/v2/manager/db_mode") for call in calls)
    assert any(call["url"].endswith("/v2/customnode/getmappings?mode=cache") for call in calls)
    assert calls[-1]["url"].endswith("/v2/manager/queue/start")


def test_comfyui_manager_api_service_falls_back_to_local_custom_node_cache(tmp_path: Path) -> None:
    comfyui_root = tmp_path / "ComfyUI"
    cache_dir = comfyui_root / "user" / "__manager" / "cache"
    cache_dir.mkdir(parents=True)
    (cache_dir / "123_custom-node-list.json").write_text(
        json.dumps(
            {
                "custom_nodes": [
                    {
                        "id": "impact-pack",
                        "title": "Impact Pack",
                        "files": ["https://github.com/ltdrdata/ComfyUI-Impact-Pack"],
                        "reference": "https://github.com/ltdrdata/ComfyUI-Impact-Pack",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    service = ComfyUIManagerApiService(
        base_url_provider=lambda: "http://127.0.0.1:8188",
        comfyui_path_provider=lambda: str(comfyui_root),
        http_requester=lambda **kwargs: (404, ""),
    )

    result = service.get_custom_node_list("cache")

    assert result.success
    assert result.data["node_packs"]["impact-pack"]["title"] == "Impact Pack"
    assert result.data["node_packs"]["impact-pack"]["mode"] == "cache"


def test_missing_node_install_orchestrator_maps_v4_enabled_state_to_enabled(tmp_path: Path) -> None:
    workflow_file = tmp_path / "workflow.json"
    workflow_file.write_text(json.dumps({"nodes": [{"type": "ImpactWildcardProcessor"}]}), encoding="utf-8")

    runtime_api = SimpleNamespace(
        get_registered_node_types=lambda: SimpleNamespace(success=True, data={"node_types": ["KSampler"]}),
    )
    manager_api = SimpleNamespace(
        is_available=lambda: SimpleNamespace(success=True, data={"value": "V4.1"}),
        get_db_mode=lambda: SimpleNamespace(success=True, data={"value": "cache"}),
        get_node_mappings=lambda mode: SimpleNamespace(
            success=True,
            data={"impact-pack": [["ImpactWildcardProcessor"], {"title_aux": "Impact Pack"}]},
        ),
        get_custom_node_list=lambda mode: SimpleNamespace(
            success=True,
            data={
                "channel": "default",
                "node_packs": {
                    "impact-pack": {
                        "id": "impact-pack",
                        "title": "Impact Pack",
                        "version": "1.0.0",
                        "files": ["https://github.com/ltdrdata/ComfyUI-Impact-Pack"],
                    }
                },
            },
        ),
        get_installed_nodes=lambda mode="cache": SimpleNamespace(
            success=True,
            data={"impact-pack": {"ver": "1.0.0", "cnr_id": "impact-pack", "enabled": True}},
        ),
        get_import_fail_info_bulk=lambda **kwargs: SimpleNamespace(success=True, data={}),
    )
    orchestrator = MissingNodeInstallOrchestrator(runtime_api, manager_api, WorkflowMissingNodeService())

    result = orchestrator.prepare_install_plan([str(workflow_file)])

    assert result.success
    assert result.data["install_plan"][0]["state"] == "enabled"
    assert result.data["install_plan"][0]["queue_action"] == "update"


def test_workflow_missing_node_service_collects_files_and_analyzes_missing_nodes(tmp_path: Path) -> None:
    workflow_file = tmp_path / "workflow.json"
    workflow_file.write_text(
        json.dumps(
            {
                "nodes": [
                    {"id": 1, "class_type": "KSampler"},
                    {"id": 2, "class_type": "ImpactWildcardProcessor"},
                ]
            }
        ),
        encoding="utf-8",
    )
    nested_dir = tmp_path / "nested"
    nested_dir.mkdir()
    (nested_dir / "other.json").write_text(json.dumps({"prompt": {"3": {"class_type": "CLIPTextEncode"}}}), encoding="utf-8")

    service = WorkflowMissingNodeService()
    files_result = service.collect_workflow_files([str(tmp_path)])
    analysis_result = service.analyze_missing_node_types(files_result.data["workflow_files"], {"KSampler"})

    assert files_result.success
    assert files_result.data["count"] == 2
    assert analysis_result.success
    assert sorted(analysis_result.data["missing_node_types"]) == ["CLIPTextEncode", "ImpactWildcardProcessor"]


def test_workflow_missing_node_service_extracts_frontend_exported_node_types() -> None:
    service = WorkflowMissingNodeService()

    result = service.extract_node_types(
        {
            "nodes": [
                {"id": 1, "type": "InstantIDFaceAnalysis"},
                {"id": 2, "type": "QG_KeyNode"},
                {"id": 3, "type": "InstantIDFaceAnalysis"},
            ]
        }
    )

    assert result.success
    assert result.data["count"] == 2
    assert result.data["node_types"] == ["InstantIDFaceAnalysis", "QG_KeyNode"]


def test_workflow_missing_node_service_extracts_node_descriptors_with_ids() -> None:
    service = WorkflowMissingNodeService()

    result = service.extract_node_descriptors(
        {
            "nodes": [
                {
                    "id": 1,
                    "type": "InstantIDFaceAnalysis",
                    "properties": {"cnr_id": "comfyui_instantid"},
                },
                {
                    "id": 2,
                    "type": "ApplyInstantIDAdvanced",
                    "properties": {"aux_id": "sunxAI/comfyui_sunxAI_facetools"},
                },
            ]
        }
    )

    assert result.success
    assert result.data["count"] == 2
    assert result.data["nodes"][0]["aux_id"] == "sunxAI/comfyui_sunxAI_facetools"
    assert result.data["nodes"][1]["cnr_id"] == "comfyui_instantid"


def test_workflow_missing_node_service_supports_mixed_prompt_and_canvas_formats(tmp_path: Path) -> None:
    workflow_file = tmp_path / "mixed.json"
    workflow_file.write_text(
        json.dumps(
            {
                "nodes": [
                    {"id": 1, "type": "InstantIDFaceAnalysis"},
                    {"id": 2, "type": "PuLIDLoader"},
                ],
                "prompt": {
                    "3": {"class_type": "KSampler"},
                },
            }
        ),
        encoding="utf-8",
    )

    service = WorkflowMissingNodeService()
    analysis_result = service.analyze_missing_node_types([str(workflow_file)], {"KSampler"})

    assert analysis_result.success
    assert sorted(analysis_result.data["missing_node_types"]) == ["InstantIDFaceAnalysis", "PuLIDLoader"]


def test_missing_node_install_orchestrator_prepares_deduplicated_install_plan(tmp_path: Path) -> None:
    workflow_file = tmp_path / "workflow.json"
    workflow_file.write_text(
        json.dumps(
            {
                "nodes": [
                    {"class_type": "ImpactWildcardProcessor"},
                    {"class_type": "ImpactWildcardProcessor"},
                    {"class_type": "UnknownCustomNode"},
                ]
            }
        ),
        encoding="utf-8",
    )

    runtime_api = SimpleNamespace(
        get_registered_node_types=lambda: SimpleNamespace(success=True, data={"node_types": ["KSampler"]}),
    )
    manager_api = SimpleNamespace(
        is_available=lambda: SimpleNamespace(success=True, data={"value": "3.32.3"}),
        get_db_mode=lambda: SimpleNamespace(success=True, data={"value": "default"}),
        get_node_mappings=lambda mode: SimpleNamespace(
            success=True,
            data={
                "impact-pack": [
                    ["ImpactWildcardProcessor"],
                    {"title_aux": "Impact Pack"},
                ]
            },
        ),
        get_custom_node_list=lambda mode: SimpleNamespace(
            success=True,
            data={
                "channel": "default",
                "node_packs": {
                    "impact-pack": {
                        "id": "impact-pack",
                        "title": "Impact Pack",
                        "state": "not-installed",
                        "version": "unknown",
                        "files": ["https://repo"],
                        "channel": "default",
                        "mode": "default",
                    }
                }
            },
        ),
        get_installed_nodes=lambda mode="default": SimpleNamespace(success=True, data={}),
        get_import_fail_info_bulk=lambda **kwargs: SimpleNamespace(success=True, data={}),
    )
    orchestrator = MissingNodeInstallOrchestrator(runtime_api, manager_api, WorkflowMissingNodeService())

    result = orchestrator.prepare_install_plan([str(workflow_file)])

    assert result.success
    assert len(result.data["install_plan"]) == 1
    assert result.data["install_plan"][0]["missing_count"] == 1
    assert result.data["install_plan"][0]["queue_action"] == "install"
    assert result.data["install_plan"][0]["metadata"]["channel"] == "default"
    assert result.data["install_plan"][0]["metadata"]["mode"] == "default"
    assert result.data["install_plan"][0]["metadata"]["ui_id"] == "impact-pack"
    assert result.data["manual_items"] == [{"node_type": "UnknownCustomNode", "reason": "未找到可自动映射的插件包。"}]


def test_missing_node_install_orchestrator_keeps_installed_missing_packages_visible(tmp_path: Path) -> None:
    workflow_file = tmp_path / "workflow.json"
    workflow_file.write_text(json.dumps({"nodes": [{"type": "ImpactWildcardProcessor"}]}), encoding="utf-8")

    runtime_api = SimpleNamespace(
        get_registered_node_types=lambda: SimpleNamespace(success=True, data={"node_types": ["KSampler"]}),
    )
    manager_api = SimpleNamespace(
        is_available=lambda: SimpleNamespace(success=True, data={"value": "3.32.3"}),
        get_db_mode=lambda: SimpleNamespace(success=True, data={"value": "default"}),
        get_node_mappings=lambda mode: SimpleNamespace(
            success=True,
            data={"impact-pack": [["ImpactWildcardProcessor"], {"title_aux": "Impact Pack"}]},
        ),
        get_custom_node_list=lambda mode: SimpleNamespace(
            success=True,
            data={
                "channel": "default",
                "node_packs": {
                    "impact-pack": {
                        "id": "impact-pack",
                        "title": "Impact Pack",
                        "name": "ComfyUI-Impact-Pack",
                        "state": "not-installed",
                        "version": "unknown",
                        "files": ["https://github.com/ltdrdata/ComfyUI-Impact-Pack"],
                        "channel": "default",
                        "mode": "default",
                    }
                }
            },
        ),
        get_installed_nodes=lambda mode="default": SimpleNamespace(
            success=True,
            data={"impact-pack": {"id": "impact-pack", "title": "Impact Pack"}},
        ),
        get_import_fail_info_bulk=lambda **kwargs: SimpleNamespace(success=True, data={}),
    )
    orchestrator = MissingNodeInstallOrchestrator(runtime_api, manager_api, WorkflowMissingNodeService())

    result = orchestrator.prepare_install_plan([str(workflow_file)])

    assert result.success
    assert len(result.data["install_plan"]) == 1
    assert result.data["install_plan"][0]["state"] == "installed"
    assert result.data["install_plan"][0]["queue_action"] == ""
    assert result.data["manual_items"] == []


def test_missing_node_install_orchestrator_executes_selected_packages() -> None:
    queued = []
    fixed = []
    enabled = []
    reinstalled = []
    updated = []
    started = []
    manager_api = SimpleNamespace(
        queue_install=lambda metadata, **kwargs: queued.append(metadata["id"]) or SimpleNamespace(success=True),
        queue_fix=lambda metadata: fixed.append(metadata["id"]) or SimpleNamespace(success=True),
        queue_reinstall=lambda metadata: reinstalled.append(metadata["id"]) or SimpleNamespace(success=True),
        queue_update=lambda metadata: updated.append(metadata["id"]) or SimpleNamespace(success=True),
        start_queue=lambda: started.append(True) or SimpleNamespace(success=True),
    )
    orchestrator = MissingNodeInstallOrchestrator(SimpleNamespace(), manager_api, WorkflowMissingNodeService())

    result = orchestrator.execute_install_plan(
        [
            {"id": "impact-pack", "title": "Impact Pack", "queue_action": "install", "metadata": {"id": "impact-pack"}},
            {"id": "was-suite", "title": "WAS Suite", "queue_action": "fix", "metadata": {"id": "was-suite"}},
            {"id": "disabled-pack", "title": "Disabled Pack", "queue_action": "enable", "metadata": {"id": "disabled-pack"}},
            {"id": "invalid-pack", "title": "Invalid Pack", "queue_action": "reinstall", "metadata": {"id": "invalid-pack"}},
            {"id": "enabled-pack", "title": "Enabled Pack", "queue_action": "update", "metadata": {"id": "enabled-pack"}},
        ]
    )

    assert result.success
    assert queued == ["impact-pack", "disabled-pack"]
    assert fixed == ["was-suite"]
    assert reinstalled == ["invalid-pack"]
    assert updated == ["enabled-pack"]
    assert started == [True]
    assert result.data["restart_required"] is True


def test_missing_node_install_orchestrator_keeps_installed_rows_in_missing_results(tmp_path: Path) -> None:
    workflow_file = tmp_path / "workflow.json"
    workflow_file.write_text(json.dumps({"nodes": [{"type": "ImpactWildcardProcessor"}]}), encoding="utf-8")

    runtime_api = SimpleNamespace(
        get_registered_node_types=lambda: SimpleNamespace(success=True, data={"node_types": ["KSampler"]}),
    )
    manager_api = SimpleNamespace(
        is_available=lambda: SimpleNamespace(success=True, data={"value": "3.32.3"}),
        get_db_mode=lambda: SimpleNamespace(success=True, data={"value": "default"}),
        get_node_mappings=lambda mode: SimpleNamespace(
            success=True,
            data={"impact-pack": [["ImpactWildcardProcessor"], {"title_aux": "Impact Pack"}]},
        ),
        get_custom_node_list=lambda mode: SimpleNamespace(
            success=True,
            data={
                "channel": "default",
                "node_packs": {
                    "impact-pack": {
                        "id": "impact-pack",
                        "title": "Impact Pack",
                        "name": "ComfyUI-Impact-Pack",
                        "state": "not-installed",
                        "version": "unknown",
                        "files": ["https://github.com/ltdrdata/ComfyUI-Impact-Pack"],
                    }
                },
            },
        ),
        get_installed_nodes=lambda mode="default": SimpleNamespace(
            success=True,
            data={"impact-pack": {"id": "impact-pack", "title": "Impact Pack"}},
        ),
        get_import_fail_info_bulk=lambda **kwargs: SimpleNamespace(success=True, data={}),
    )
    orchestrator = MissingNodeInstallOrchestrator(runtime_api, manager_api, WorkflowMissingNodeService())

    result = orchestrator.prepare_install_plan([str(workflow_file)])

    assert result.success
    assert len(result.data["install_plan"]) == 1
    assert result.data["install_plan"][0]["state"] == "installed"
    assert result.data["install_plan"][0]["status"] == "当前状态"
    assert result.data["manual_items"] == []


def test_missing_node_install_orchestrator_surfaces_import_failed_candidates(tmp_path: Path) -> None:
    workflow_file = tmp_path / "workflow.json"
    workflow_file.write_text(
        json.dumps(
            {
                "nodes": [
                    {
                        "type": "InstantIDFaceAnalysis",
                        "properties": {"cnr_id": "comfyui_sunxai_facetools"},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    runtime_api = SimpleNamespace(
        get_registered_node_types=lambda: SimpleNamespace(success=True, data={"node_types": ["KSampler"]}),
    )
    manager_api = SimpleNamespace(
        is_available=lambda: SimpleNamespace(success=True, data={"value": "3.32.3"}),
        get_db_mode=lambda: SimpleNamespace(success=True, data={"value": "default"}),
        get_node_mappings=lambda mode: SimpleNamespace(success=True, data={}),
        get_custom_node_list=lambda mode: SimpleNamespace(
            success=True,
            data={
                "channel": "default",
                "node_packs": {
                    "comfyui_sunxai_facetools": {
                        "id": "comfyui_sunxai_facetools",
                        "title": "comfyui_sunxAI_facetools",
                        "state": "installed",
                        "version": "0.2.7",
                        "repository": "https://github.com/sunxAI/comfyui_sunxAI_facetools",
                    }
                },
            },
        ),
        get_installed_nodes=lambda mode="default": SimpleNamespace(
            success=True,
            data={"comfyui_sunxai_facetools": {"id": "comfyui_sunxai_facetools", "title": "comfyui_sunxAI_facetools"}},
        ),
        get_import_fail_info_bulk=lambda **kwargs: SimpleNamespace(
            success=True,
            data={"comfyui_sunxai_facetools": {"error": "ImportError"}},
        ),
    )
    orchestrator = MissingNodeInstallOrchestrator(runtime_api, manager_api, WorkflowMissingNodeService())

    result = orchestrator.prepare_install_plan([str(workflow_file)])

    assert result.success
    assert result.data["install_plan"][0]["state"] == "import-fail"
    assert result.data["install_plan"][0]["status"] == "待修复"
    assert result.data["install_plan"][0]["queue_action"] == "fix"
