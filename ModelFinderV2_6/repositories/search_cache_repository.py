from typing import Callable, Optional

from ..adapters.filesystem_adapter import FileSystemAdapter
from ..file_manager import get_results_folder
from .json_file_repository import JsonFileRepository


class SearchCacheRepository:
    CACHE_FILENAME = "search_cache.json"

    def __init__(
        self,
        results_folder_provider: Callable[[], str] = get_results_folder,
        filesystem: Optional[FileSystemAdapter] = None,
        fallback_dir: Optional[str] = None,
    ):
        self._results_folder_provider = results_folder_provider
        self._filesystem = filesystem or FileSystemAdapter()
        self._fallback_dir = fallback_dir

    def get_cache_path(self) -> str:
        try:
            cache_root = self._results_folder_provider()
            self._filesystem.makedirs(cache_root, exist_ok=True)
            return self._filesystem.join(cache_root, self.CACHE_FILENAME)
        except Exception:
            fallback_dir = self._fallback_dir or self._filesystem.dirname(
                self._filesystem.dirname(self._filesystem.abspath(__file__))
            )
            self._filesystem.makedirs(fallback_dir, exist_ok=True)
            return self._filesystem.join(fallback_dir, self.CACHE_FILENAME)

    def load(self) -> dict:
        cache_path = self.get_cache_path()
        repository = JsonFileRepository(cache_path, filesystem=self._filesystem)
        try:
            data = repository.load(dict)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def save(self, cache_data: dict) -> bool:
        cache_path = self.get_cache_path()
        repository = JsonFileRepository(cache_path, filesystem=self._filesystem)
        try:
            payload = dict(cache_data or {})
            repository.save(payload, indent=2, ensure_ascii=False)
            return True
        except Exception:
            return False
