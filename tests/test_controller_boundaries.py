from types import SimpleNamespace

import pytest

from ModelFinderV2_6.controller import AppController
from ModelFinderV2_6.operation_result import OperationResult


pytestmark = pytest.mark.unit


class _Var:
    def __init__(self, value=None):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class _ImmediateRoot:
    def __init__(self):
        self.scheduled = []
        self.destroyed = False

    def after(self, delay, callback, *args):
        if delay == 0:
            callback(*args)
            return None
        self.scheduled.append((delay, callback, args))
        return None

    def destroy(self):
        self.destroyed = True


class _FakeView:
    def __init__(self):
        self.logs = []
        self.info_calls = []
        self.error_calls = []
        self.warning_calls = []
        self.ask_calls = []
        self.ask_yes_no_result = True
        self.retention_days = 30
        self.selected_theme = None
        self.loaded_mappings = None
        self.loaded_node_types = None
        self.loaded_node_indices = None
        self.loaded_extensions = None
        self.plugin_status_updates = []
        self.comfyui_path = ""
        self.comfyui_python_path = ""
        self.workflow_mode = "single"
        self.comfyui_launch_logs = []
        self.comfyui_launch_status = None
        self.comfyui_launch_details = None
        self.comfyui_launch_button_states = []
        self.missing_installer_logs = []
        self.missing_installer_runtime = None
        self.missing_installer_steps = None
        self.missing_installer_current_step = None
        self.missing_installer_paths = []
        self.missing_installer_summary = {}
        self.missing_installer_preflight_summary = {}
        self.missing_installer_packages = []
        self.missing_installer_preflight_rows = []
        self.missing_installer_manual_items = []
        self.missing_installer_install_rows = []
        self.missing_installer_restart_visible = False
        self.missing_installer_queue_progress = ""
        self.missing_installer_preflight_actions = None
        self.selected_missing_installer_package_id = None
        self.missing_installer_quick_path = ""

    def update_log(self, message):
        self.logs.append(message)

    def show_info(self, title, message):
        self.info_calls.append((title, message))

    def show_error(self, title, message):
        self.error_calls.append((title, message))

    def show_warning(self, title, message):
        self.warning_calls.append((title, message))

    def ask_yes_no(self, title, message):
        self.ask_calls.append((title, message))
        return self.ask_yes_no_result

    def get_retention_days(self):
        return self.retention_days

    def set_selected_theme(self, theme):
        self.selected_theme = theme

    def get_selected_theme(self):
        return self.selected_theme

    def load_irregular_mappings(self, mappings):
        self.loaded_mappings = mappings

    def load_model_node_types(self, node_types):
        self.loaded_node_types = node_types

    def load_node_indices(self, node_indices):
        self.loaded_node_indices = node_indices

    def load_model_extensions(self, extensions):
        self.loaded_extensions = extensions

    def get_comfyui_path(self):
        return self.comfyui_path

    def set_comfyui_path(self, path):
        self.comfyui_path = path

    def get_comfyui_python_path(self):
        return self.comfyui_python_path

    def set_comfyui_python_path(self, path):
        self.comfyui_python_path = path

    def get_workflow_mode(self):
        return self.workflow_mode

    def update_plugin_status(self, name, status):
        self.plugin_status_updates.append((name, status))

    def append_comfyui_launch_log(self, message):
        self.comfyui_launch_logs.append(message)

    def clear_comfyui_launch_log(self):
        self.comfyui_launch_logs.clear()

    def set_comfyui_launch_status(self, status):
        self.comfyui_launch_status = status

    def set_comfyui_launch_details(self, *, pid="", command=""):
        self.comfyui_launch_details = {"pid": pid, "command": command}

    def set_comfyui_launch_button_states(self, *, start_enabled, stop_enabled):
        self.comfyui_launch_button_states.append((start_enabled, stop_enabled))

    def append_missing_installer_log(self, message):
        self.missing_installer_logs.append(message)

    def clear_missing_installer_log(self):
        self.missing_installer_logs.clear()

    def set_missing_installer_runtime_status(self, *, comfyui_status, manager_status, start_enabled):
        self.missing_installer_runtime = (comfyui_status, manager_status, start_enabled)

    def set_missing_installer_steps(self, *, current_step, completed_steps):
        self.missing_installer_steps = (current_step, set(completed_steps))

    def show_missing_installer_step(self, step_index):
        self.missing_installer_current_step = step_index

    def set_missing_installer_selected_paths(self, paths):
        self.missing_installer_paths = list(paths)
        if len(paths) == 1:
            self.missing_installer_quick_path = paths[0]
        elif not paths:
            self.missing_installer_quick_path = ""

    def get_missing_installer_quick_path(self):
        return self.missing_installer_quick_path

    def set_missing_installer_quick_path(self, path):
        self.missing_installer_quick_path = path

    def set_missing_installer_analysis_summary(self, summary):
        self.missing_installer_summary = dict(summary)

    def load_missing_installer_packages(self, packages):
        self.missing_installer_packages = [dict(item) for item in packages]

    def set_missing_installer_preflight_summary(self, summary):
        self.missing_installer_preflight_summary = dict(summary)

    def load_missing_installer_preflight_rows(self, rows):
        self.missing_installer_preflight_rows = [dict(item) for item in rows]

    def set_missing_installer_preflight_actions(self, *, can_install, safe_only_enabled, blocked_count):
        self.missing_installer_preflight_actions = (can_install, safe_only_enabled, blocked_count)

    def load_missing_installer_manual_items(self, items):
        self.missing_installer_manual_items = list(items)

    def load_missing_installer_install_rows(self, packages):
        self.missing_installer_install_rows = [dict(item) for item in packages]

    def get_selected_missing_installer_package_id(self):
        return self.selected_missing_installer_package_id

    def set_missing_installer_restart_button_visible(self, visible):
        self.missing_installer_restart_visible = visible

    def set_missing_installer_queue_progress(self, message):
        self.missing_installer_queue_progress = message


