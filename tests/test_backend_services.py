from pathlib import Path
from types import SimpleNamespace

import pytest

from ModelFinderV2_6.irregular_mapping_service import IrregularMappingService
from ModelFinderV2_6.model_config_service import ModelConfigService
from ModelFinderV2_6.plugin_repair_service import PluginRepairService


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
