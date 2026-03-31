import os
import subprocess
import sys

from .operation_result import OperationResult


class PluginRepairService:
    def __init__(
        self,
        plugin_repair_model,
        helper_script_path_provider=None,
        process_launcher=None,
        platform_name=None,
        python_executable=None,
    ):
        self.plugin_repair_model = plugin_repair_model
        self._helper_script_path_provider = helper_script_path_provider or self._default_helper_script_path
        self._process_launcher = process_launcher or subprocess.Popen
        self._platform_name = platform_name or sys.platform
        self._python_executable = python_executable or sys.executable

    @staticmethod
    def _default_helper_script_path():
        return os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "download_helper_joy_caption_two.py",
        )

    def get_plugins_for_view(self):
        return [
            {
                "name": plugin.name,
                "description": plugin.description,
                "status": "未检查",
            }
            for plugin in self.plugin_repair_model.get_all_plugins()
        ]

    def validate_comfyui_dir(self, dir_path):
        expected_items = ["main.py", "web", "comfy", "models"]
        found_count = 0
        for item in expected_items:
            if os.path.exists(os.path.join(dir_path, item)):
                found_count += 1
        return found_count >= len(expected_items) // 2

    def check_plugin_status(self, comfyui_path):
        need_repair = set(self.plugin_repair_model.check_plugin_status(comfyui_path))
        plugin_statuses = []
        for plugin in self.plugin_repair_model.get_all_plugins():
            plugin_statuses.append(
                {
                    "name": plugin.name,
                    "status": "需要修复" if plugin.name in need_repair else "已安装正确",
                }
            )

        return OperationResult(
            True,
            "" if need_repair else "所有支持的插件都已正确安装。",
            {
                "need_repair": sorted(need_repair),
                "plugin_statuses": plugin_statuses,
            },
        )

    def launch_repair_helper(self):
        script_path = self._helper_script_path_provider()
        if not os.path.exists(script_path):
            return OperationResult(False, f"未找到修复助手脚本: {script_path}")

        command = [self._python_executable, script_path]
        kwargs = {}
        if self._platform_name.startswith("win") and hasattr(subprocess, "CREATE_NEW_CONSOLE"):
            kwargs["creationflags"] = subprocess.CREATE_NEW_CONSOLE

        self._process_launcher(command, **kwargs)
        return OperationResult(
            True,
            "已启动修复助手，请在新窗口中操作",
            {"script_path": script_path},
        )