def _build_controller(view: _FakeView) -> AppController:
    controller = object.__new__(AppController)
    controller.root = _ImmediateRoot()
    controller.view = view
    controller.batch_summary_file_path = None
    controller.runtime_service = None
    controller.result_view_service = None
    controller.settings_model = None
    controller.comfyui_launcher_service = None
    controller.comfyui_manager_api_service = SimpleNamespace(get_version=lambda: OperationResult(False, message="offline"))
    controller.missing_node_install_orchestrator = None
    controller.dependency_preflight_service = None
    controller.dependency_install_planner = None
    controller.auto_open_html = _Var()
    controller.random_theme = _Var()
    controller.status_var = _Var("")
    controller._loaded_theme = ""
    controller._loaded_chrome_path = ""
    controller._loaded_comfyui_path = ""
    controller._loaded_comfyui_python_path = ""
    controller._loaded_retention_days = 30
    controller._comfyui_runtime_poll_scheduled = False
    controller._last_comfyui_runtime_state = "idle"
    controller._comfyui_browser_opened = False
    controller._manager_queue_poll_scheduled = False
    controller._missing_installer_step = 0
    controller._missing_installer_completed_steps = set()
    controller._missing_installer_selected_paths = []
    controller._missing_installer_analysis_result = None
    controller._missing_installer_install_plan = []
    controller._missing_installer_preflight_result = None
    controller._missing_installer_manual_items = []
    controller._missing_installer_recheck_paths = []
    controller._pending_missing_analysis = False
    controller._pending_missing_recheck = False
    controller._missing_installer_restart_available = False
    controller._missing_installer_launch_mode = "manager_only"
    controller._is_shutting_down = False
    controller._manager_runtime_status_label = "未启动"
    controller._manager_runtime_ready = False
    controller._manager_runtime_check_inflight = False
    controller._manager_runtime_last_check = 0.0
    controller._pending_runtime_wait_deadline = 0.0
    controller._missing_runtime_wait_logged = False
    return controller


def test_view_batch_html_only_opens_service_resolved_result(monkeypatch, tmp_path) -> None:
    view = _FakeView()
    controller = _build_controller(view)
    controller.batch_summary_file_path = str(tmp_path / "summary.csv")
    html_path = tmp_path / "summary.html"
    controller.result_view_service = SimpleNamespace(
        resolve_viewable_result=lambda path: OperationResult(
            True,
            data={"open_path": str(html_path), "generated_html": True},
        )
    )

    opened = []
    monkeypatch.setattr("ModelFinderV2_6.controller.webbrowser.open", lambda url: opened.append(url))

    AppController.view_batch_html(controller)

    assert view.logs == [f"尝试为 summary.csv 生成HTML视图..."]
    assert view.error_calls == []
    assert opened == [f"file:///{html_path}"]


