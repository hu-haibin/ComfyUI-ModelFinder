import json
from pathlib import Path

import pytest

from ModelFinderV2_6.model_config_manager import ModelConfigManager


pytestmark = pytest.mark.unit


def _make_manager(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, config: dict) -> ModelConfigManager:
    config_path = tmp_path / "model_config.json"
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    monkeypatch.setattr(ModelConfigManager, "_get_config_path", lambda self: str(config_path))
    return ModelConfigManager()


def test_remove_node_model_index_removes_only_selected_index(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    manager = _make_manager(
        tmp_path,
        monkeypatch,
        {
            "model_node_types": ["Sampler"],
            "node_model_indices": {"default": [0], "Sampler": [0, 1, 2]},
            "model_extensions": [".safetensors"],
        },
    )

    assert manager.remove_node_model_index("Sampler", 1)
    assert manager.get_node_model_indices()["Sampler"] == [0, 2]


def test_remove_node_model_index_without_index_removes_mapping(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    manager = _make_manager(
        tmp_path,
        monkeypatch,
        {
            "model_node_types": ["Sampler"],
            "node_model_indices": {"default": [0], "Sampler": [3]},
            "model_extensions": [".safetensors"],
        },
    )

    assert manager.remove_node_model_index("Sampler")
    assert "Sampler" not in manager.get_node_model_indices()


def test_remove_last_default_node_model_index_is_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    manager = _make_manager(
        tmp_path,
        monkeypatch,
        {
            "model_node_types": [],
            "node_model_indices": {"default": [0]},
            "model_extensions": [".safetensors"],
        },
    )

    assert not manager.remove_node_model_index("default", 0)
    assert manager.get_node_model_indices()["default"] == [0]
