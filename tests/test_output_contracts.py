import csv
import json
from pathlib import Path

import pytest

from ModelFinderV2_6.analysis_model import AnalysisModel
from ModelFinderV2_6.utils import create_html_view
from ModelFinderV2_6.workflow_report_service import (
    ALL_MISSING_BASENAME,
    BATCH_RESULTS_BASENAME,
    BATCH_SUMMARY_HEADERS,
    COL_ACTUAL_SEARCH_TERM,
    COL_HIT_LINK,
    COL_HIT_TITLE,
    COL_MATCH_REASON,
    COL_NORMALIZED_FILE,
    COL_ORIGINAL_FILE,
    COL_REMOTE_FILE,
    COL_SUSPICIOUS,
    MISSING_FILES_HEADERS,
    WorkflowReportService,
)


pytestmark = pytest.mark.unit


def _build_report_service(output_dir: Path) -> WorkflowReportService:
    def _output_path_provider(basename: str, extension: str) -> str:
        return str(output_dir / f"{basename}.{extension}")

    return WorkflowReportService(output_path_provider=_output_path_provider)


def test_missing_files_csv_contract_keeps_headers_merge_and_search_link(tmp_path: Path) -> None:
    analysis = AnalysisModel(report_service=_build_report_service(tmp_path))

    csv_path = analysis.create_csv_file(
        [
            {"node_id": 2, "node_type": "CheckpointLoaderSimple", "file_path": "b-model.safetensors"},
            {"node_id": 1, "node_type": "CheckpointLoaderSimple", "file_path": "a-model.safetensors"},
            {"node_id": 3, "node_type": "CheckpointLoaderSimple", "file_path": "a-model.safetensors"},
        ],
        "demo-workflow",
    )

    assert csv_path == str(tmp_path / "demo-workflow.csv")
    with Path(csv_path).open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)

    assert reader.fieldnames == MISSING_FILES_HEADERS
    assert [row[MISSING_FILES_HEADERS[3]] for row in rows] == ["a-model.safetensors", "b-model.safetensors"]
    assert rows[0][MISSING_FILES_HEADERS[1]] == "1,3"
    assert rows[0][MISSING_FILES_HEADERS[2]] == "CheckpointLoaderSimple"
    assert rows[0][MISSING_FILES_HEADERS[7]].startswith("https://www.bing.com/search?q=")
    assert rows[0][COL_REMOTE_FILE] == ""
    assert rows[0][COL_ORIGINAL_FILE] == "a-model.safetensors"
    assert rows[0][COL_NORMALIZED_FILE] == "a-model.safetensors"
    assert rows[0][COL_ACTUAL_SEARCH_TERM].startswith('site:huggingface.co')


def test_batch_summary_contract_keeps_filename_and_columns(tmp_path: Path) -> None:
    analysis = AnalysisModel(report_service=_build_report_service(tmp_path))

    workflow_a = tmp_path / "workflow_a.json"
    workflow_b = tmp_path / "workflow_b.json"
    workflow_a.write_text(
        json.dumps(
            {
                "nodes": [
                    {
                        "id": 1,
                        "type": "CheckpointLoaderSimple",
                        "widgets_values": ["missing-a.safetensors"],
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    workflow_b.write_text(
        json.dumps(
            {
                "nodes": [
                    {
                        "id": 2,
                        "type": "CheckpointLoaderSimple",
                        "widgets_values": ["missing-b.safetensors"],
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    batch_summary_csv = analysis.batch_process_workflows(str(tmp_path), "*.json")

    assert batch_summary_csv == str(tmp_path / f"{BATCH_RESULTS_BASENAME}.csv")
    assert (tmp_path / f"{ALL_MISSING_BASENAME}.csv").exists()

    with Path(batch_summary_csv).open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)

    assert reader.fieldnames == BATCH_SUMMARY_HEADERS
    assert [row[BATCH_SUMMARY_HEADERS[0]] for row in rows] == ["workflow_a.json", "workflow_b.json"]
    assert [row[BATCH_SUMMARY_HEADERS[2]] for row in rows] == ["1", "1"]


def test_html_report_contract_keeps_core_fields_and_links(tmp_path: Path) -> None:
    csv_path = tmp_path / "report.csv"
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=MISSING_FILES_HEADERS)
        writer.writeheader()
        writer.writerow(
            {
                MISSING_FILES_HEADERS[0]: "1",
                MISSING_FILES_HEADERS[1]: "100",
                MISSING_FILES_HEADERS[2]: "CheckpointLoaderSimple",
                MISSING_FILES_HEADERS[3]: "demo.safetensors",
                MISSING_FILES_HEADERS[4]: "已处理",
                MISSING_FILES_HEADERS[5]: "https://huggingface.co/foo/bar/resolve/main/demo.safetensors",
                MISSING_FILES_HEADERS[6]: "https://hf-mirror.com/foo/bar/resolve/main/demo.safetensors",
                MISSING_FILES_HEADERS[7]: "https://www.bing.com/search?q=demo",
                COL_REMOTE_FILE: "demo.safetensors",
                COL_ORIGINAL_FILE: "wan2.1_t2v_14b_fp16.safetensors",
                COL_NORMALIZED_FILE: "wan2.1_t2v_14b_fp16.safetensors",
                COL_ACTUAL_SEARCH_TERM: 'site:huggingface.co "wan2.1_t2v_14b_fp16"',
                COL_HIT_TITLE: "Wan2.2 T2V 14B fp16",
                COL_HIT_LINK: "https://huggingface.co/Wan-AI/Wan2.2-T2V-14B",
                COL_MATCH_REASON: "可疑点: 版本号不一致(wan2.1 vs wan2.2)",
                COL_SUSPICIOUS: "是",
            }
        )

    html_path = create_html_view(str(csv_path))

    assert html_path is not None
    html = Path(html_path).read_text(encoding="utf-8")
    assert MISSING_FILES_HEADERS[3] in html
    assert MISSING_FILES_HEADERS[5] in html
    assert MISSING_FILES_HEADERS[6] in html
    assert MISSING_FILES_HEADERS[7] in html
    assert "https://huggingface.co/foo/bar/resolve/main/demo.safetensors" in html
    assert "https://hf-mirror.com/foo/bar/resolve/main/demo.safetensors" in html
    assert "https://www.bing.com/search?q=demo" in html
    assert "demo.safetensors" in html
    assert "工作流" in html
    assert "云端" in html
    assert f'"label": "{COL_REMOTE_FILE}"' not in html
    assert "匹配证据" in html
    assert "<details" in html
    assert "Wan2.2 T2V 14B fp16" in html
    assert "版本号不一致" in html
    assert "table-layout: auto;" in html