def test_browse_workflow_input_routes_to_existing_handlers_by_mode() -> None:
    view = _FakeView()
    controller = _build_controller(view)
    calls = []
    controller.browse_workflow = lambda: calls.append("single")
    controller.browse_workflow_dir = lambda: calls.append("batch")

    AppController.browse_workflow_input(controller)
    view.workflow_mode = "batch"
    AppController.browse_workflow_input(controller)

    assert calls == ["single", "batch"]


def test_start_workflow_processing_reuses_existing_processing_entry_points() -> None:
    view = _FakeView()
    controller = _build_controller(view)
    calls = []
    controller.analyze_and_search = lambda: calls.append("single")
    controller.batch_process = lambda: calls.append("batch")

    AppController.start_workflow_processing(controller)
    view.workflow_mode = "batch"
    AppController.start_workflow_processing(controller)

    assert calls == ["single", "batch"]


def test_view_workflow_result_routes_to_existing_result_handlers() -> None:
    view = _FakeView()
    controller = _build_controller(view)
    calls = []
    controller.view_result = lambda: calls.append("single")
    controller.view_batch_html = lambda: calls.append("batch")

    AppController.view_workflow_result(controller)
    view.workflow_mode = "batch"
    AppController.view_workflow_result(controller)

    assert calls == ["single", "batch"]


def test_view_batch_html_surfaces_unknown_result_types_without_business_logic(monkeypatch, tmp_path) -> None:
    view = _FakeView()
    controller = _build_controller(view)
    controller.batch_summary_file_path = str(tmp_path / "summary.txt")
    controller.result_view_service = SimpleNamespace(
        resolve_viewable_result=lambda path: OperationResult(
            False,
            data={"source_path": path, "extension": ".txt"},
        )
    )

    monkeypatch.setattr("ModelFinderV2_6.controller.webbrowser.open", lambda url: None)

    AppController.view_batch_html(controller)

    assert view.error_calls == [("错误", "未知的文件类型: summary.txt")]


def test_load_settings_uses_runtime_service_for_chrome_resolution() -> None:
    view = _FakeView()
    controller = _build_controller(view)
    controller.settings_model = SimpleNamespace(
        load=lambda: {
            "auto_open_html": False,
            "random_theme": False,
            "theme": "flatly",
            "chrome_path": "",
            "comfyui_path": "C:/ComfyUI",
            "comfyui_python_path": "C:/Python/python.exe",
            "retention_days": 14,
        }
    )
    controller.runtime_service = SimpleNamespace(
        resolve_chrome_path=lambda configured_path: OperationResult(
            True,
            data={"chrome_path": "C:/Chrome/chrome.exe", "source": "detected"},
        )
    )

    applied_themes = []
    controller.apply_theme = lambda: applied_themes.append(view.selected_theme)

    AppController.load_settings(controller)

    assert controller.auto_open_html.get() is False
    assert controller.random_theme.get() is False
    assert controller._loaded_chrome_path == "C:/Chrome/chrome.exe"
    assert controller._loaded_comfyui_path == "C:/ComfyUI"
    assert controller._loaded_comfyui_python_path == "C:/Python/python.exe"
    assert controller._loaded_retention_days == 14
    assert view.selected_theme == "flatly"
    assert applied_themes == ["flatly"]
    assert any("自动检测到Chrome路径" in message for message in view.logs)


def test_cleanup_old_files_uses_runtime_service_and_recovers_ui_messages() -> None:
    view = _FakeView()
    controller = _build_controller(view)
    controller.runtime_service = SimpleNamespace(
        cleanup_results=lambda days: OperationResult(True, data={"deleted_count": 3, "retention_days": days})
    )

    AppController.cleanup_old_files(controller)

    assert view.ask_calls
    assert view.info_calls == [("清理完成", "已清理 3 个旧结果目录")]
    assert "开始清理 30 天前的旧文件..." in view.logs
    assert "清理完成，删除了 3 个目录。" in view.logs


