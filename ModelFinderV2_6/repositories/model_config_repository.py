import os
from typing import Optional

from ..adapters.filesystem_adapter import FileSystemAdapter
from .json_file_repository import JsonFileRepository


class ModelConfigRepository:
    CONFIG_FILENAME = "model_config.json"

    def __init__(
        self,
        config_path: Optional[str] = None,
        filesystem: Optional[FileSystemAdapter] = None,
    ):
        self._filesystem = filesystem or FileSystemAdapter()
        self.config_path = config_path or self._filesystem.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..",
            self.CONFIG_FILENAME,
        )
        self.config_path = self._filesystem.abspath(self.config_path)
        self._json_repository = JsonFileRepository(self.config_path, filesystem=self._filesystem)

    def load(self, default_factory):
        return self._json_repository.load(default_factory)

    def save(self, payload):
        self._json_repository.save(payload, indent=4, ensure_ascii=False)
