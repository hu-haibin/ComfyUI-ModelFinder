import csv
import logging
from typing import Callable, List, Optional, Tuple

from .adapters.filesystem_adapter import FileSystemAdapter
from .file_manager import get_results_folder
from .operation_result import OperationResult
from .workflow_report_service import ALL_MISSING_BASENAME, BATCH_SUMMARY_HEADERS


logger = logging.getLogger(__name__)


class WorkflowProcessingService:
    def __init__(
        self,
        analysis_model,
        results_folder_provider: Callable[[], str] = get_results_folder,
        filesystem: Optional[FileSystemAdapter] = None,
    ):
        self.analysis_model = analysis_model
        self._results_folder_provider = results_folder_provider
        self._filesystem = filesystem or FileSystemAdapter()

    def analyze_workflow(self, workflow_file: str) -> OperationResult:
        missing_files = self.analysis_model.find_missing_models(workflow_file)
        if not missing_files:
            return OperationResult(
                True,
                "No missing files were found.",
                {"missing_count": 0, "csv_file": None},
                code="no_missing",
            )

        csv_file = self.analysis_model.create_csv_file(missing_files, self._filesystem.basename(workflow_file))
        if not csv_file:
            return OperationResult(
                False,
                "Failed to create the missing-files CSV.",
                {"missing_count": len(missing_files), "csv_file": None},
                code="csv_failed",
            )

        return OperationResult(
            True,
            "Missing-files CSV is ready.",
            {"missing_count": len(missing_files), "csv_file": csv_file},
            code="csv_ready",
        )

    def search_links(self, csv_file: str, progress_callback=None) -> OperationResult:
        search_result = self.analysis_model.search_model_links(csv_file, progress_callback=progress_callback)
        if isinstance(search_result, OperationResult):
            return search_result

        if isinstance(search_result, str) and self._filesystem.exists(search_result):
            return OperationResult(
                True,
                "HTML result is ready.",
                {"html_file": search_result},
                code="html_ready",
            )
        if search_result is True:
            return OperationResult(
                True,
                "All models were already processed or available.",
                {"html_file": None},
                code="nothing_to_search",
            )
        return OperationResult(
            False,
            "Search completed without generating HTML.",
            {"html_file": None},
            code="completed_without_html",
        )

    def batch_process(self, directory: str, file_pattern: str, progress_callback=None) -> OperationResult:
        processed_summary_csv = self.analysis_model.batch_process_workflows(
            directory,
            file_pattern,
            progress_callback=progress_callback,
        )
        all_missing_summary_csv = self.find_latest_missing_summary_csv()

        if processed_summary_csv is True:
            return OperationResult(
                True,
                "Batch processing finished with no missing files.",
                {
                    "processed_summary_csv": None,
                    "all_missing_summary_csv": all_missing_summary_csv,
                    "batch_rows": [],
                },
                code="no_missing",
            )

        if isinstance(processed_summary_csv, str) and self._filesystem.exists(processed_summary_csv):
            batch_rows = self.load_batch_rows(processed_summary_csv)
            return OperationResult(
                True,
                "Batch summary CSV is ready.",
                {
                    "processed_summary_csv": processed_summary_csv,
                    "all_missing_summary_csv": all_missing_summary_csv,
                    "batch_rows": batch_rows,
                },
                code="summary_ready",
            )

        return OperationResult(
            False,
            "Batch processing failed to produce the expected summary files.",
            {
                "processed_summary_csv": None,
                "all_missing_summary_csv": all_missing_summary_csv,
                "batch_rows": [],
            },
            code="failed",
        )

    def find_latest_missing_summary_csv(self) -> Optional[str]:
        try:
            output_dir = self._results_folder_provider()
            if not output_dir or not self._filesystem.is_dir(output_dir):
                logger.warning("Results directory not valid: %s", output_dir)
                return None

            date_folders = sorted(
                [
                    item
                    for item in self._filesystem.listdir(output_dir)
                    if self._filesystem.is_dir(self._filesystem.join(output_dir, item))
                ],
                reverse=True,
            )
            if not date_folders:
                logger.warning("No date folders found in results directory: %s", output_dir)
                return None

            latest_date_dir = self._filesystem.join(output_dir, date_folders[0])
            potential_summary = self._filesystem.join(latest_date_dir, f"{ALL_MISSING_BASENAME}.csv")
            if self._filesystem.exists(potential_summary):
                return potential_summary

            logger.warning("%s.csv not found in %s", ALL_MISSING_BASENAME, latest_date_dir)
            return None
        except Exception:
            logger.error("Failed to resolve the latest missing-summary CSV.", exc_info=True)
            return None

    def load_batch_rows(self, processed_summary_csv: str) -> List[Tuple[str, str]]:
        rows: List[Tuple[str, str]] = []
        try:
            with open(processed_summary_csv, "r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                for row in reader:
                    rows.append((row.get(BATCH_SUMMARY_HEADERS[0], ""), row.get(BATCH_SUMMARY_HEADERS[2], "0")))
        except Exception:
            logger.error("Failed to load batch summary rows from %s", processed_summary_csv, exc_info=True)
        return rows
