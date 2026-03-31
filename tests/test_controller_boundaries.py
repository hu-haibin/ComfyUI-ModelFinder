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

    def update_plugin_status(self, name, status):
        self.plugin_status_updates.append((name, status))


def _build_controller(view: _FakeView) -> AppController:
    controller = object.__new__(AppController)
    controller.view = view
    controller.batch_summary_file_path = None
    controller.runtime_service = None
    controller.result_view_service = None
    controller.settings_model = None
    controller.auto_open_html = _Var()
    controller.random_theme = _Var()
    controller._loaded_theme = ""
    controller._loaded_chrome_path = ""
    controller._loaded_comfyui_path = ""
    controller._loaded_retention_days = 30
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
