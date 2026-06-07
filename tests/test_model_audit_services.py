import json
from pathlib import Path

import pytest

from ModelFinderV2_6.comfyui_runtime_model_catalog_service import ComfyUIRuntimeModelCatalogService
from ModelFinderV2_6.workflow_model_audit_service import WorkflowModelAuditService


pytestmark = pytest.mark.unit


class _StubConfigManager:
    def __init__(self, *, node_types=None, node_indices=None):
        self._node_types = list(node_types or [])
        self._node_indices = dict(node_indices or {"default": [0]})

    def get_model_node_types(self):
        return list(self._node_types)

    def get_node_model_indices(self):
        return dict(self._node_indices)


def test_runtime_model_catalog_service_scans_core_model_directories(tmp_path: Path) -> None:
    comfyui_root = tmp_path / "ComfyUI"
    (comfyui_root / "models" / "checkpoints").mkdir(parents=True)
    (comfyui_root / "models" / "loras" / "nested").mkdir(parents=True)
    (comfyui_root / "models" / "vae_approx").mkdir(parents=True)
    (comfyui_root / "models" / "clip").mkdir(parents=True)
    (comfyui_root / "models" / "t2i_adapter").mkdir(parents=True)
    (comfyui_root / "models" / "unet").mkdir(parents=True)
    (comfyui_root / "models" / "checkpoints" / "base.safetensors").write_text("", encoding="utf-8")
    (comfyui_root / "models" / "loras" / "nested" / "style.safetensors").write_text("", encoding="utf-8")
    (comfyui_root / "models" / "vae_approx" / "vae.pt").write_text("", encoding="utf-8")
    (comfyui_root / "models" / "clip" / "clip_g.safetensors").write_text("", encoding="utf-8")
    (comfyui_root / "models" / "t2i_adapter" / "adapter.bin").write_text("", encoding="utf-8")
    (comfyui_root / "models" / "unet" / "flux1-dev.sft").write_text("", encoding="utf-8")

    service = ComfyUIRuntimeModelCatalogService(comfyui_path_provider=lambda: str(comfyui_root))

    result = service.get_core_model_catalog()

    assert result.success
    assert result.data["catalog"]["checkpoints"] == ["base.safetensors"]
    assert result.data["catalog"]["loras"] == [str(Path("nested") / "style.safetensors")]
    assert result.data["catalog"]["vae"] == ["vae.pt"]
    assert result.data["catalog"]["text_encoders"] == ["clip_g.safetensors"]
    assert result.data["catalog"]["controlnet"] == ["adapter.bin"]
    assert result.data["catalog"]["diffusion_models"] == ["flux1-dev.sft"]


def test_workflow_model_audit_service_marks_resolved_and_missing_core_models(tmp_path: Path) -> None:
    comfyui_root = tmp_path / "ComfyUI"
    checkpoints_dir = comfyui_root / "models" / "checkpoints"
    loras_dir = comfyui_root / "models" / "loras"
    checkpoints_dir.mkdir(parents=True)
    loras_dir.mkdir(parents=True)
    (checkpoints_dir / "present.safetensors").write_text("", encoding="utf-8")

    workflow_path = tmp_path / "workflow.json"
    workflow_path.write_text(
        json.dumps(
            {
                "nodes": [
                    {"type": "CheckpointLoaderSimple", "widgets_values": ["present.safetensors"]},
                    {"type": "LoraLoader", "widgets_values": ["missing-lora.safetensors"]},
                ]
            }
        ),
        encoding="utf-8",
    )

    catalog_service = ComfyUIRuntimeModelCatalogService(comfyui_path_provider=lambda: str(comfyui_root))
    service = WorkflowModelAuditService(
        catalog_service=catalog_service,
        model_config_manager=_StubConfigManager(),
    )

    result = service.audit_workflows([str(workflow_path)])

    assert result.success
    rows = {(item["model_name"], item["status"]) for item in result.data["items"]}
    assert ("present.safetensors", "resolved") in rows
    assert ("missing-lora.safetensors", "missing_core_model") in rows
    assert result.data["summary"]["resolved_count"] == 1
    assert result.data["summary"]["missing_core_count"] == 1


def test_workflow_model_audit_service_classifies_plugin_loader_as_extension_runtime(tmp_path: Path) -> None:
    comfyui_root = tmp_path / "ComfyUI"
    (comfyui_root / "models" / "checkpoints").mkdir(parents=True)

    workflow_path = tmp_path / "workflow.json"
    workflow_path.write_text(
        json.dumps(
            {
                "nodes": [
                    {"type": "FancyPrivateLoader", "widgets_values": ["plugin-model.bin"]},
                ]
            }
        ),
        encoding="utf-8",
    )

    catalog_service = ComfyUIRuntimeModelCatalogService(comfyui_path_provider=lambda: str(comfyui_root))
    service = WorkflowModelAuditService(
        catalog_service=catalog_service,
        model_config_manager=_StubConfigManager(
            node_types=["FancyPrivateLoader"],
            node_indices={"default": [0], "FancyPrivateLoader": [0]},
        ),
    )

    result = service.audit_workflows([str(workflow_path)])

    assert result.success
    assert result.data["items"][0]["status"] == "needs_extension_runtime"
    assert result.data["summary"]["needs_extension_count"] == 1


def test_workflow_model_audit_service_marks_unsupported_workflow_format(tmp_path: Path) -> None:
    comfyui_root = tmp_path / "ComfyUI"
    (comfyui_root / "models" / "checkpoints").mkdir(parents=True)
    workflow_path = tmp_path / "workflow.json"
    workflow_path.write_text(json.dumps({"foo": "bar"}), encoding="utf-8")

    catalog_service = ComfyUIRuntimeModelCatalogService(comfyui_path_provider=lambda: str(comfyui_root))
    service = WorkflowModelAuditService(
        catalog_service=catalog_service,
        model_config_manager=_StubConfigManager(),
    )

    result = service.audit_workflows([str(workflow_path)])

    assert result.success
    assert result.data["summary"]["unsupported_count"] == 1
    assert result.data["unresolved_items"][0]["status"] == "unsupported_workflow_format"
