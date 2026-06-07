import pytest

from ModelFinderV2_6.search_match_evidence import build_match_evidence
from ModelFinderV2_6.workflow_report_service import (
    COL_CONFIDENCE,
    COL_MATCH_REASON,
    COL_REMOTE_FILE,
    COL_SUSPICIOUS,
    COL_SUSPICIOUS_REASON,
)


pytestmark = pytest.mark.unit


def test_build_match_evidence_flags_version_conflict_for_wan_models() -> None:
    evidence = build_match_evidence(
        original_name="wan2.1_t2v_14b_fp16.safetensors",
        normalized_name="wan2.1_t2v_14b_fp16.safetensors",
        search_term='site:huggingface.co "wan2.1_t2v_14b_fp16"',
        node_type="CheckpointLoaderSimple",
        result_site="hf",
        hit_title="Wan2.2 T2V 14B fp16",
        hit_link="https://huggingface.co/Wan-AI/Wan2.2-T2V-14B",
        found_url="https://huggingface.co/Wan-AI/Wan2.2-T2V-14B",
    )

    assert evidence[COL_SUSPICIOUS] == "是"
    assert "版本号不一致" in evidence[COL_SUSPICIOUS_REASON]
    assert "wan2.1" in evidence[COL_MATCH_REASON]
    assert evidence[COL_REMOTE_FILE] == ""
    assert float(evidence[COL_CONFIDENCE]) < 0.5


def test_build_match_evidence_marks_weak_hits_as_suspicious_when_no_strong_name_exists() -> None:
    evidence = build_match_evidence(
        original_name="demo-model.safetensors",
        normalized_name="demo-model.safetensors",
        search_term='site:huggingface.co "demo-model"',
        node_type="CheckpointLoaderSimple",
        result_site="hf",
        hit_title="Useful model collection",
        hit_link="https://huggingface.co/foo/bar",
        found_url="https://huggingface.co/foo/bar",
    )

    assert evidence[COL_SUSPICIOUS] == "是"
    assert "强名称证据" in evidence[COL_SUSPICIOUS_REASON]


def test_build_match_evidence_skips_matching_for_non_hf_sources() -> None:
    evidence = build_match_evidence(
        original_name="CPU",
        normalized_name="CPU",
        search_term='site:liblib.art "CPU"',
        node_type="Anything",
        result_site="liblib",
        hit_title="CPU 模型页",
        hit_link="https://www.liblib.art/modelinfo/cpu",
        found_url="https://www.liblib.art/modelinfo/cpu",
    )

    assert evidence[COL_SUSPICIOUS] == ""
    assert evidence[COL_SUSPICIOUS_REASON] == ""
    assert evidence[COL_REMOTE_FILE] == ""
    assert evidence[COL_MATCH_REASON] == "非HuggingFace下载源，仅记录命中，不参与自动匹配判断"


def test_build_match_evidence_extracts_remote_filename_from_hf_download_url() -> None:
    evidence = build_match_evidence(
        original_name="ema_vae_fp16.safetensors",
        normalized_name="ema_vae_fp16.safetensors",
        search_term='site:huggingface.co "ema_vae_fp16"',
        node_type="VAE",
        result_site="hf",
        hit_title="ema_vae_fp16",
        hit_link="https://huggingface.co/numz/SeedVR2_comfyUI/blob/main/ema_vae_fp16.safetensors",
        found_url="https://huggingface.co/numz/SeedVR2_comfyUI/resolve/main/ema_vae_fp16.safetensors",
    )

    assert evidence[COL_REMOTE_FILE] == "ema_vae_fp16.safetensors"
