import csv
import logging
import os
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Tuple

from .file_manager import get_results_folder


logger = logging.getLogger(__name__)


@dataclass
class AnalyzeWorkflowResult:
    status: str
    missing_count: int = 0
    csv_file: Optional[str] = None


@dataclass
class SearchLinksResult:
    status: str
    html_file: Optional[str] = None


@dataclass
class BatchProcessResult:
    status: str
    processed_summary_csv: Optional[str] = None
    all_missing_summary_csv: Optional[str] = None
    batch_rows: List[Tuple[str, str]] = field(default_factory=list)


class WorkflowProcessingService:
    def __init__(self, analysis_model, results_folder_provider: Callable[[], str] = get_results_folder):
        self.analysis_model = analysis_model
        self._results_folder_provider = results_folder_provider

    def analyze_workflow(self, workflow_file: str) -> AnalyzeWorkflowResult:
        missing_files = self.analysis_model.find_missing_models(workflow_file)
        if not missing_files:
            return AnalyzeWorkflowResult(status="no_missing")

        csv_file = self.analysis_model.create_csv_file(missing_files, os.path.basename(workflow_file))
        if not csv_file:
            return AnalyzeWorkflowResult(status="csv_failed", missing_count=len(missing_files))

        return AnalyzeWorkflowResult(
            status="csv_ready",
            missing_count=len(missing_files),
            csv_file=csv_file,
        )

    def search_links(self, csv_file: str, progress_callback=None) -> SearchLinksResult:
        search_result = self.analysis_model.search_model_links(csv_file, progress_callback=progress_callback)
        if isinstance(search_result, str) and os.path.exists(search_result):
            return SearchLinksResult(status="html_ready", html_file=search_result)
        if search_result is True:
            return SearchLinksResult(status="nothing_to_search")
        return SearchLinksResult(status="completed_without_html")

    def batch_process(self, directory: str, file_pattern: str, progress_callback=None) -> BatchProcessResult:
        processed_summary_csv = self.analysis_model.batch_process_workflows(
            directory,
            file_pattern,
            progress_callback=progress_callback,
        )
        all_missing_summary_csv = self.find_latest_missing_summary_csv()

        if processed_summary_csv is True:
            return BatchProcessResult(
                status="no_missing",
                all_missing_summary_csv=all_missing_summary_csv,
            )

        if isinstance(processed_summary_csv, str) and os.path.exists(processed_summary_csv):
            return BatchProcessResult(
                status="summary_ready",
                processed_summary_csv=processed_summary_csv,
                all_missing_summary_csv=all_missing_summary_csv,
                batch_rows=self.load_batch_rows(processed_summary_csv),
            )

        return BatchProcessResult(
            status="failed",
            all_missing_summary_csv=all_missing_summary_csv,
        )

    def find_latest_missing_summary_csv(self) -> Optional[str]:
        try:
            output_dir = self._results_folder_provider()
            if not output_dir or not os.path.isdir(output_dir):
                logger.warning(f"Results directory not valid: {output_dir}")
                return None

            date_folders = sorted(
                [d for d in os.listdir(output_dir) if os.path.isdir(os.path.join(output_dir, d))],
                reverse=True,
            )
            if not date_folders:
                logger.warning(f"No date folders found in results directory: {output_dir}")
                return None

            latest_date_dir = os.path.join(output_dir, date_folders[0])
            potential_summary = os.path.join(latest_date_dir, "汇总缺失文件.csv")
            if os.path.exists(potential_summary):
                return potential_summary

            logger.warning(f"汇总缺失文件.csv not found in {latest_date_dir}")
            return None
        except Exception:
            logger.error("查找汇总缺失文件时出错", exc_info=True)
            return None

    def load_batch_rows(self, processed_summary_csv: str) -> List[Tuple[str, str]]:
        rows: List[Tuple[str, str]] = []
        try:
            with open(processed_summary_csv, "r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                for row in reader:
                    rows.append((row.get("工作流文件", ""), row.get("缺失数量", "0")))
        except Exception:
            logger.error(f"读取批量结果CSV时出错: {processed_summary_csv}", exc_info=True)
        return rows
