import logging
from typing import Any, Dict, List, Optional, Union

from .repositories.model_config_repository import ModelConfigRepository


logger = logging.getLogger(__name__)


class ModelConfigManager:
    CONFIG_FILENAME = "model_config.json"
    DEFAULT_CONFIG = {
        "model_node_types": [
            "CheckpointLoader",
            "VAELoader",
            "ModelLoader",
            "LoraLoader",
        ],
        "node_model_indices": {
            "default": [0],
        },
        "model_extensions": [
            ".safetensors",
            ".pth",
            ".ckpt",
            ".pt",
            ".bin",
        ],
    }

    def __init__(self, repository: Optional[ModelConfigRepository] = None):
        self.repository = repository or ModelConfigRepository()
        self._config = self._load_config()
        logger.info(
            "ModelConfigManager initialized with %s node types, %s node-index entries and %s extensions.",
            len(self.get_model_node_types()),
            len(self.get_node_model_indices()),
            len(self.get_model_extensions()),
        )

    def _load_config(self) -> Dict[str, Any]:
        try:
            config = self.repository.load(self._create_default_config)
            self._validate_config(config)
            return config
        except Exception:
            logger.error("Failed to load model config. Falling back to defaults.", exc_info=True)
            return self._create_default_config()

    def _save_config(self) -> bool:
        try:
            self.repository.save(self._config)
            return True
        except Exception:
            logger.error("Failed to save model config.", exc_info=True)
            return False

    def _validate_config(self, config: Dict[str, Any]) -> bool:
        required_keys = ["model_node_types", "node_model_indices", "model_extensions"]
        for key in required_keys:
            if key not in config:
                raise ValueError(f"Config is missing required key: {key}")

        if not isinstance(config["model_node_types"], list):
            raise TypeError("model_node_types must be a list")
        if not isinstance(config["node_model_indices"], dict):
            raise TypeError("node_model_indices must be a dict")
        if not isinstance(config["model_extensions"], list):
            raise TypeError("model_extensions must be a list")

        for node_type, indices in list(config["node_model_indices"].items()):
            if isinstance(indices, int):
                config["node_model_indices"][node_type] = [indices]
            elif not isinstance(indices, list) or not all(isinstance(index, int) for index in indices):
                raise TypeError(f"node_model_indices[{node_type!r}] must be a list of ints")

        return True

    def _create_default_config(self) -> Dict[str, Any]:
        default_config = {
            "model_node_types": list(self.DEFAULT_CONFIG["model_node_types"]),
            "node_model_indices": {
                key: list(value) for key, value in self.DEFAULT_CONFIG["node_model_indices"].items()
            },
            "model_extensions": list(self.DEFAULT_CONFIG["model_extensions"]),
        }
        try:
            self.repository.save(default_config)
        except Exception:
            logger.error("Failed to persist default model config.", exc_info=True)
        return default_config

    def get_model_node_types(self) -> List[str]:
        return list(self._config.get("model_node_types", []))

    def get_node_model_indices(self) -> Dict[str, List[int]]:
        indices = self._config.get("node_model_indices", {"default": [0]})
        return {key: list(value) for key, value in indices.items()}

    def get_model_extensions(self) -> List[str]:
        return list(self._config.get("model_extensions", []))

    def get_full_config(self) -> Dict[str, Any]:
        return {
            "model_node_types": self.get_model_node_types(),
            "node_model_indices": self.get_node_model_indices(),
            "model_extensions": self.get_model_extensions(),
        }

    def add_model_node_type(self, node_type: str) -> bool:
        normalized = (node_type or "").strip()
        if not normalized:
            return False
        if normalized in self._config["model_node_types"]:
            return False

        self._config["model_node_types"].append(normalized)
        return self._save_config()

    def add_node_model_index(self, node_type: str, indices: Union[List[int], int]) -> bool:
        normalized = (node_type or "").strip()
        if not normalized:
            return False

        if isinstance(indices, int):
            normalized_indices = [indices]
        elif isinstance(indices, (list, tuple)) and all(isinstance(index, int) for index in indices):
            normalized_indices = list(indices)
        else:
            return False

        existing = self._config["node_model_indices"].get(normalized)
        if existing == normalized_indices:
            return False

        self._config["node_model_indices"][normalized] = normalized_indices
        return self._save_config()

    def add_model_extension(self, extension: str) -> bool:
        normalized = (extension or "").strip()
        if not normalized:
            return False
        if not normalized.startswith("."):
            normalized = f".{normalized}"
        if normalized in self._config["model_extensions"]:
            return False

        self._config["model_extensions"].append(normalized)
        return self._save_config()

    def remove_model_node_type(self, node_type: str) -> bool:
        normalized = (node_type or "").strip()
        if not normalized or normalized not in self._config["model_node_types"]:
            return False

        self._config["model_node_types"].remove(normalized)
        return self._save_config()

    def remove_node_model_index(self, node_type: str, index: Union[int, None] = None) -> bool:
        normalized = (node_type or "").strip()
        if not normalized or normalized not in self._config["node_model_indices"]:
            return False

        if index is None:
            if normalized == "default":
                return False
            del self._config["node_model_indices"][normalized]
            return self._save_config()

        if not isinstance(index, int):
            return False

        current_indices = list(self._config["node_model_indices"][normalized])
        if index not in current_indices:
            return False
        if normalized == "default" and len(current_indices) == 1:
            return False

        current_indices.remove(index)
        if current_indices:
            self._config["node_model_indices"][normalized] = current_indices
        else:
            del self._config["node_model_indices"][normalized]
        return self._save_config()

    def remove_model_extension(self, extension: str) -> bool:
        normalized = (extension or "").strip()
        if not normalized:
            return False
        if not normalized.startswith("."):
            normalized = f".{normalized}"
        if normalized not in self._config["model_extensions"]:
            return False

        self._config["model_extensions"].remove(normalized)
        return self._save_config()

    def update_model_node_types(self, node_types: List[str]) -> bool:
        if not isinstance(node_types, list):
            return False
        self._config["model_node_types"] = [str(item).strip() for item in node_types if str(item).strip()]
        return self._save_config()

    def update_node_model_indices(self, indices_map: Dict[str, List[int]]) -> bool:
        if not isinstance(indices_map, dict):
            return False

        normalized_map: Dict[str, List[int]] = {}
        for node_type, indices in indices_map.items():
            if not isinstance(node_type, str) or not isinstance(indices, list):
                return False
            if not all(isinstance(index, int) for index in indices):
                return False
            normalized_map[node_type.strip()] = list(indices)

        if "default" not in normalized_map:
            normalized_map["default"] = list(self._config["node_model_indices"].get("default", [0]))

        self._config["node_model_indices"] = normalized_map
        return self._save_config()

    def update_model_extensions(self, extensions: List[str]) -> bool:
        if not isinstance(extensions, list):
            return False

        normalized_extensions = []
        for extension in extensions:
            normalized = str(extension).strip()
            if not normalized:
                continue
            if not normalized.startswith("."):
                normalized = f".{normalized}"
            normalized_extensions.append(normalized)

        self._config["model_extensions"] = normalized_extensions
        return self._save_config()

    def reset_to_default(self) -> bool:
        self._config = self._create_default_config()
        return True

    def reload_config(self) -> bool:
        try:
            self._config = self._load_config()
            return True
        except Exception:
            logger.error("Failed to reload model config.", exc_info=True)
            return False
