from typing import Callable, Optional

from .adapters.filesystem_adapter import FileSystemAdapter
from .file_manager import cleanup_old_results, get_results_folder
from .operation_result import OperationResult
from .utils import find_chrome_path


class ApplicationRuntimeService:
    def __init__(
        self,
        chrome_path_finder: Callable[[], str] = find_chrome_path,
        cleanup_old_results_func: Callable[..., int] = cleanup_old_results,
        results_folder_provider: Callable[[], str] = get_results_folder,
        filesystem: Optional[FileSystemAdapter] = None,
    ):
        self._chrome_path_finder = chrome_path_finder
        self._cleanup_old_results_func = cleanup_old_results_func
        self._results_folder_provider = results_folder_provider
        self._filesystem = filesystem or FileSystemAdapter()

    def resolve_chrome_path(self, configured_path: str) -> OperationResult:
        normalized = (configured_path or "").strip()
        if normalized:
            return OperationResult(
                True,
                "Using configured Chrome path.",
                {"chrome_path": normalized, "source": "configured"},
                code="chrome_path_configured",
            )

        detected = (self._chrome_path_finder() or "").strip()
        if detected:
            return OperationResult(
                True,
                "Detected Chrome path automatically.",
                {"chrome_path": detected, "source": "detected"},
                code="chrome_path_detected",
            )

        return OperationResult(
            False,
            "Chrome path is unavailable.",
            {"chrome_path": "", "source": "missing"},
            code="chrome_path_missing",
        )

    def cleanup_results(self, retention_days: int) -> OperationResult:
        deleted_count = self._cleanup_old_results_func(days_to_keep=retention_days)
        if deleted_count > 0:
            return OperationResult(
                True,
                f"Deleted {deleted_count} old result directories.",
                {"deleted_count": deleted_count, "retention_days": retention_days},
                code="cleanup_completed",
            )

        return OperationResult(
            True,
            "No old result directories needed cleanup.",
            {"deleted_count": 0, "retention_days": retention_days},
            code="cleanup_noop",
        )

    def resolve_results_folder(self) -> OperationResult:
        results_dir = self._results_folder_provider()
        if results_dir and self._filesystem.is_dir(results_dir):
            return OperationResult(
                True,
                "Results folder resolved.",
                {"results_dir": results_dir},
                code="results_folder_resolved",
            )

        return OperationResult(
            False,
            "Results folder path is invalid.",
            {"results_dir": results_dir},
            code="results_folder_invalid",
        )
