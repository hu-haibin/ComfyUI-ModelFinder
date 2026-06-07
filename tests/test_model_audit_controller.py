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

    def after(self, delay, callback, *args):
        if delay == 0:
            callback(*args)
            return None
        self.scheduled.append((delay, callback, args))
        return None


class _FakeView:
    def __init__(self):
        self.comfyui_launch_logs = []
        self.model_audit_logs = []
        self.model_audit_runtime = None
        self.model_audit_paths = []
        self.model_audit_summary = {}
        self.model_audit_rows = []
        self.model_audit_unresolved = []
        self.model_audit_quick_path = ""
        self.comfyui_path = ""
        self.comfyui_python_path = ""

    def get_comfyui_path(self):
        return self.comfyui_path

    def get_comfyui_python_path(self):
        return self.comfyui_python_path

    def append_comfyui_launch_log(self, message):
        self.comfyui_launch_logs.append(message)

    def set_comfyui_launch_status(self, status):
        self.comfyui_launch_status = status

    def set_comfyui_launch_details(self, *, pid="", command=""):
        self.comfyui_launch_details = {"pid": pid, "command": command}

    def set_comfyui_launch_button_states(self, *, start_enabled, stop_enabled):
        self.comfyui_launch_buttons = (start_enabled, stop_enabled)

    def append_model_audit_log(self, message):
        self.model_audit_logs.append(message)

    def clear_model_audit_log(self):
        self.model_audit_logs.clear()

    def set_model_audit_runtime_status(self, *, comfyui_status, catalog_status, start_enabled):
        self.model_audit_runtime = (comfyui_status, catalog_status, start_enabled)

    def set_model_audit_selected_paths(self, paths):
        self.model_audit_paths = list(paths)
        if len(paths) == 1:
            self.model_audit_quick_path = paths[0]
        elif not paths:
            self.model_audit_quick_path = ""

    def get_model_audit_quick_path(self):
        return self.model_audit_quick_path

    def set_model_audit_quick_path(self, path):
        self.model_audit_quick_path = path

    def set_model_audit_summary(self, summary):
        self.model_audit_summary = dict(summary)

    def load_model_audit_rows(self, rows):
        self.model_audit_rows = [dict(item) for item in rows]

    def load_model_audit_unresolved_items(self, items):
        self.model_audit_unresolved = [dict(item) for item in items]

    def set_missing_installer_runtime_status(self, *, comfyui_status, manager_status, start_enabled):
        self.missing_runtime = (comfyui_status, manager_status, start_enabled)


def _build_controller(view: _FakeView) -> AppController:
    controller = object.__new__(AppController)
    controller.root = _ImmediateRoot()
    controller.view = view
    controller.status_var = _Var("")
    controller._loaded_comfyui_path = ""
    controller._loaded_comfyui_python_path = ""
    controller._last_comfyui_runtime_state = "idle"
    controller._is_shutting_down = False
    controller._comfyui_runtime_poll_scheduled = False
    controller._comfyui_browser_opened = False
    controller._pending_missing_analysis = False
    controller._pending_missing_recheck = False
    controller._pending_runtime_wait_deadline = 0.0
    controller._missing_runtime_wait_logged = False
    controller._manager_runtime_status_label = "未启动"
    controller._manager_runtime_ready = False
    controller._manager_runtime_check_inflight = False
    controller._manager_runtime_last_check = 0.0
    controller._missing_installer_step = 0
    controller._missing_installer_restart_available = False
    controller._missing_installer_install_plan = []
    controller._model_audit_selected_paths = []
    controller._model_audit_result = None
    controller._model_audit_pending = False
    controller._model_audit_wait_deadline = 0.0
    controller._model_audit_wait_logged = False
    controller._model_audit_catalog_loaded = False
    controller.comfyui_launcher_service = SimpleNamespace(
        get_runtime_snapshot=lambda: OperationResult(True, data={"state": "idle"}),
        is_service_port_open=lambda: False,
        drain_output=lambda: [],
    )
    controller.workflow_model_audit_service = SimpleNamespace(
        audit_workflows=lambda paths: OperationResult(
            True,
            data={"summary": {}, "items": [], "unresolved_items": [], "workflow_count": 0, "runtime_ready": True},
        )
    )
    controller.comfyui_runtime_model_catalog_service = SimpleNamespace(
        get_core_model_catalog=lambda: OperationResult(True, data={"summary": {}})
    )
    controller.refresh_missing_node_installer_runtime = lambda snapshot=None: {"comfyui_ready": False, "manager_ready": False}
    controller._maybe_open_comfyui_browser = lambda snapshot: None
    return controller


