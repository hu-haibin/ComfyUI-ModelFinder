import csv
from pathlib import Path

import pytest

from ModelFinderV2_6.workflow_processing_service import WorkflowProcessingService


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


def test_analyze_workflow_returns_csv_ready_when_missing_files_found(tmp_path: Path) -> None:
    csv_file = tmp_path / "missing.csv"
    csv_file.write_text("", encoding="utf-8")
    service = WorkflowProcessingService(
        _DummyAnalysisModel(
            missing_files=[{"node_id": 1, "node_type": "CheckpointLoaderSimple", "file_path": "demo.safetensors"}],
            csv_file=str(csv_file),
        )
    )

    result = service.analyze_workflow(str(tmp_path / "workflow.json"))

    assert result.status == "csv_ready"
    assert result.missing_count == 1
    assert result.csv_file == str(csv_file)


@pytest.mark.parametrize(
    ("search_result", "expected_status"),
    [
        (True, "nothing_to_search"),
        (False, "completed_without_html"),
    ],
)
def test_search_links_maps_non_html_outcomes(search_result, expected_status, tmp_path: Path) -> None:
    csv_file = tmp_path / "missing.csv"
    csv_file.write_text("", encoding="utf-8")
    service = WorkflowProcessingService(_DummyAnalysisModel(search_result=search_result))

    result = service.search_links(str(csv_file))

    assert result.status == expected_status
    assert result.html_file is None


def test_batch_process_returns_summary_rows_and_latest_missing_summary_csv(tmp_path: Path) -> None:
    processed_summary_csv = tmp_path / "batch_summary.csv"
    with processed_summary_csv.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=["工作流文件", "缺失数量"])
        writer.writeheader()
        writer.writerow({"工作流文件": "a.json", "缺失数量": "2"})
        writer.writerow({"工作流文件": "b.json", "缺失数量": "0"})

    results_root = tmp_path / "results"
    latest_dir = results_root / "2026-03-31"
    latest_dir.mkdir(parents=True)
    missing_summary_csv = latest_dir / "汇总缺失文件.csv"
    missing_summary_csv.write_text("", encoding="utf-8")

    service = WorkflowProcessingService(
        _DummyAnalysisModel(batch_result=str(processed_summary_csv)),
        results_folder_provider=lambda: str(results_root),
    )

    result = service.batch_process(str(tmp_path), "*.json;*")

    assert result.status == "summary_ready"
    assert result.processed_summary_csv == str(processed_summary_csv)
    assert result.all_missing_summary_csv == str(missing_summary_csv)
    assert result.batch_rows == [("a.json", "2"), ("b.json", "0")]