def test_open_results_folder_only_uses_runtime_service_result(monkeypatch, tmp_path) -> None:
    view = _FakeView()
    controller = _build_controller(view)
    controller.runtime_service = SimpleNamespace(
        resolve_results_folder=lambda: OperationResult(True, data={"results_dir": str(tmp_path)})
    )

    opened = []
    monkeypatch.setattr("ModelFinderV2_6.controller.webbrowser.open", lambda url: opened.append(url))

    AppController.open_results_folder(controller)

    assert opened == [f"file:///{tmp_path}"]
    assert view.error_calls == []


def test_refresh_views_consume_operation_result_data_without_business_logic() -> None:
    view = _FakeView()
    controller = _build_controller(view)
    controller.irregular_mapping_service = SimpleNamespace(
        list_mappings=lambda: OperationResult(True, data=[{"id": "1"}], code="mappings_loaded")
    )
    controller.model_config_service = SimpleNamespace(
        get_snapshot=lambda: OperationResult(
            True,
            data=SimpleNamespace(
                node_types=["CheckpointLoaderSimple"],
                node_indices={"default": [0]},
                extensions=[".safetensors"],
            ),
            code="snapshot_loaded",
        )
    )

    AppController.refresh_irregular_mappings_view(controller)
    AppController.refresh_model_config_view(controller)

    assert view.loaded_mappings == [{"id": "1"}]
    assert view.loaded_node_types == ["CheckpointLoaderSimple"]
    assert view.loaded_node_indices == {"default": [0]}
    assert view.loaded_extensions == [".safetensors"]


def test_check_plugin_status_uses_validation_result_boundary(tmp_path) -> None:
    view = _FakeView()
    comfyui_path = tmp_path / "ComfyUI"
    comfyui_path.mkdir()
    view.comfyui_path = str(comfyui_path)
    controller = _build_controller(view)
    controller.plugin_repair_service = SimpleNamespace(
        validate_comfyui_dir=lambda path: OperationResult(False, code="invalid_comfyui_dir"),
        check_plugin_status=lambda path: OperationResult(
            True,
            data={"plugin_statuses": [{"name": "Joy Caption Two", "status": "需要修复"}]},
            message="done",
            code="plugin_status_checked",
        ),
    )

    AppController.check_plugin_status(controller)

    assert view.ask_calls
    assert view.plugin_status_updates == [("Joy Caption Two", "需要修复")]


def test_start_comfyui_updates_runtime_view_without_process_logic() -> None:
    view = _FakeView()
    view.comfyui_path = "C:/ComfyUI"
    view.comfyui_python_path = "C:/Python/python.exe"
    controller = _build_controller(view)
    controller.comfyui_launcher_service = SimpleNamespace(
        validate_paths=lambda comfyui_path, python_path, launch_mode=None: OperationResult(
            True,
            data={
                "comfyui_path": comfyui_path,
                "python_path": python_path,
                "command": [python_path, "-u", "main.py", "--enable-manager"],
                "url": "http://127.0.0.1:8188",
            },
            code="paths_valid",
        ),
        start=lambda comfyui_path, python_path, launch_mode=None: OperationResult(
            True,
            data={"state": "running", "pid": 2468, "command": [python_path, "-u", "main.py", "--enable-manager"], "url": "http://127.0.0.1:8188"},
            code="launch_started",
        ),
        drain_output=lambda: ["booting..."],
        get_runtime_snapshot=lambda: OperationResult(
            True,
            data={"state": "running", "pid": 2468, "command": [view.comfyui_python_path, "-u", "main.py", "--enable-manager"], "url": "http://127.0.0.1:8188"},
            code="runtime_snapshot",
        ),
        is_service_port_open=lambda: False,
    )
    controller.comfyui_manager_api_service = SimpleNamespace(get_version=lambda: OperationResult(True, data={"value": "3.32.3"}))

    AppController.start_comfyui(controller)
    AppController._poll_comfyui_runtime(controller)

    assert view.comfyui_launch_logs[0] == "启动命令: C:/Python/python.exe -u main.py --enable-manager"
    assert "访问地址: http://127.0.0.1:8188" in view.comfyui_launch_logs
    assert "ComfyUI 已启动，正在读取日志..." in view.comfyui_launch_logs
    assert "booting..." in view.comfyui_launch_logs
    assert view.comfyui_launch_status == "运行中"
    assert view.comfyui_launch_details == {"pid": 2468, "command": "C:/Python/python.exe -u main.py --enable-manager"}
    assert view.comfyui_launch_button_states[-1] == (False, True)


