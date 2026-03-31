import csv
from pathlib import Path

import pytest

from ModelFinderV2_6.operation_result import OperationResult
from ModelFinderV2_6.workflow_processing_service import WorkflowProcessingService
from ModelFinderV2_6.workflow_report_service import ALL_MISSING_BASENAME, BATCH_SUMMARY_HEADERS


pytestmark = pytest.mark.unit


class _DummyAnalysisModel:
    def __init__(self, *, missing_files=None, csv_file=None, search_result=None, batch_result=None):
        self.missing_files = missing_files if missing_files is not None else []
        self.csv_file = csv_file
        self.search_result = search_result
        self.batch_result = batch_result

    def find_missing_models(self, workflow_file: str):
        return self.missing_files

    def create_csv_file(self, missing_files, output_basename: str):
        return self.csv_file

    def search_model_links(self, csv_file: str, progress_callback=None):
        return self.search_result

    def batch_process_workflows(self, directory: str, file_pattern: str, progress_callback=None):
        return self.batch_result


def test_analyze_workflow_returns_operation_result_when_csv_is_ready(tmp_path: Path) -> None:
    csv_file = tmp_path / "missing.csv"
    csv_file.write_text("", encoding="utf-8")
    service = WorkflowProcessingService(
        _DummyAnalysisModel(
            missing_files=[{"node_id": 1, "node_type": "CheckpointLoaderSimple", "file_path": "demo.safetensors"}],
            csv_file=str(csv_file),
        )
    )

    result = service.analyze_workflow(str(tmp_path / "workflow.json"))

    assert result.success
    assert result.code == "csv_ready"
    assert result.data["missing_count"] == 1
    assert result.data["csv_file"] == str(csv_file)


@pytest.mark.parametrize(
    ("search_result", "expected_code"),
    [
        (True, "nothing_to_search"),
        (False, "completed_without_html"),
        (OperationResult(True, data={"html_file": "demo.html"}, code="html_ready"), "html_ready"),
    ],
)
def test_search_links_normalizes_legacy_and_operation_results(search_result, expected_code, tmp_path: Path) -> None:
    csv_file = tmp_path / "missing.csv"
    csv_file.write_text("", encoding="utf-8")
    service = WorkflowProcessingService(_DummyAnalysisModel(search_result=search_result))

    result = service.search_links(str(csv_file))

    assert result.code == expected_code


def test_batch_process_returns_summary_rows_and_latest_missing_summary_csv(tmp_path: Path) -> None:
    processed_summary_csv = tmp_path / "batch_summary.csv"
    with processed_summary_csv.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=[BATCH_SUMMARY_HEADERS[0], BATCH_SUMMARY_HEADERS[2]])
        writer.writeheader()
        writer.writerow({BATCH_SUMMARY_HEADERS[0]: "a.json", BATCH_SUMMARY_HEADERS[2]: "2"})
        writer.writerow({BATCH_SUMMARY_HEADERS[0]: "b.json", BATCH_SUMMARY_HEADERS[2]: "0"})

    results_root = tmp_path / "results"
    latest_dir = results_root / "2026-03-31"
    latest_dir.mkdir(parents=True)
    missing_summary_csv = latest_dir / f"{ALL_MISSING_BASENAME}.csv"
    missing_summary_csv.write_text("", encoding="utf-8")

    service = WorkflowProcessingService(
        _DummyAnalysisModel(batch_result=str(processed_summary_csv)),
        results_folder_provider=lambda: str(results_root),
    )

    result = service.batch_process(str(tmp_path), "*.json;*")

    assert result.success
    assert result.code == "summary_ready"
    assert result.data["processed_summary_csv"] == str(processed_summary_csv)
    assert result.data["all_missing_summary_csv"] == str(missing_summary_csv)
    assert result.data["batch_rows"] == [("a.json", "2"), ("b.json", "0")]
