import json
import os
import subprocess
import sys

from .operation_result import OperationResult


class DependencyEnvironmentService:
    def __init__(
        self,
        *,
        python_path_provider,
        comfyui_path_provider,
        command_runner=None,
    ):
        self._python_path_provider = python_path_provider
        self._comfyui_path_provider = comfyui_path_provider
        self._command_runner = command_runner or self._default_command_runner

    def collect_environment_snapshot(self) -> OperationResult:
        python_path = (self._python_path_provider() or "").strip() or sys.executable
        comfyui_path = (self._comfyui_path_provider() or "").strip()
        if python_path and not os.path.exists(python_path):
            return OperationResult(False, f"Python 路径不存在: {python_path}", code="dependency_python_missing")

        pip_packages = {}
        pip_result = self._run_python(
            python_path,
            ["-m", "pip", "list", "--format=json"],
        )
        if pip_result["success"]:
            try:
                pip_packages = {
                    str(item.get("name", "")).strip().lower(): str(item.get("version", "")).strip()
                    for item in json.loads(pip_result["stdout"] or "[]")
                    if item.get("name")
                }
            except Exception:
                pip_packages = {}

        runtime_result = self._run_python(
            python_path,
            [
                "-c",
                (
                    "import json, platform, sys\n"
                    "payload={'python_version': platform.python_version(), 'platform': sys.platform}\n"
                    "try:\n"
                    " import torch\n"
                    " payload['torch_version']=getattr(torch,'__version__',None)\n"
                    " payload['torch_cuda']=getattr(getattr(torch,'version',None),'cuda',None)\n"
                    "except Exception:\n"
                    " payload['torch_version']=None\n"
                    " payload['torch_cuda']=None\n"
                    "print(json.dumps(payload))\n"
                ),
            ],
        )
        runtime_data = {"python_version": "", "platform": sys.platform, "torch_version": None, "torch_cuda": None}
        if runtime_result["success"]:
            try:
                runtime_data.update(json.loads(runtime_result["stdout"] or "{}"))
            except Exception:
                pass

        installed_plugins = []
        if comfyui_path:
            custom_nodes_dir = os.path.join(comfyui_path, "custom_nodes")
            if os.path.isdir(custom_nodes_dir):
                installed_plugins = sorted(
                    name
                    for name in os.listdir(custom_nodes_dir)
                    if os.path.isdir(os.path.join(custom_nodes_dir, name)) and not name.startswith("__")
                )

        return OperationResult(
            True,
            "Dependency environment snapshot collected.",
            {
                "python_path": python_path,
                "python_version": runtime_data.get("python_version") or "",
                "platform": runtime_data.get("platform") or sys.platform,
                "torch_version": runtime_data.get("torch_version"),
                "torch_cuda": runtime_data.get("torch_cuda"),
                "pip_packages": pip_packages,
                "installed_plugins": installed_plugins,
                "comfyui_path": comfyui_path,
                "pip_list_available": pip_result["success"],
            },
            code="dependency_environment_loaded",
        )

    def _run_python(self, python_path, arguments):
        command = [python_path, *arguments]
        return self._command_runner(command)

    @staticmethod
    def _default_command_runner(command):
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
                timeout=15,
            )
            return {
                "success": completed.returncode == 0,
                "returncode": completed.returncode,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
            }
        except Exception as exc:
            return {"success": False, "returncode": -1, "stdout": "", "stderr": str(exc)}