def test_refresh_comfyui_launch_runtime_consumes_service_snapshot() -> None:
    view = _FakeView()
    controller = _build_controller(view)
    controller._last_comfyui_runtime_state = "running"
    controller.comfyui_launcher_service = SimpleNamespace(
        get_runtime_snapshot=lambda: OperationResult(
            True,
            data={"state": "failed", "pid": 2468, "command": ["python.exe", "-u", "main.py"], "exit_code": 1, "url": "http://127.0.0.1:8188"},
            code="runtime_snapshot",
        ),
        is_service_port_open=lambda: False,
    )
    controller.comfyui_manager_api_service = SimpleNamespace(get_version=lambda: OperationResult(False, message="offline"))

    AppController.refresh_comfyui_launch_runtime(controller)

    assert view.comfyui_launch_status == "启动失败"
    assert view.comfyui_launch_details == {"pid": 2468, "command": "python.exe -u main.py"}
    assert view.comfyui_launch_button_states[-1] == (True, False)
    assert view.comfyui_launch_logs[-1] == "ComfyUI 已退出，退出码: 1"


def test_update_status_skips_duplicate_messages() -> None:
    view = _FakeView()
    controller = _build_controller(view)

    AppController.update_status(controller, "ComfyUI 运行中")
    AppController.update_status(controller, "ComfyUI 运行中")

    assert controller.status_var.get() == "ComfyUI 运行中"


def test_poll_comfyui_runtime_opens_browser_once_when_port_is_ready(monkeypatch) -> None:
    view = _FakeView()
    controller = _build_controller(view)
    opened_urls = []
    monkeypatch.setattr("ModelFinderV2_6.controller.webbrowser.open", lambda url: opened_urls.append(url))
    controller.comfyui_launcher_service = SimpleNamespace(
        drain_output=lambda: [],
        get_runtime_snapshot=lambda: OperationResult(
            True,
            data={"state": "running", "pid": 2468, "command": ["python.exe", "-u", "main.py"], "url": "http://127.0.0.1:8188"},
            code="runtime_snapshot",
        ),
        is_service_port_open=lambda: True,
        get_launch_url=lambda: "http://127.0.0.1:8188",
    )
    controller.comfyui_manager_api_service = SimpleNamespace(get_version=lambda: OperationResult(True, data={"value": "3.32.3"}))

    AppController._poll_comfyui_runtime(controller)
    AppController._poll_comfyui_runtime(controller)

    assert opened_urls == ["http://127.0.0.1:8188"]
    assert view.comfyui_launch_logs[-1] == "已打开浏览器: http://127.0.0.1:8188"


def test_analyze_missing_installer_workflows_stores_plan_and_advances_step() -> None:
    view = _FakeView()
    controller = _build_controller(view)
    controller.comfyui_launcher_service = SimpleNamespace(
        get_runtime_snapshot=lambda: OperationResult(True, data={"state": "running"}),
        is_service_port_open=lambda: True,
        is_running=lambda: True,
    )
    controller.comfyui_manager_api_service = SimpleNamespace(get_version=lambda: OperationResult(True, data={"value": "3.32.3"}))
    controller.missing_node_install_orchestrator = SimpleNamespace(
        prepare_install_plan=lambda paths: OperationResult(
            True,
            data={
                "workflow_files": paths,
                "analysis": {"total_workflows": 2, "total_node_types": 5, "missing_count": 2},
                "install_plan": [{"id": "impact-pack", "title": "Impact Pack", "selected": True, "missing_count": 2, "status": "待安装"}],
                "manual_items": [{"node_type": "UnknownNode", "reason": "未找到可自动映射的插件包。"}],
            },
        )
    )
    controller._manager_runtime_ready = True
    controller._manager_runtime_status_label = "可用"
    controller._missing_installer_selected_paths = ["a.json", "b.json"]

    AppController.analyze_missing_installer_workflows(controller)

    assert controller._missing_installer_step == 1
    assert controller._missing_installer_completed_steps == {0}
    assert view.missing_installer_summary["missing_count"] == 2
    assert view.missing_installer_packages[0]["id"] == "impact-pack"
    assert view.missing_installer_manual_items == [{"node_type": "UnknownNode", "reason": "未找到可自动映射的插件包。"}]


