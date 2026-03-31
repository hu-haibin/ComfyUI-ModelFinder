# irregular_names_model.py
import logging
import re
import uuid
from typing import Dict, List, Optional

from .repositories.irregular_mapping_repository import IrregularMappingRepository


logger = logging.getLogger(__name__)


class IrregularNamesModel:
    MAPPINGS_FILENAME = "irregular_names_map.json"

    def __init__(self, repository: Optional[IrregularMappingRepository] = None):
        self.repository = repository or IrregularMappingRepository()
        self.mappings = self._load_mappings()
        logger.info("Loaded %s irregular-name mappings.", len(self.mappings))

    def _load_mappings(self) -> List[Dict[str, str]]:
        try:
            loaded_data = self.repository.load(list)
            if not isinstance(loaded_data, list):
                return []
            return [item for item in loaded_data if isinstance(item, dict)]
        except Exception:
            logger.error("Failed to load irregular-name mappings.", exc_info=True)
            return []

    def _save_mappings(self) -> bool:
        try:
            self.repository.save(self.mappings)
            return True
        except Exception:
            logger.error("Failed to save irregular-name mappings.", exc_info=True)
            return False

    def get_all_mappings(self) -> List[Dict[str, str]]:
        return [dict(mapping) for mapping in self.mappings]

    def add_mapping(self, original_name, corrected_name, notes="") -> bool:
        normalized_original = (original_name or "").strip()
        normalized_corrected = (corrected_name or "").strip()
        if not normalized_original or not normalized_corrected:
            return False

        for mapping in self.mappings:
            if mapping.get("original_name") == normalized_original:
                return False

        self.mappings.append(
            {
                "id": str(uuid.uuid4()),
                "original_name": normalized_original,
                "corrected_name": normalized_corrected,
                "notes": notes or "",
            }
        )
        return self._save_mappings()

    def update_mapping(self, mapping_id, new_original_name, new_corrected_name, new_notes="") -> bool:
        normalized_original = (new_original_name or "").strip()
        normalized_corrected = (new_corrected_name or "").strip()
        if not mapping_id or not normalized_original or not normalized_corrected:
            return False

        for index, mapping in enumerate(self.mappings):
            if mapping.get("id") != mapping_id:
                continue

            for other_index, other_mapping in enumerate(self.mappings):
                if other_index != index and other_mapping.get("original_name") == normalized_original:
                    return False

            self.mappings[index] = {
                "id": mapping_id,
                "original_name": normalized_original,
                "corrected_name": normalized_corrected,
                "notes": new_notes or "",
            }
            return self._save_mappings()

        return False

    def delete_mapping(self, mapping_id) -> bool:
        original_length = len(self.mappings)
        self.mappings = [mapping for mapping in self.mappings if mapping.get("id") != mapping_id]
        if len(self.mappings) == original_length:
            return False
        return self._save_mappings()

    @staticmethod
    def _normalize_string(text) -> str:
        if not text or not isinstance(text, str):
            return ""
        normalized = text.strip()
        return re.sub(r"\s+", " ", normalized)

    def get_corrected_name(self, name_to_check):
        if not name_to_check:
            return name_to_check

        normalized_input = self._normalize_string(name_to_check)

        for mapping in self.mappings:
            if mapping.get("original_name", "") == name_to_check:
                return mapping.get("corrected_name")

        for mapping in self.mappings:
            original = mapping.get("original_name", "")
            if self._normalize_string(original) == normalized_input:
                return mapping.get("corrected_name")

        for mapping in self.mappings:
            original = mapping.get("original_name", "")
            if original.lower() == name_to_check.lower():
                return mapping.get("corrected_name")

        return name_to_check

    def find_mapping_by_id(self, mapping_id):
        for mapping in self.mappings:
            if mapping.get("id") == mapping_id:
                return dict(mapping)
        return None

    def dump_all_mappings_debug(self) -> int:
        logger.info("Current irregular-name mapping count: %s", len(self.mappings))
        for index, mapping in enumerate(self.mappings, start=1):
            logger.info(
                "Mapping #%s: id=%s original=%r corrected=%r",
                index,
                mapping.get("id", ""),
                mapping.get("original_name", ""),
                mapping.get("corrected_name", ""),
            )
        return len(self.mappings)
