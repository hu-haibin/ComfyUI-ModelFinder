import json
import os
from typing import Dict, Iterable, List, Optional, Tuple

from .comfyui_runtime_model_catalog_service import ComfyUIRuntimeModelCatalogService
from .model_config_manager import ModelConfigManager
from .operation_result import OperationResult


class WorkflowModelAuditService:
    CORE_NODE_SPECS = {
        "CheckpointLoaderSimple": (("checkpoints", "checkpoint", 0, "ckpt_name"),),
        "CheckpointLoader": (("checkpoints", "checkpoint", 0, "ckpt_name"),),
        "unCLIPCheckpointLoader": (("checkpoints", "checkpoint", 0, "ckpt_name"),),
        "LoraLoader": (("loras", "lora", 0, "lora_name"),),
        "LoraLoaderModelOnly": (("loras", "lora", 0, "lora_name"),),
        "VAELoader": (("vae", "vae", 0, "vae_name"),),
        "ControlNetLoader": (("controlnet", "controlnet", 0, "control_net_name"),),
        "UNETLoader": (("diffusion_models", "unet", 0, "unet_name"),),
        "CLIPLoader": (("text_encoders", "text_encoder", 0, "clip_name"),),
        "DualCLIPLoader": (
            ("text_encoders", "text_encoder", 0, "clip_name1"),
            ("text_encoders", "text_encoder", 1, "clip_name2"),
        ),
        "TripleCLIPLoader": (
            ("text_encoders", "text_encoder", 0, "clip_name1"),
            ("text_encoders", "text_encoder", 1, "clip_name2"),
            ("text_encoders", "text_encoder", 2, "clip_name3"),
        ),
    }

    IGNORED_VALUES = {"default", "none", "empty", "auto", "off", "on"}

    def __init__(
        self,
        *,
        catalog_service: Optional[ComfyUIRuntimeModelCatalogService] = None,
        model_config_manager: Optional[ModelConfigManager] = None,
    ):
        self.catalog_service = catalog_service or ComfyUIRuntimeModelCatalogService()
        self.model_config_manager = model_config_manager or ModelConfigManager()

    def collect_workflow_files(self, paths: Iterable[str]) -> OperationResult:
        collected: List[str] = []
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
                        normalized = os.path.abspath(os.path.join(root, name))
                        if normalized not in seen:
                            seen.add(normalized)
                            collected.append(normalized)
            elif path.lower().endswith(".json"):
                seen.add(path)
                collected.append(path)

        collected.sort()
        if not collected:
            return OperationResult(False, "未找到可检测的工作流 JSON 文件。", code="workflow_files_missing")

        return OperationResult(
            True,
            "Workflow files collected.",
            {"workflow_files": collected, "count": len(collected)},
            code="workflow_files_collected",
        )

    def extract_runtime_model_references(self, workflow_json) -> OperationResult:
        if not isinstance(workflow_json, dict):
            return OperationResult(
                True,
                "Unsupported workflow format.",
                {"items": [], "unresolved_items": [], "workflow_supported": False},
                code="unsupported_workflow_format",
            )

        if isinstance(workflow_json.get("nodes"), list):
            return OperationResult(
                True,
                "Runtime model references extracted.",
                self._extract_from_canvas_workflow(workflow_json["nodes"]),
                code="workflow_model_references_extracted",
            )

        if isinstance(workflow_json.get("prompt"), dict):
            return OperationResult(
                True,
                "Runtime model references extracted.",
                self._extract_from_prompt_workflow(workflow_json["prompt"]),
                code="workflow_model_references_extracted",
            )

        return OperationResult(
            True,
            "Unsupported workflow format.",
            {"items": [], "unresolved_items": [], "workflow_supported": False},
            code="unsupported_workflow_format",
        )

    def audit_workflows(self, paths: Iterable[str]) -> OperationResult:
        collect_result = self.collect_workflow_files(paths)
        if not collect_result.success:
            return collect_result

        catalog_result = self.catalog_service.get_core_model_catalog()
        if not catalog_result.success:
            return catalog_result

        catalog_lookup = catalog_result.data["normalized_lookup"]
        aggregated: Dict[Tuple[str, str, str, str], dict] = {}
        unresolved_items = []
        workflow_count = 0

        for workflow_file in collect_result.data["workflow_files"]:
            try:
                with open(workflow_file, "r", encoding="utf-8-sig", errors="ignore") as handle:
                    workflow_json = json.load(handle)
            except Exception as exc:
                unresolved_items.append(
                    {
                        "workflow": workflow_file,
                        "status": "unsupported_workflow_format",
                        "reason": f"读取失败: {exc}",
                    }
                )
                continue

            workflow_count += 1
            extracted = self.extract_runtime_model_references(workflow_json)
            items = extracted.data["items"]
            if not extracted.data.get("workflow_supported", True):
                unresolved_items.append(
                    {
                        "workflow": workflow_file,
                        "status": "unsupported_workflow_format",
                        "reason": "暂不支持的工作流格式",
                    }
                )
                continue

            for item in items:
                normalized_value = self.catalog_service.normalize_entry_name(item["model_name"])
                if item["status"] != "needs_extension_runtime":
                    if normalized_value in catalog_lookup.get(item["model_type_key"], set()):
                        item["status"] = "resolved"
                    else:
                        item["status"] = "missing_core_model"

                key = (
                    item["model_name"],
                    item["model_type"],
                    item["source_node_type"],
                    item["status"],
                )
                entry = aggregated.setdefault(
                    key,
                    {
                        "model_name": item["model_name"],
                        "model_type": item["model_type"],
                        "source_node_type": item["source_node_type"],
                        "status": item["status"],
                        "workflow_count": 0,
                        "workflows": [],
                        "sample_workflow": os.path.basename(workflow_file),
                    },
                )
                if workflow_file not in entry["workflows"]:
                    entry["workflows"].append(workflow_file)
                    entry["workflow_count"] += 1

                if item["status"] != "resolved":
                    unresolved_items.append(
                        {
                            "workflow": workflow_file,
                            "model_name": item["model_name"],
                            "model_type": item["model_type"],
                            "source_node_type": item["source_node_type"],
                            "status": item["status"],
                        }
                    )

        items = sorted(
            aggregated.values(),
            key=lambda item: (
                item["status"],
                item["model_type"],
                item["model_name"].lower(),
                item["source_node_type"].lower(),
            ),
        )
        summary = {
            "workflow_count": workflow_count,
            "core_reference_count": sum(1 for item in items if item["status"] in {"resolved", "missing_core_model"}),
            "resolved_count": sum(1 for item in items if item["status"] == "resolved"),
            "missing_core_count": sum(1 for item in items if item["status"] == "missing_core_model"),
            "needs_extension_count": sum(1 for item in items if item["status"] == "needs_extension_runtime"),
            "unsupported_count": sum(1 for item in unresolved_items if item["status"] == "unsupported_workflow_format"),
        }

        return OperationResult(
            True,
            "Workflow model audit completed.",
            {
                "summary": summary,
                "items": items,
                "unresolved_items": unresolved_items,
                "workflow_count": workflow_count,
                "runtime_ready": True,
            },
            code="workflow_model_audit_completed",
        )

    def _extract_from_canvas_workflow(self, nodes: List[dict]) -> dict:
        items = []
        unresolved = []
        model_node_types = set(self.model_config_manager.get_model_node_types())
        node_model_indices = self.model_config_manager.get_node_model_indices()

        for node in nodes[:1000]:
            if not isinstance(node, dict):
                continue
            node_type = (node.get("type") or "").strip()
            widgets = node.get("widgets_values")
            if not node_type or not isinstance(widgets, list):
                continue

            if node_type in self.CORE_NODE_SPECS:
                for category, model_type, index, _ in self.CORE_NODE_SPECS[node_type]:
                    value = self._get_widget_value(widgets, index)
                    if value:
                        items.append(
                            self._create_item(
                                model_name=value,
                                model_type=model_type,
                                model_type_key=category,
                                source_node_type=node_type,
                                status="pending_core_check",
                            )
                        )
                continue

            if node_type in model_node_types or "Loader" in node_type:
                indices = node_model_indices.get(node_type, node_model_indices.get("default", [0]))
                for index in indices:
                    value = self._get_widget_value(widgets, index)
                    if value:
                        items.append(
                            self._create_item(
                                model_name=os.path.basename(value.replace("\\", "/")) if ("\\" in value or "/" in value) else value,
                                model_type="extension_resource",
                                model_type_key="extension_resource",
                                source_node_type=node_type,
                                status="needs_extension_runtime",
                            )
                        )
        return {"items": items, "unresolved_items": unresolved, "workflow_supported": True}

    def _extract_from_prompt_workflow(self, prompt: dict) -> dict:
        items = []
        for node in prompt.values():
            if not isinstance(node, dict):
                continue
            node_type = (node.get("class_type") or "").strip()
            inputs = node.get("inputs") if isinstance(node.get("inputs"), dict) else {}
            if node_type not in self.CORE_NODE_SPECS:
                continue

            for category, model_type, _, input_name in self.CORE_NODE_SPECS[node_type]:
                value = self._get_prompt_input_value(inputs, input_name)
                if value:
                    items.append(
                        self._create_item(
                            model_name=value,
                            model_type=model_type,
                            model_type_key=category,
                            source_node_type=node_type,
                            status="pending_core_check",
                        )
                    )
        return {"items": items, "unresolved_items": [], "workflow_supported": True}

    def _get_widget_value(self, widgets: list, index: int) -> Optional[str]:
        if index >= len(widgets) or not isinstance(widgets[index], str):
            return None
        value = widgets[index].strip()
        if not value or value.lower() in self.IGNORED_VALUES:
            return None
        return value

    def _get_prompt_input_value(self, inputs: dict, input_name: str) -> Optional[str]:
        value = inputs.get(input_name)
        if not isinstance(value, str):
            return None
        normalized = value.strip()
        if not normalized or normalized.lower() in self.IGNORED_VALUES:
            return None
        return normalized

    @staticmethod
    def _create_item(*, model_name: str, model_type: str, model_type_key: str, source_node_type: str, status: str) -> dict:
        return {
            "model_name": model_name,
            "model_type": model_type,
            "model_type_key": model_type_key,
            "source_node_type": source_node_type,
            "status": status,
        }