def test_run_missing_installer_dependency_preflight_advances_step_and_marks_blocked_items() -> None:
    view = _FakeView()
    controller = _build_controller(view)
    controller._missing_installer_install_plan = [
        {"id": "impact-pack", "title": "Impact Pack", "selected": True, "missing_count": 2, "status": "待安装", "metadata": {"id": "impact-pack"}}
    ]
    controller.dependency_preflight_service = SimpleNamespace(
        evaluate=lambda packages: OperationResult(
            True,
            data={
                "rows": [
                    {
                        "id": "impact-pack",
                        "title": "Impact Pack",
                        "source_plugins": ["Impact Pack"],
                        "strategy": "defer_manual",
                        "risk_level": "高",
                        "conclusion": "blocked",
                        "conclusion_label": "阻断安装",
                        "reasons": ["conflict"],
                    }
                ],
                "summary": {"safe": 0, "safe_with_policy": 0, "warning": 0, "blocked": 1},
                "blocked_package_ids": ["impact-pack"],
                "logs": ["预检完成：0 个安全，0 个需策略安装，0 个警告，1 个阻断。"],
            },
        )
    )

    AppController.run_missing_installer_dependency_preflight(controller)

    assert controller._missing_installer_step == 3
    assert controller._missing_installer_install_plan[0]["selected"] is False
    assert controller._missing_installer_install_plan[0]["status"] == "阻断安装"
    assert view.missing_installer_preflight_summary["blocked"] == 1
    assert view.missing_installer_preflight_rows[0]["id"] == "impact-pack"


def test_analyze_missing_installer_workflows_uses_missing_installer_start_mode_when_runtime_is_offline() -> None:
    view = _FakeView()
    controller = _build_controller(view)
    controller._missing_installer_selected_paths = ["a.json"]
    controller.comfyui_launcher_service = SimpleNamespace(
        get_runtime_snapshot=lambda: OperationResult(True, data={"state": "idle"}),
        is_service_port_open=lambda: False,
        is_running=lambda: False,
    )
    starts = []
    controller.start_comfyui_for_missing_installer = lambda: starts.append("missing_installer")

    AppController.analyze_missing_installer_workflows(controller)

    assert starts == ["missing_installer"]
    assert controller._pending_missing_analysis is True
    assert any("尚未就绪" in line for line in view.missing_installer_logs)


def test_analyze_missing_installer_workflows_only_logs_runtime_wait_once_while_pending() -> None:
    view = _FakeView()
    controller = _build_controller(view)
    controller._missing_installer_selected_paths = ["a.json"]
    controller._pending_missing_analysis = True
    controller._missing_runtime_wait_logged = True
    controller.comfyui_launcher_service = SimpleNamespace(
        get_runtime_snapshot=lambda: OperationResult(True, data={"state": "idle"}),
        is_service_port_open=lambda: False,
        is_running=lambda: False,
    )
    controller.start_comfyui_for_missing_installer = lambda: (_ for _ in ()).throw(
        AssertionError("should not restart again")
    )

    AppController.analyze_missing_installer_workflows(controller)

    assert not any("尚未就绪" in line for line in view.missing_installer_logs)


def test_add_missing_installer_quick_path_auto_analyzes_single_input(tmp_path) -> None:
    view = _FakeView()
    controller = _build_controller(view)
    workflow = tmp_path / "workflow.json"
    workflow.write_text("{}", encoding="utf-8")
    view.missing_installer_quick_path = str(workflow)
    calls = []
    controller.analyze_missing_installer_workflows = lambda: calls.append("analyze")

    AppController.add_missing_installer_quick_path(controller, auto_analyze=True)

    assert controller._missing_installer_selected_paths == [str(workflow)]
    assert calls == ["analyze"]


def test_browse_missing_installer_workflow_files_auto_analyzes_single_pick(monkeypatch) -> None:
    view = _FakeView()
    controller = _build_controller(view)
    calls = []
    controller.analyze_missing_installer_workflows = lambda: calls.append("analyze")
    monkeypatch.setattr(
        "ModelFinderV2_6.controller.filedialog.askopenfilenames",
        lambda **kwargs: ["C:/flows/one.json"],
    )

    AppController.browse_missing_installer_workflow_files(controller)

    assert controller._missing_installer_selected_paths == ["C:/flows/one.json"]
    assert calls == ["analyze"]


