import os
import queue
import socket
import subprocess
import threading
from typing import Callable, Optional

from .adapters.filesystem_adapter import FileSystemAdapter
from .operation_result import OperationResult


class ComfyUILauncherService:
    MANAGER_ONLY_MODE = "manager_only"
    DEFAULT_MODE = "default"
    _MANAGER_DIR_CANDIDATES = {"comfyui-manager", "comfyui_manager"}

    def __init__(
        self,
        *,
        process_launcher: Callable[..., subprocess.Popen] = subprocess.Popen,
        process_tree_killer: Optional[Callable[[int], object]] = None,
        port_checker: Optional[Callable[[str, int, float], bool]] = None,
        platform_name: Optional[str] = None,
        filesystem: Optional[FileSystemAdapter] = None,
        host: str = "127.0.0.1",
        port: int = 8188,
        enable_manager: bool = True,
    ):
        self._process_launcher = process_launcher
        self._process_tree_killer = process_tree_killer or self._default_process_tree_killer
        self._port_checker = port_checker or self._default_port_checker
        self._platform_name = platform_name or os.name
        self._filesystem = filesystem or FileSystemAdapter()
        self._host = host
        self._port = port
        self._enable_manager = enable_manager
        self._process = None
        self._command = []
        self._cwd = ""
        self._output_queue = queue.Queue()
        self._exit_code = None
        self._state = "idle"
        self._stop_requested = False
        self._reader_thread = None
        self._last_pid = None
        self._launch_mode = self.DEFAULT_MODE

    def validate_paths(self, comfyui_path: str, python_path: str, launch_mode: str = DEFAULT_MODE) -> OperationResult:
        normalized_comfyui = (comfyui_path or "").strip()
        normalized_python = (python_path or "").strip()

        if not normalized_comfyui:
            return OperationResult(False, "请选择 ComfyUI 路径", code="missing_comfyui_path")
        if not self._filesystem.exists(normalized_comfyui) or not self._filesystem.is_dir(normalized_comfyui):
            return OperationResult(False, f"ComfyUI 路径不存在: {normalized_comfyui}", code="invalid_comfyui_path")

        main_py = self._filesystem.join(normalized_comfyui, "main.py")
        if not self._filesystem.exists(main_py):
            return OperationResult(False, f"ComfyUI 目录中未找到 main.py: {normalized_comfyui}", code="missing_main_py")

        if not normalized_python:
            return OperationResult(False, "请选择 Python 路径", code="missing_python_path")
        if not self._filesystem.exists(normalized_python) or self._filesystem.is_dir(normalized_python):
            return OperationResult(False, f"Python 路径不存在: {normalized_python}", code="invalid_python_path")
        if self.is_service_port_open():
            return OperationResult(
                False,
                f"端口 {self._port} 已被占用，请先关闭占用该端口的程序",
                {"port": self._port, "url": self.get_launch_url()},
                code="port_in_use",
            )

        command = self._build_command(normalized_comfyui, normalized_python, launch_mode)

        return OperationResult(
            True,
            "路径校验通过",
            {
                "comfyui_path": normalized_comfyui,
                "python_path": normalized_python,
                "command": command,
                "launch_mode": launch_mode,
                "port": self._port,
                "url": self.get_launch_url(),
            },
            code="paths_valid",
        )

    def start(self, comfyui_path: str, python_path: str, launch_mode: str = DEFAULT_MODE) -> OperationResult:
        if self.is_running():
            return OperationResult(
                False,
                "ComfyUI 已在运行中",
                self.get_runtime_snapshot().data,
                code="already_running",
            )

        validation_result = self.validate_paths(comfyui_path, python_path, launch_mode=launch_mode)
        if not validation_result.success:
            return validation_result

        normalized_comfyui = validation_result.data["comfyui_path"]
        command = validation_result.data["command"]
        self._reset_output_queue()
        self._command = list(command)
        self._cwd = normalized_comfyui
        self._exit_code = None
        self._stop_requested = False
        self._launch_mode = validation_result.data.get("launch_mode", self.DEFAULT_MODE)

        try:
            self._process = self._process_launcher(
                command,
                cwd=normalized_comfyui,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
        except Exception as exc:
            self._process = None
            self._state = "failed"
            return OperationResult(
                False,
                f"启动 ComfyUI 失败: {exc}",
                {"command": list(command), "pid": None, "exit_code": None, "state": self._state},
                code="launch_failed",
            )

        self._state = "running"
        self._last_pid = getattr(self._process, "pid", None)
        self._reader_thread = threading.Thread(target=self._read_process_output, daemon=True)
        self._reader_thread.start()
        return OperationResult(
            True,
            "ComfyUI 已启动",
            self.get_runtime_snapshot().data,
            code="launch_started",
        )

    def stop(self) -> OperationResult:
        process = self._process
        if not process or process.poll() is not None:
            snapshot = self.get_runtime_snapshot().data
            if self._state == "idle":
                self._state = "stopped"
                snapshot = self.get_runtime_snapshot().data
            return OperationResult(True, "当前没有运行中的 ComfyUI 进程", snapshot, code="stop_noop")

        self._stop_requested = True
        try:
            if str(self._platform_name).startswith(("nt", "win")):
                self._process_tree_killer(process.pid)
            else:
                process.terminate()
                process.wait(timeout=5)
        except Exception:
            try:
                process.kill()
            except Exception:
                pass

        self._last_pid = getattr(process, "pid", None)
        self._state = "stopped"
        self._exit_code = process.poll()
        self._process = None
        self._cleanup_reader_thread(process)
        return OperationResult(True, "ComfyUI 已停止", self.get_runtime_snapshot().data, code="stop_completed")

    def shutdown(self) -> OperationResult:
        result = self.stop()
        process = self._process
        if process is None or process.poll() is not None:
            self._cleanup_reader_thread(process)
        return result

    def is_running(self) -> bool:
        process = self._process
        return bool(process and process.poll() is None)

    def get_runtime_snapshot(self) -> OperationResult:
        pid = self._last_pid
        exit_code = self._exit_code
        if self._process:
            pid = getattr(self._process, "pid", None)
            self._last_pid = pid
            polled_code = self._process.poll()
            if polled_code is None:
                self._state = "running"
            else:
                exit_code = polled_code
                self._exit_code = polled_code
                if self._stop_requested or polled_code == 0:
                    self._state = "stopped"
                else:
                    self._state = "failed"

        return OperationResult(
            True,
            "Runtime snapshot ready.",
            {
                "command": list(self._command),
                "cwd": self._cwd,
                "pid": pid,
                "exit_code": exit_code,
                "state": self._state,
                "launch_mode": self._launch_mode,
                "port": self._port,
                "url": self.get_launch_url(),
            },
            code="runtime_snapshot",
        )

    def is_service_port_open(self, timeout: float = 0.2) -> bool:
        return bool(self._port_checker(self._host, self._port, timeout))

    def get_launch_url(self) -> str:
        return f"http://{self._host}:{self._port}"

    def drain_output(self) -> list[str]:
        lines = []
        while True:
            try:
                lines.append(self._output_queue.get_nowait())
            except queue.Empty:
                break
        return lines

    def _read_process_output(self) -> None:
        process = self._process
        if not process or not process.stdout:
            return

        try:
            for raw_line in iter(process.stdout.readline, ""):
                if raw_line == "":
                    break
                self._output_queue.put(raw_line.rstrip("\r\n"))
        finally:
            try:
                process.stdout.close()
            except Exception:
                pass

    def _build_command(self, comfyui_path: str, python_path: str, launch_mode: str) -> list[str]:
        command = [python_path, "-u", "main.py"]

        if self._enable_manager or launch_mode == self.MANAGER_ONLY_MODE:
            command.append("--enable-manager")

        if launch_mode == self.MANAGER_ONLY_MODE:
            command.append("--disable-all-custom-nodes")
            manager_dirs = self._detect_manager_directories(comfyui_path)
            if manager_dirs:
                command.append("--whitelist-custom-nodes")
                command.extend(manager_dirs)

        return command

    def _detect_manager_directories(self, comfyui_path: str) -> list[str]:
        manager_dirs = []
        custom_nodes_dir = self._filesystem.join(comfyui_path, "custom_nodes")
        if self._filesystem.exists(custom_nodes_dir) and self._filesystem.is_dir(custom_nodes_dir):
            try:
                for name in self._filesystem.listdir(custom_nodes_dir):
                    if str(name).strip().lower() in self._MANAGER_DIR_CANDIDATES:
                        manager_dirs.append(name)
            except OSError:
                manager_dirs = []

        if not manager_dirs:
            manager_dirs = ["ComfyUI-Manager"]

        return manager_dirs

    def _reset_output_queue(self) -> None:
        self._output_queue = queue.Queue()

    def _cleanup_reader_thread(self, process=None, timeout: float = 1.0) -> None:
        process = process or self._process
        stdout = getattr(process, "stdout", None) if process else None
        if stdout is not None:
            try:
                stdout.close()
            except Exception:
                pass

        reader_thread = self._reader_thread
        if reader_thread and reader_thread.is_alive() and reader_thread is not threading.current_thread():
            reader_thread.join(timeout=timeout)

        if reader_thread and not reader_thread.is_alive():
            self._reader_thread = None

    @staticmethod
    def _default_process_tree_killer(pid: int) -> object:
        return subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(pid)],
            capture_output=True,
            text=True,
            check=False,
        )

    @staticmethod
    def _default_port_checker(host: str, port: int, timeout: float) -> bool:
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except OSError:
            return False
