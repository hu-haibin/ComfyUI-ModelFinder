import os
from typing import Callable, Optional

from .adapters.filesystem_adapter import FileSystemAdapter
from .operation_result import OperationResult
from .utils import create_html_view


class ResultViewService:
    def __init__(
        self,
        html_view_builder: Callable[[str], str] = create_html_view,
        filesystem: Optional[FileSystemAdapter] = None,
    ):
        self._html_view_builder = html_view_builder
        self._filesystem = filesystem or FileSystemAdapter()

    def resolve_viewable_result(self, result_path: str) -> OperationResult:
        normalized = (result_path or "").strip()
        if not normalized:
            return OperationResult(False, "No result file is available to view.", code="missing_result_path")

        if not self._filesystem.exists(normalized):
            return OperationResult(
                False,
                "Result file does not exist.",
                {"source_path": normalized},
                code="missing_result_file",
            )

        extension = os.path.splitext(normalized)[1].lower()
        if extension == ".html":
            return OperationResult(
                True,
                "HTML result is ready.",
                {"open_path": normalized, "source_path": normalized, "generated_html": False},
                code="html_ready",
            )

        if extension == ".csv":
            html_path = self._html_view_builder(normalized)
            if html_path and self._filesystem.exists(html_path):
                return OperationResult(
                    True,
                    "HTML view generated from CSV.",
                    {"open_path": html_path, "source_path": normalized, "generated_html": True},
                    code="html_generated",
                )

            return OperationResult(
                False,
                "Failed to generate an HTML view from the CSV result.",
                {"source_path": normalized},
                code="html_generation_failed",
            )

        return OperationResult(
            False,
            "Unknown result file type.",
            {"source_path": normalized, "extension": extension},
            code="unsupported_result_type",
        )