def test_start_comfyui_for_missing_installer_uses_default_mode() -> None:
    view = _FakeView()
    view.comfyui_path = "C:/ComfyUI"
    view.comfyui_python_path = "C:/Python/python.exe"
    controller = _build_controller(view)
    controller._missing_installer_launch_mode = "default"
    calls = []
    controller._start_comfyui_with_mode = lambda mode: calls.append(mode)

    AppController.start_comfyui_for_missing_installer(controller)

    assert calls == ["default"]
    assert "完整模式" in view.missing_installer_logs[-1]


def xest_start_comfyui_for_missing_installer_uses_manager_only_mode() -> None:
    view = _FakeView()
    view.comfyui_path = "C:/ComfyUI"
    view.comfyui_python_path = "C:/Python/python.exe"
    controller = _build_controller(view)
    controller._missing_installer_launch_mode = "default"
    calls = []
    controller._start_comfyui_with_mode = lambda mode: calls.append(mode)

    AppController.start_comfyui_for_missing_installer(controller)

    assert calls == ["default"]
    assert "完整模式" in view.missing_installer_logs[-1]


def xest_start_comfyui_for_missing_installer_uses_manager_only_mode_legacy() -> None:
    view = _FakeView()
    view.comfyui_path = "C:/ComfyUI"
    view.comfyui_python_path = "C:/Python/python.exe"
    controller = _build_controller(view)
    calls = []
    controller._start_comfyui_with_mode = lambda mode: calls.append(mode)

    AppController.start_comfyui_for_missing_installer(controller)

    assert calls == ["manager_only"]
    assert "仅加载 ComfyUI-Manager" in view.missing_installer_logs[-1]


def test_start_comfyui_for_missing_installer_uses_default_mode() -> None:
    view = _FakeView()
    view.comfyui_path = "C:/ComfyUI"
    view.comfyui_python_path = "C:/Python/python.exe"
    controller = _build_controller(view)
    controller._missing_installer_launch_mode = "default"
    calls = []
    controller._start_comfyui_with_mode = lambda mode: calls.append(mode)

    AppController.start_comfyui_for_missing_installer(controller)

    assert calls == ["default"]
    assert "Manager" in view.missing_installer_logs[-1]


def test_poll_comfyui_runtime_forwards_manager_install_logs_to_missing_installer() -> None:
    view = _FakeView()
    controller = _build_controller(view)
    controller.comfyui_launcher_service = SimpleNamespace(
        drain_output=lambda: [
            "[ComfyUI-Manager] Installation failed: security_level",
            "FETCH ComfyRegistry Data: 5/136",
            "plain workflow log",
        ],
        get_runtime_snapshot=lambda: OperationResult(
            True,
            data={"state": "running", "pid": 2468, "command": ["python.exe"], "url": "http://127.0.0.1:8188"},
            code="runtime_snapshot",
        ),
        is_service_port_open=lambda: False,
        get_launch_url=lambda: "http://127.0.0.1:8188",
    )
    controller.comfyui_manager_api_service = SimpleNamespace(get_version=lambda: OperationResult(False, message="offline"))

    AppController._poll_comfyui_runtime(controller)

    assert "[ComfyUI-Manager] Installation failed: security_level" in view.missing_installer_logs
    assert "FETCH ComfyRegistry Data: 5/136" not in view.missing_installer_logs
    assert "plain workflow log" not in view.missing_installer_logs


def test_maybe_open_comfyui_browser_uses_background_thread(monkeypatch) -> None:
    view = _FakeView()
    controller = _build_controller(view)
    controller.comfyui_launcher_service = SimpleNamespace(
        is_service_port_open=lambda: True,
        get_launch_url=lambda: "http://127.0.0.1:8188",
    )
    started = []

    class _FakeThread:
        def __init__(self, *, target=None, args=(), daemon=None):
            self.target = target
            self.args = args
            self.daemon = daemon

        def start(self):
            started.append((self.target, self.args, self.daemon))

    monkeypatch.setattr("ModelFinderV2_6.controller.threading.Thread", _FakeThread)

    AppController._maybe_open_comfyui_browser(controller, {"state": "running", "url": "http://127.0.0.1:8188"})

    assert started[0][1] == ("http://127.0.0.1:8188",)
    assert started[0][2] is True
    assert controller._comfyui_browser_opened is True


