import csv
import logging
import os
from typing import Callable, Iterable

from .file_manager import get_output_path
from .operation_result import OperationResult


logger = logging.getLogger(__name__)


MISSING_FILES_HEADERS = [
    "\u5e8f\u53f7",
    "\u8282\u70b9ID",
    "\u8282\u70b9\u7c7b\u578b",
    "\u6587\u4ef6\u540d",
    "\u72b6\u6001",
    "\u4e0b\u8f7d\u94fe\u63a5",
    "\u955c\u50cf\u94fe\u63a5",
    "\u641c\u7d22\u94fe\u63a5",
]

BATCH_SUMMARY_HEADERS = [
    "\u5de5\u4f5c\u6d41\u6587\u4ef6",
    "CSV\u6587\u4ef6",
    "\u7f3a\u5931\u6570\u91cf",
]

ALL_MISSING_BASENAME = "\u6c47\u603b\u7f3a\u5931\u6587\u4ef6"
BATCH_RESULTS_BASENAME = "\u6279\u91cf\u5904\u7406\u7ed3\u679c"


class WorkflowReportService:
    def __init__(self, output_path_provider: Callable[[str, str], str] = get_output_path):
        self._output_path_provider = output_path_provider

    def create_missing_files_report(
        self,
        missing_files: Iterable[dict],
        output_basename: str,
        process_name_for_search: Callable[[str], dict],
        search_url_builder: Callable[[str, str, str], tuple],
    ) -> OperationResult:
        missing_files = list(missing_files)
        if not missing_files:
            return OperationResult(False, "No missing files were provided.", code="missing_report_empty")

        csv_file_path = self._output_path_provider(output_basename, "csv")
        try:
            merged_files = {}
            for item_data in missing_files:
                original_file_path = item_data["file_path"]
                processed_names = process_name_for_search(original_file_path)

                if original_file_path not in merged_files:
                    merged_files[original_file_path] = {
                        "node_id": str(item_data["node_id"]),
                        "node_type": item_data["node_type"],
                        "original_file_path": original_file_path,
                        "name_for_decision": processed_names["mapped"],
                        "name_for_query_embedding": processed_names["final_search_term"],
                    }
                    continue

                existing = merged_files[original_file_path]
                existing["node_id"] = f"{existing['node_id']},{item_data['node_id']}"
                if item_data["node_type"] not in existing["node_type"].split(","):
                    existing["node_type"] = f"{existing['node_type']},{item_data['node_type']}"

            final_rows = sorted(merged_files.values(), key=lambda row: row["original_file_path"])
            with open(csv_file_path, "w", newline="", encoding="utf-8-sig") as handle:
                writer = csv.DictWriter(handle, fieldnames=MISSING_FILES_HEADERS)
                writer.writeheader()
                for index, row in enumerate(final_rows, 1):
                    _, site_query = search_url_builder(
                        row["name_for_decision"],
                        row["name_for_query_embedding"],
                        row["node_type"],
                    )
                    query_param = site_query.replace(" ", "+").replace('"', "%22")
                    search_link_url = f"https://www.bing.com/search?q={query_param}"
                    writer.writerow(
                        {
                            MISSING_FILES_HEADERS[0]: index,
                            MISSING_FILES_HEADERS[1]: row["node_id"],
                            MISSING_FILES_HEADERS[2]: row["node_type"],
                            MISSING_FILES_HEADERS[3]: row["original_file_path"],
                            MISSING_FILES_HEADERS[4]: "",
                            MISSING_FILES_HEADERS[5]: "",
                            MISSING_FILES_HEADERS[6]: "",
                            MISSING_FILES_HEADERS[7]: search_link_url,
                        }
                    )
        except Exception:
            logger.error("Failed to create missing-files CSV report.", exc_info=True)
            return OperationResult(False, "Failed to create missing-files CSV report.", code="missing_report_failed")

        return OperationResult(
            True,
            "Missing-files CSV report created.",
            {"csv_file": csv_file_path, "row_count": len(final_rows)},
            code="missing_report_created",
        )

    def create_batch_summary_report(self, results_summary: Iterable[dict]) -> OperationResult:
        rows = sorted(list(results_summary), key=lambda row: row["workflow"])
        if not rows:
            return OperationResult(False, "No batch summary rows were provided.", code="batch_summary_empty")

        batch_results_path = self._output_path_provider(BATCH_RESULTS_BASENAME, "csv")
        try:
            with open(batch_results_path, "w", newline="", encoding="utf-8-sig") as handle:
                writer = csv.DictWriter(handle, fieldnames=BATCH_SUMMARY_HEADERS)
                writer.writeheader()
                for row in rows:
                    writer.writerow(
                        {
                            BATCH_SUMMARY_HEADERS[0]: os.path.basename(row["workflow"]),
                            BATCH_SUMMARY_HEADERS[1]: os.path.basename(row["csv"]),
                            BATCH_SUMMARY_HEADERS[2]: row["missing_count"],
                        }
                    )
        except Exception:
            logger.error("Failed to create batch summary CSV report.", exc_info=True)
            return OperationResult(False, "Failed to create batch summary CSV report.", code="batch_summary_failed")

        return OperationResult(
            True,
            "Batch summary CSV report created.",
            {"csv_file": batch_results_path, "row_count": len(rows)},
            code="batch_summary_created",
        )
