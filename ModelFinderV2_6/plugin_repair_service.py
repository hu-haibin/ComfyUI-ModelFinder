import os
import subprocess
import sys

from .adapters.filesystem_adapter import FileSystemAdapter
from .operation_result import OperationResult


class PluginRepairService:
    def __init__(
        self,
        plugin_repair_model,
        helper_script_path_provider=None,
        process_launcher=None,
        platform_name=None,
        python_executable=None,
        filesystem=None,
    ):
        self.plugin_repair_model = plugin_repair_model
        self._helper_script_path_provider = helper_script_path_provider or self._default_helper_script_path
        self._process_launcher = process_launcher or subprocess.Popen
        self._platform_name = platform_name or sys.platform
        self._python_executable = python_executable or sys.executable
        self._filesystem = filesystem or FileSystemAdapter()

    @staticmethod
    def _default_helper_script_path():
        return os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "download_helper_joy_caption_two.py",
        )

    def get_plugins_for_view(self):
        plugins = [
            {
                "name": plugin.name,
                "description": plugin.description,
                "status": "\u672a\u68c0\u67e5",
            }
            for plugin in self.plugin_repair_model.get_all_plugins()
        ]
        return OperationResult(True, "\u63d2\u4ef6\u5217\u8868\u5df2\u52a0\u8f7d", plugins, code="plugins_loaded")

    def validate_comfyui_dir(self, dir_path):
        expected_items = ["main.py", "web", "comfy", "models"]
        found_count = 0
        for item in expected_items:
            if self._filesystem.exists(self._filesystem.join(dir_path, item)):
                found_count += 1

        is_valid = found_count >= len(expected_items) // 2
        return OperationResult(
            is_valid,
            "\u5df2\u68c0\u6d4b\u5230ComfyUI\u76ee\u5f55\u7ed3\u6784" if is_valid else "\u8be5\u8def\u5f84\u4e0d\u50cf\u6807\u51c6ComfyUI\u76ee\u5f55",
            {"matched_items": found_count, "expected_items": expected_items},
            code="valid_comfyui_dir" if is_valid else "invalid_comfyui_dir",
        )

    def check_plugin_status(self, comfyui_path):
        need_repair = set(self.plugin_repair_model.check_plugin_status(comfyui_path))
        plugin_statuses = []
        for plugin in self.plugin_repair_model.get_all_plugins():
            plugin_statuses.append(
                {
                    "name": plugin.name,
                    "status": "\u9700\u8981\u4fee\u590d" if plugin.name in need_repair else "\u5df2\u5b89\u88c5\u6b63\u786e",
                }
            )

        return OperationResult(
            True,
            "" if need_repair else "\u6240\u6709\u652f\u6301\u7684\u63d2\u4ef6\u90fd\u5df2\u6b63\u786e\u5b89\u88c5",
            {
                "need_repair": sorted(need_repair),
                "plugin_statuses": plugin_statuses,
            },
            code="plugin_status_checked",
        )

    def launch_repair_helper(self):
        script_path = self._helper_script_path_provider()
        if not self._filesystem.exists(script_path):
            return OperationResult(
                False,
                f"\u672a\u627e\u5230\u4fee\u590d\u52a9\u624b\u811a\u672c: {script_path}",
                {"script_path": script_path},
                code="helper_script_missing",
            )

        command = [self._python_executable, script_path]
        kwargs = {}
        if self._platform_name.startswith("win") and hasattr(subprocess, "CREATE_NEW_CONSOLE"):
            kwargs["creationflags"] = subprocess.CREATE_NEW_CONSOLE

        self._process_launcher(command, **kwargs)
        return OperationResult(
            True,
            "\u5df2\u542f\u52a8\u4fee\u590d\u52a9\u624b\uff0c\u8bf7\u5728\u65b0\u7a97\u53e3\u4e2d\u64cd\u4f5c",
            {"script_path": script_path},
            code="helper_launched",
        )
