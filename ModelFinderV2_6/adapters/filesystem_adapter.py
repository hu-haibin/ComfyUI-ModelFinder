import os
from typing import Iterable, List


class FileSystemAdapter:
    def exists(self, path: str) -> bool:
        return os.path.exists(path)

    def is_dir(self, path: str) -> bool:
        return os.path.isdir(path)

    def makedirs(self, path: str, exist_ok: bool = True) -> None:
        os.makedirs(path, exist_ok=exist_ok)

    def listdir(self, path: str) -> List[str]:
        return os.listdir(path)

    def join(self, *parts: Iterable[str]) -> str:
        return os.path.join(*parts)

    def dirname(self, path: str) -> str:
        return os.path.dirname(path)

    def abspath(self, path: str) -> str:
        return os.path.abspath(path)

    def basename(self, path: str) -> str:
        return os.path.basename(path)

    def replace(self, source: str, target: str) -> None:
        os.replace(source, target)

    def remove(self, path: str) -> None:
        os.remove(path)
