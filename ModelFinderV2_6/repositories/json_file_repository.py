import json
from typing import Any, Callable, Optional

from ..adapters.filesystem_adapter import FileSystemAdapter


class JsonFileRepository:
    def __init__(self, file_path: str, filesystem: Optional[FileSystemAdapter] = None):
        self.file_path = file_path
        self._filesystem = filesystem or FileSystemAdapter()

    def load(self, default_factory: Callable[[], Any]) -> Any:
        if not self._filesystem.exists(self.file_path):
            return default_factory()

        with open(self.file_path, "r", encoding="utf-8") as handle:
            return json.load(handle)

    def save(self, payload: Any, *, indent: int = 2, ensure_ascii: bool = False) -> None:
        parent_dir = self._filesystem.dirname(self.file_path)
        if parent_dir:
            self._filesystem.makedirs(parent_dir, exist_ok=True)

        temp_path = f"{self.file_path}.tmp"
        try:
            with open(temp_path, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=ensure_ascii, indent=indent)
            self._filesystem.replace(temp_path, self.file_path)
        except Exception:
            if self._filesystem.exists(temp_path):
                self._filesystem.remove(temp_path)
            raise
