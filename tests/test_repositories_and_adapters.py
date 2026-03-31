import json
from pathlib import Path

import pytest

from ModelFinderV2_6.adapters.filesystem_adapter import FileSystemAdapter
from ModelFinderV2_6.irregular_names_model import IrregularNamesModel
from ModelFinderV2_6.repositories.irregular_mapping_repository import IrregularMappingRepository
from ModelFinderV2_6.repositories.json_file_repository import JsonFileRepository
from ModelFinderV2_6.repositories.model_config_repository import ModelConfigRepository
from ModelFinderV2_6.repositories.search_cache_repository import SearchCacheRepository


pytestmark = pytest.mark.unit


def test_json_file_repository_round_trips_payload(tmp_path: Path) -> None:
    target_file = tmp_path / "data.json"
    repository = JsonFileRepository(str(target_file))

    repository.save({"foo": "bar"})

    assert repository.load(dict) == {"foo": "bar"}


def test_model_config_repository_targets_explicit_file(tmp_path: Path) -> None:
    config_path = tmp_path / "model_config.json"
    repository = ModelConfigRepository(config_path=str(config_path))

    repository.save({"model_node_types": [], "node_model_indices": {"default": [0]}, "model_extensions": []})

    payload = json.loads(config_path.read_text(encoding="utf-8"))
    assert payload["node_model_indices"]["default"] == [0]


def test_irregular_mapping_repository_persists_and_model_uses_repository(tmp_path: Path) -> None:
    mapping_path = tmp_path / "irregular_names_map.json"
    repository = IrregularMappingRepository(mappings_path=str(mapping_path))
    model = IrregularNamesModel(repository=repository)

    assert model.add_mapping("old-name", "new-name", "note")

    stored = json.loads(mapping_path.read_text(encoding="utf-8"))
    assert stored[0]["original_name"] == "old-name"
    assert model.get_corrected_name("old-name") == "new-name"


def test_search_cache_repository_round_trips_without_extra_fields(tmp_path: Path) -> None:
    results_root = tmp_path / "results"
    repository = SearchCacheRepository(results_folder_provider=lambda: str(results_root))
    cache_data = {
        "hf|demo|checkpointloadersimple": {
            "site": "hf",
            "url": "https://huggingface.co/foo/bar",
            "status": "已处理",
            "updated_at": 123.0,
        }
    }

    assert repository.save(cache_data)

    stored = json.loads((results_root / "search_cache.json").read_text(encoding="utf-8"))
    loaded = repository.load()
    assert "_saved_at" not in stored
    assert loaded == cache_data


def test_filesystem_adapter_exposes_common_path_helpers(tmp_path: Path) -> None:
    adapter = FileSystemAdapter()
    nested_dir = tmp_path / "foo" / "bar"
    adapter.makedirs(str(nested_dir), exist_ok=True)
    file_path = nested_dir / "demo.txt"
    file_path.write_text("x", encoding="utf-8")

    assert adapter.is_dir(str(nested_dir))
    assert adapter.exists(str(file_path))
    assert adapter.basename(str(file_path)) == "demo.txt"
