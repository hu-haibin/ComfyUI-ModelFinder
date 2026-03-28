import csv
import json
import re
import time
from pathlib import Path

import pytest

from ModelFinderV2_6.analysis_model import AnalysisModel
from ModelFinderV2_6.settings_model import SettingsModel
from ModelFinderV2_6.utils import create_html_view, get_mirror_link


pytestmark = pytest.mark.unit


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
                "文件名": "demo.safetensors",
                "节点ID": "123",
                "节点类型": "CheckpointLoaderSimple",
                "状态": "已处理",
                "下载链接": "https://huggingface.co/foo/bar/resolve/main/demo.safetensors",
                "镜像链接": "https://hf-mirror.com/foo/bar/resolve/main/demo.safetensors",
                "搜索链接": "https://www.liblib.art/modelinfo/demo",
            }
        )


def test_get_mirror_link_returns_empty_for_non_hf_url() -> None:
    assert get_mirror_link("") == ""
    assert get_mirror_link("https://example.com/model") == ""


def test_get_mirror_link_converts_hf_resolve_url() -> None:
    url = "https://huggingface.co/foo/bar/resolve/main/model.safetensors"
    assert get_mirror_link(url) == "https://hf-mirror.com/foo/bar/resolve/main/model.safetensors"


def test_create_html_view_generates_interactive_report(tmp_path: Path) -> None:
    csv_path = tmp_path / "sample.csv"
    _write_sample_csv(csv_path)

    html_path = create_html_view(str(csv_path))

    assert html_path is not None
    html = Path(html_path).read_text(encoding="utf-8")
    assert "data-col-key=" in html
    assert "addEventListener('click'" in html
    assert "links.join('\\n')" in html
    assert "toggleSort(''" not in html
    assert "demo.safetensors" in html
    assert "Copy Mirror Links" in html

    all_rows = re.search(r"const allRows = (.*?);\n\s*const columns = ", html, re.S)
    assert all_rows is not None
    rows = json.loads(all_rows.group(1))
    assert len(rows) == 1
    assert rows[0]["文件名"] == "demo.safetensors"


def test_settings_defaults_include_comfyui_path() -> None:
    assert "comfyui_path" in SettingsModel.DEFAULT_SETTINGS


def test_failed_cache_entries_are_not_reused() -> None:
    analysis = AnalysisModel()
    assert not analysis._is_cache_entry_valid({"url": "", "status": "未找到HF", "updated_at": time.time()})
    assert analysis._is_cache_entry_valid({"url": "https://huggingface.co/foo/bar", "status": "已处理", "updated_at": time.time()})


def test_search_candidates_include_fallback_site_and_stem_variant() -> None:
    analysis = AnalysisModel()
    candidates = analysis._get_search_candidates("demo.safetensors", "demo.safetensors", "CheckpointLoaderSimple")

    assert candidates[0]["search_site"] == "hf"
    assert any(candidate["search_site"] == "liblib" for candidate in candidates)
    assert any('site:huggingface.co "demo"' == candidate["site_query"] for candidate in candidates)
