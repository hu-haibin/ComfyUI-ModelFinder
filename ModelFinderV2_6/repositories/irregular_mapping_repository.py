import os
from typing import Optional

from ..adapters.filesystem_adapter import FileSystemAdapter
from .json_file_repository import JsonFileRepository


class IrregularMappingRepository:
    MAPPINGS_FILENAME = "irregular_names_map.json"

    def __init__(
        self,
        mappings_path: Optional[str] = None,
        filesystem: Optional[FileSystemAdapter] = None,
    ):
        self._filesystem = filesystem or FileSystemAdapter()
        self.mappings_path = mappings_path or self._filesystem.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..",
            self.MAPPINGS_FILENAME,
        )
        self.mappings_path = self._filesystem.abspath(self.mappings_path)
        self._json_repository = JsonFileRepository(self.mappings_path, filesystem=self._filesystem)

    def load(self, default_factory):
        return self._json_repository.load(default_factory)

    def save(self, payload):
        self._json_repository.save(payload, indent=2, ensure_ascii=False)
