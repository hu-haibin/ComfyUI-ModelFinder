import os
from typing import Callable, Dict, Iterable, Optional

from .operation_result import OperationResult


class ComfyUIRuntimeModelCatalogService:
    SUPPORTED_MODEL_EXTENSIONS = {
        ".ckpt",
        ".pt",
        ".pt2",
        ".bin",
        ".pth",
        ".safetensors",
        ".pkl",
        ".sft",
    }

    CATEGORY_DIRECTORIES = {
        "checkpoints": ("checkpoints",),
        "loras": ("loras",),
        "vae": ("vae", "vae_approx"),
        "controlnet": ("controlnet", "t2i_adapter"),
        "diffusion_models": ("unet", "diffusion_models"),
        "text_encoders": ("text_encoders", "clip"),
    }

    def __init__(
        self,
        *,
        comfyui_path_provider: Optional[Callable[[], str]] = None,
        walker: Callable[[str], Iterable] = os.walk,
    ):
        self._comfyui_path_provider = comfyui_path_provider
        self._walker = walker

    def get_core_model_catalog(self, comfyui_path: Optional[str] = None) -> OperationResult:
        resolved_path = os.path.abspath((comfyui_path or self._read_path_from_provider()).strip())
        if not resolved_path:
            return OperationResult(False, "请先配置 ComfyUI 路径。", code="comfyui_path_missing")

        models_dir = os.path.join(resolved_path, "models")
        if not os.path.isdir(models_dir):
            return OperationResult(False, f"未找到 ComfyUI models 目录: {models_dir}", code="models_dir_missing")

        catalog: Dict[str, list[str]] = {}
        normalized_lookup: Dict[str, set[str]] = {}
        for category, subdirs in self.CATEGORY_DIRECTORIES.items():
            entries = set()
            for subdir in subdirs:
                directory = os.path.join(models_dir, subdir)
                entries.update(self._scan_model_directory(directory))
            ordered_entries = sorted(entries)
            catalog[category] = ordered_entries
            normalized_lookup[category] = {self.normalize_entry_name(item) for item in ordered_entries}

        summary = {category: len(entries) for category, entries in catalog.items()}
        summary["total"] = sum(summary.values())
        return OperationResult(
            True,
            "ComfyUI 运行时模型目录已加载。",
            {
                "comfyui_path": resolved_path,
                "models_dir": models_dir,
                "catalog": catalog,
                "normalized_lookup": normalized_lookup,
                "summary": summary,
            },
            code="runtime_model_catalog_loaded",
        )

    @classmethod
    def normalize_entry_name(cls, value: str) -> str:
        normalized = os.path.normpath((value or "").strip().replace("/", os.sep).replace("\\", os.sep))
        return normalized.lower()

    def _scan_model_directory(self, directory: str) -> set[str]:
        if not os.path.isdir(directory):
            return set()

        discovered = set()
        for root, dirnames, filenames in self._walker(directory):
            dirnames[:] = [name for name in dirnames if name != ".git"]
            for filename in filenames:
                extension = os.path.splitext(filename)[1].lower()
                if extension not in self.SUPPORTED_MODEL_EXTENSIONS:
                    continue
                full_path = os.path.join(root, filename)
                relative_path = os.path.relpath(full_path, directory)
                discovered.add(relative_path)
        return discovered

    def _read_path_from_provider(self) -> str:
        if self._comfyui_path_provider is None:
            return ""

        try:
            return (self._comfyui_path_provider() or "").strip()
        except Exception:
            return ""