def test_add_model_audit_quick_path_updates_selected_inputs(monkeypatch) -> None:
    view = _FakeView()
    controller = _build_controller(view)
    view.model_audit_quick_path = r"C:\tmp\demo.json"

    monkeypatch.setattr("os.path.exists", lambda path: path == r"C:\tmp\demo.json")
    monkeypatch.setattr("os.path.isdir", lambda path: False)

    AppController.add_model_audit_quick_path(controller)

    assert controller._model_audit_selected_paths == [r"C:\tmp\demo.json"]
    assert view.model_audit_paths == [r"C:\tmp\demo.json"]


def test_run_model_audit_requires_runtime_ready() -> None:
    view = _FakeView()
    controller = _build_controller(view)
    controller._model_audit_selected_paths = [r"C:\tmp\demo.json"]

    AppController.run_model_audit(controller)

    assert any("ComfyUI 未运行" in line for line in view.model_audit_logs)
    assert controller.status_var.get() == "请先启动 ComfyUI"


def test_run_model_audit_updates_summary_and_rows() -> None:
    view = _FakeView()
    controller = _build_controller(view)
    controller._model_audit_selected_paths = [r"C:\tmp\demo.json"]
    controller.comfyui_launcher_service = SimpleNamespace(
        get_runtime_snapshot=lambda: OperationResult(True, data={"state": "running"}),
        is_service_port_open=lambda: True,
        drain_output=lambda: [],
    )
    controller.workflow_model_audit_service = SimpleNamespace(
        audit_workflows=lambda paths: OperationResult(
            True,
            data={
                "summary": {
                    "workflow_count": 1,
                    "core_reference_count": 2,
                    "resolved_count": 1,
                    "missing_core_count": 1,
                    "needs_extension_count": 0,
                },
                "items": [
                    {
                        "model_name": "demo.safetensors",
                        "model_type": "checkpoint",
                        "source_node_type": "CheckpointLoaderSimple",
                        "workflow_count": 1,
                        "status": "missing_core_model",
                        "sample_workflow": "demo.json",
                    }
                ],
                "unresolved_items": [],
                "workflow_count": 1,
                "runtime_ready": True,
            },
        )
    )

    AppController.run_model_audit(controller)

    assert view.model_audit_summary["workflow_count"] == 1
    assert view.model_audit_summary["missing_core_count"] == 1
    assert view.model_audit_rows[0]["model_name"] == "demo.safetensors"
    assert view.model_audit_runtime[1] == "已加载"


def test_start_comfyui_for_model_audit_starts_runtime_when_offline() -> None:
    view = _FakeView()
    controller = _build_controller(view)
    launched = []
    controller._start_comfyui_with_mode = lambda mode: launched.append(mode)
    controller._model_audit_selected_paths = [r"C:\tmp\demo.json"]

    AppController.start_comfyui_for_model_audit(controller)

    assert launched == ["default"]
    assert controller._model_audit_pending is True
    assert any("启动 ComfyUI" in line for line in view.model_audit_logs)


def test_poll_runtime_executes_pending_model_audit_once_service_is_ready() -> None:
    view = _FakeView()
    controller = _build_controller(view)
    controller._model_audit_pending = True
    controller._model_audit_wait_deadline = 9999999999
    executed = []
    controller._execute_model_audit = lambda: executed.append("audit")
    controller.comfyui_launcher_service = SimpleNamespace(
        drain_output=lambda: [],
        get_runtime_snapshot=lambda: OperationResult(
            True,
            data={"state": "running", "pid": 1, "command": ["python.exe", "-u", "main.py"], "url": "http://127.0.0.1:8188"},
        ),
        is_service_port_open=lambda: True,
    )
    controller.refresh_comfyui_launch_runtime = lambda snapshot=None: None

    AppController._poll_comfyui_runtime(controller)

    assert executed == ["audit"]
    assert controller._model_audit_pending is False
