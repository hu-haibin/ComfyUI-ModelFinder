import json
import os
from typing import Iterable

from .operation_result import OperationResult


class WorkflowMissingNodeService:
    def collect_workflow_files(self, paths: Iterable[str]) -> OperationResult:
        collected = []
        seen = set()

        for raw_path in paths or []:
            path = os.path.abspath((raw_path or "").strip())
            if not path or path in seen or not os.path.exists(path):
                continue

            if os.path.isdir(path):
                for root, _, files in os.walk(path):
                    for name in files:
                        if not name.lower().endswith(".json"):
                            continue
                        file_path = os.path.join(root, name)
                        normalized = os.path.abspath(file_path)
                        if normalized not in seen:
                            collected.append(normalized)
                            seen.add(normalized)
            elif path.lower().endswith(".json"):
                collected.append(path)
                seen.add(path)

        collected.sort()
        if not collected:
            return OperationResult(False, "未找到可分析的工作流 JSON 文件。", code="workflow_files_missing")

        return OperationResult(
            True,
            "Workflow files collected.",
            {"workflow_files": collected, "count": len(collected)},
            code="workflow_files_collected",
        )

    def extract_node_types(self, workflow_json) -> OperationResult:
        node_types = set()
        self._collect_node_types(workflow_json, node_types)
        return OperationResult(
            True,
            "Workflow node types extracted.",
            {"node_types": sorted(node_types), "count": len(node_types)},
            code="workflow_node_types_extracted",
        )

    def extract_node_descriptors(self, workflow_json) -> OperationResult:
        descriptors = {}
        self._collect_node_descriptors(workflow_json, descriptors)
        descriptor_list = sorted(descriptors.values(), key=lambda item: (item["type"], item.get("cnr_id") or "", item.get("aux_id") or ""))
        return OperationResult(
            True,
            "Workflow node descriptors extracted.",
            {"nodes": descriptor_list, "count": len(descriptor_list)},
            code="workflow_node_descriptors_extracted",
        )

    def analyze_missing_node_types(self, workflow_files, registered_node_types) -> OperationResult:
        registered = set(registered_node_types or [])
        all_node_types = set()
        per_file = {}
        all_node_descriptors = {}
        missing_descriptors = {}

        for workflow_file in workflow_files or []:
            try:
                with open(workflow_file, "r", encoding="utf-8-sig") as handle:
                    workflow_json = json.load(handle)
            except Exception as exc:
                return OperationResult(
                    False,
                    f"读取工作流失败: {workflow_file} ({exc})",
                    code="workflow_read_failed",
                )

            extracted = self.extract_node_types(workflow_json)
            descriptor_result = self.extract_node_descriptors(workflow_json)
            node_types = extracted.data["node_types"]
            per_file[workflow_file] = node_types
            all_node_types.update(node_types)
            for descriptor in descriptor_result.data["nodes"]:
                descriptor_key = self._descriptor_key(descriptor)
                all_node_descriptors[descriptor_key] = descriptor
                if descriptor["type"] not in registered:
                    missing_descriptors[descriptor_key] = descriptor

        missing_node_types = sorted(all_node_types - registered)
        return OperationResult(
            True,
            "Workflow analysis completed.",
            {
                "workflow_files": list(workflow_files or []),
                "node_types_by_file": per_file,
                "all_node_types": sorted(all_node_types),
                "missing_node_types": missing_node_types,
                "all_node_descriptors": sorted(all_node_descriptors.values(), key=lambda item: (item["type"], item.get("cnr_id") or "", item.get("aux_id") or "")),
                "missing_nodes": sorted(missing_descriptors.values(), key=lambda item: (item["type"], item.get("cnr_id") or "", item.get("aux_id") or "")),
                "total_workflows": len(list(workflow_files or [])),
                "total_node_types": len(all_node_types),
                "missing_count": len(missing_node_types),
            },
            code="workflow_missing_nodes_analyzed",
        )

    @staticmethod
    def _descriptor_key(descriptor) -> str:
        return "|".join(
            [
                descriptor.get("type", "").strip(),
                descriptor.get("cnr_id", "").strip(),
                descriptor.get("aux_id", "").strip(),
            ]
        )

    def _collect_node_descriptors(self, value, descriptors: dict) -> None:
        if isinstance(value, list):
            for item in value:
                self._collect_node_descriptors(item, descriptors)
            return

        if not isinstance(value, dict):
            return

        self._maybe_add_prompt_node_descriptor(value, descriptors)

        if "nodes" in value and isinstance(value["nodes"], list):
            for node in value["nodes"]:
                if isinstance(node, dict):
                    self._maybe_add_canvas_node_descriptor(node, descriptors)
                self._collect_node_descriptors(node, descriptors)

        if "prompt" in value and isinstance(value["prompt"], dict):
            for node in value["prompt"].values():
                self._collect_node_descriptors(node, descriptors)

        for child in value.values():
            if isinstance(child, (dict, list)):
                self._collect_node_descriptors(child, descriptors)

    def _maybe_add_prompt_node_descriptor(self, value: dict, descriptors: dict) -> None:
        class_type = value.get("class_type")
        if not isinstance(class_type, str) or not class_type.strip():
            return

        properties = value.get("properties") if isinstance(value.get("properties"), dict) else {}
        descriptor = {
            "type": class_type.strip(),
            "cnr_id": self._normalize_optional_text(properties.get("cnr_id")),
            "aux_id": self._normalize_optional_text(properties.get("aux_id")),
        }
        descriptors[self._descriptor_key(descriptor)] = descriptor

    def _maybe_add_canvas_node_descriptor(self, node: dict, descriptors: dict) -> None:
        node_type = node.get("type")
        if not isinstance(node_type, str) or not node_type.strip():
            return

        properties = node.get("properties") if isinstance(node.get("properties"), dict) else {}
        descriptor = {
            "type": node_type.strip(),
            "cnr_id": self._normalize_optional_text(properties.get("cnr_id")),
            "aux_id": self._normalize_optional_text(properties.get("aux_id")),
        }
        descriptors[self._descriptor_key(descriptor)] = descriptor

    def _collect_node_types(self, value, node_types: set) -> None:
        if isinstance(value, list):
            for item in value:
                self._collect_node_types(item, node_types)
            return

        if not isinstance(value, dict):
            return

        class_type = value.get("class_type")
        if isinstance(class_type, str) and class_type.strip():
            node_types.add(class_type.strip())

        if "nodes" in value and isinstance(value["nodes"], list):
            for node in value["nodes"]:
                if isinstance(node, dict):
                    node_type = node.get("type")
                    if isinstance(node_type, str) and node_type.strip():
                        node_types.add(node_type.strip())
                self._collect_node_types(node, node_types)

        if "prompt" in value and isinstance(value["prompt"], dict):
            for node in value["prompt"].values():
                self._collect_node_types(node, node_types)

        for child in value.values():
            if isinstance(child, (dict, list)):
                self._collect_node_types(child, node_types)

    @staticmethod
    def _normalize_optional_text(value):
        if isinstance(value, str):
            normalized = value.strip()
            return normalized or ""
        return ""