def test_controller_shutdown_stops_runtime_poll_and_calls_launcher_shutdown() -> None:
    view = _FakeView()
    controller = _build_controller(view)
    shutdown_calls = []
    controller.comfyui_launcher_service = SimpleNamespace(shutdown=lambda: shutdown_calls.append("shutdown"))
    controller._pending_missing_analysis = True
    controller._pending_missing_recheck = True

    AppController.shutdown(controller)

    assert controller._is_shutting_down is True
    assert controller._pending_missing_analysis is False
    assert controller._pending_missing_recheck is False
    assert shutdown_calls == ["shutdown"]


def test_schedule_comfyui_runtime_poll_uses_fast_interval_during_installation() -> None:
    view = _FakeView()
    controller = _build_controller(view)
    controller._missing_installer_step = 4
    controller._missing_installer_restart_available = False
    controller._missing_installer_install_plan = [{"id": "impact-pack", "status": "已排队"}]

    AppController._schedule_comfyui_runtime_poll(controller)

    assert controller.root.scheduled[0][0] == 100


def test_start_missing_installer_installation_updates_status_and_schedules_queue() -> None:
    view = _FakeView()
    controller = _build_controller(view)
    controller.comfyui_manager_api_service = SimpleNamespace(
        get_queue_status=lambda: OperationResult(
            True,
            data={"total_count": 1, "done_count": 1, "in_progress_count": 0, "is_processing": False},
        )
    )
    controller.missing_node_install_orchestrator = SimpleNamespace(
        execute_install_plan=lambda selected: OperationResult(
            True,
            data={"queued_package_ids": ["impact-pack"], "failed_packages": [], "restart_required": True},
        )
    )
    controller.dependency_install_planner = SimpleNamespace(
        build_execution_plan=lambda packages, preflight_result, safe_only=False: OperationResult(
            True,
            data={"executable_packages": packages, "blocked_packages": [], "skipped_packages": []},
        )
    )
    controller._missing_installer_install_plan = [
        {
            "id": "impact-pack",
            "title": "Impact Pack",
            "selected": True,
            "selectable": True,
            "queue_action": "install",
            "missing_count": 2,
            "status": "待安装",
            "metadata": {"id": "impact-pack"},
        }
    ]
    controller._missing_installer_preflight_result = {
        "rows": [
            {"id": "impact-pack", "conclusion": "safe", "strategy": "install", "reasons": []}
        ]
    }

    AppController.start_missing_installer_installation(controller)
    AppController._poll_manager_queue(controller)

    assert controller._missing_installer_step == 4
    assert view.missing_installer_install_rows[0]["status"] == "需重启生效"
    assert view.missing_installer_restart_visible is True


def test_start_missing_installer_installation_can_skip_preflight_and_queue_directly() -> None:
    view = _FakeView()
    controller = _build_controller(view)
    controller.comfyui_manager_api_service = SimpleNamespace(
        get_queue_status=lambda: OperationResult(
            True,
            data={"total_count": 1, "done_count": 1, "in_progress_count": 0, "is_processing": False},
        )
    )
    controller.missing_node_install_orchestrator = SimpleNamespace(
        execute_install_plan=lambda selected: OperationResult(
            True,
            data={"queued_package_ids": ["impact-pack"], "failed_packages": [], "restart_required": True},
        )
    )
    controller._missing_installer_install_plan = [
        {
            "id": "impact-pack",
            "title": "Impact Pack",
            "selected": True,
            "selectable": True,
            "queue_action": "install",
            "missing_count": 2,
            "status": "待安装",
            "metadata": {"id": "impact-pack"},
        }
    ]
    controller._missing_installer_preflight_result = None

    AppController.start_missing_installer_installation(controller, ignore_preflight=True)
    AppController._poll_manager_queue(controller)

    assert any("已跳过依赖预检" in line for line in view.missing_installer_logs)
    assert controller._missing_installer_step == 4
    assert view.missing_installer_install_rows[0]["status"] == "需重启生效"
