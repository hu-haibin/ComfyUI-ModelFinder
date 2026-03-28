import csv
import importlib
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from ModelFinderV2_6.analysis_model import AnalysisModel
from ModelFinderV2_6.utils import create_html_view


pytestmark = pytest.mark.integration

RUNTIME_MODULES = [
    "run_model_finder",
    "ModelFinderV2_6.__init__",
    "ModelFinderV2_6.file_manager",
    "ModelFinderV2_6.utils",
    "ModelFinderV2_6.settings_model",
    "ModelFinderV2_6.model_config_manager",
    "ModelFinderV2_6.model_type_detector",
    "ModelFinderV2_6.irregular_names_model",
    "ModelFinderV2_6.model_registry",
    "ModelFinderV2_6.model_mover",
    "ModelFinderV2_6.plugin_repair",
    "ModelFinderV2_6.analysis_model",
    "ModelFinderV2_6.controller",
    "ModelFinderV2_6.view",
    "ModelFinderV2_6.model_finder",
]


def _write_sample_csv(csv_path: Path) -> None:
    fieldnames = [
        "序号",
        "文件名",
        "节点ID",
        "节点类型",
        "状态",
        "下载链接",
        "镜像链接",
        "搜索链接",
    ]
    with csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(
            {
                "序号": "1",
                "文件名": "alpha.safetensors",
                "节点ID": "11",
                "节点类型": "CheckpointLoaderSimple",
                "状态": "已处理",
                "下载链接": "https://huggingface.co/foo/bar/resolve/main/alpha.safetensors",
                "镜像链接": "https://hf-mirror.com/foo/bar/resolve/main/alpha.safetensors",
                "搜索链接": "",
            }
        )
        writer.writerow(
            {
                "序号": "2",
                "文件名": "beta.safetensors",
                "节点ID": "12",
                "节点类型": "Qwen3_VQA",
                "状态": "未找到HF",
                "下载链接": "",
                "镜像链接": "",
                "搜索链接": "",
            }
        )


@pytest.mark.parametrize("module_name", RUNTIME_MODULES)
def test_runtime_modules_importable(module_name: str) -> None:
    importlib.import_module(module_name)


def test_generated_html_script_passes_node_syntax_check(tmp_path: Path) -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed")

    csv_path = tmp_path / "integration.csv"
    _write_sample_csv(csv_path)
    html_path = Path(create_html_view(str(csv_path)))
    html = html_path.read_text(encoding="utf-8")

    script_match = re.search(r"<script>(.*?)</script>", html, re.S)
    assert script_match is not None

    js_path = tmp_path / "page.js"
    js_path.write_text(script_match.group(1), encoding="utf-8")

    result = subprocess.run([node, "--check", str(js_path)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr

    csv_rows = list(csv.DictReader(csv_path.open("r", encoding="utf-8-sig", newline="")))
    all_rows = re.search(r"const allRows = (.*?);\n\s*const columns = ", html, re.S)
    assert all_rows is not None
    rows = json.loads(all_rows.group(1))
    assert len(rows) == len(csv_rows)


class _DummyIrregularNamesModel:
    @staticmethod
    def get_corrected_name(name: str) -> str:
        return name


class _DummyView:
    def __init__(self, comfyui_path: str) -> None:
        self._comfyui_path = comfyui_path

    def get_comfyui_path(self) -> str:
        return self._comfyui_path


class _DummyController:
    def __init__(self, comfyui_path: str) -> None:
        self.view = _DummyView(comfyui_path)
        self.irregular_names_model = _DummyIrregularNamesModel()

    def get_loaded_comfyui_path(self) -> str:
        return self.view.get_comfyui_path()


def test_find_missing_models_uses_configured_comfyui_models_path(tmp_path: Path) -> None:
    comfyui_root = tmp_path / "ComfyUI"
    models_dir = comfyui_root / "models" / "checkpoints"
    models_dir.mkdir(parents=True)
    (models_dir / "demo.safetensors").write_text("x", encoding="utf-8")

    workflow_path = tmp_path / "workflow.json"
    workflow_path.write_text(
        json.dumps(
            {
                "nodes": [
                    {
                        "id": 1,
                        "type": "CheckpointLoaderSimple",
                        "widgets_values": ["demo.safetensors"],
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    analysis = AnalysisModel(controller=_DummyController(str(comfyui_root)))
    missing = analysis.find_missing_models(str(workflow_path))

    assert missing == []
