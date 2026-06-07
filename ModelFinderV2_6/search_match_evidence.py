import os
import re
from urllib.parse import unquote, urlparse

from .workflow_report_service import (
    COL_CONFIDENCE,
    COL_HIT_IDENTIFIER,
    COL_HIT_LINK,
    COL_HIT_SOURCE,
    COL_HIT_TITLE,
    COL_MATCH_REASON,
    COL_REMOTE_FILE,
    COL_SUSPICIOUS,
    COL_SUSPICIOUS_REASON,
)

PRECISION_TOKENS = ("fp32", "fp16", "bf16", "fp8", "int8", "int4", "nf4", "4bit", "8bit")
COMPONENT_HINTS = ("vae", "unet", "clip_vision", "clipvision", "clip", "text_encoder", "text-encoder", "lora", "controlnet")
NODE_TYPE_COMPONENT_HINTS = {
    "vae": "vae",
    "unet": "unet",
    "clipvision": "clip_vision",
    "clip_vision": "clip_vision",
    "clip": "clip",
    "textencoder": "clip",
    "text_encoder": "clip",
    "lora": "lora",
    "controlnet": "controlnet",
}

VERSION_PATTERN = re.compile(r"[a-z]*\d+(?:[._]\d+)+[a-z]*", re.IGNORECASE)
FILE_WITH_EXTENSION_PATTERN = re.compile(r"[\w.\-]+\.[a-z0-9]{2,16}", re.IGNORECASE)


def _safe_text(value) -> str:
    return (value or "").strip()


def _normalize_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", _safe_text(value).lower()).strip()


def _normalize_version_tokens(value: str):
    text = _safe_text(value).lower().replace("_", ".")
    return sorted({token.replace("_", ".") for token in VERSION_PATTERN.findall(text)})


def _extract_precision_tokens(value: str):
    text = _safe_text(value).lower()
    return sorted({token for token in PRECISION_TOKENS if token in text})


def _extract_extension(value: str) -> str:
    raw_value = _safe_text(value)
    parsed = urlparse(raw_value)
    if parsed.scheme and parsed.netloc:
        raw_value = unquote(os.path.basename(parsed.path or ""))
    extension = os.path.splitext(raw_value)[1].lower()
    return extension


def _extract_component_token(text: str, node_type: str = "") -> str:
    normalized_text = _normalize_text(text)
    normalized_node_type = _normalize_text(node_type)

    for token in COMPONENT_HINTS:
        normalized_token = token.replace("_", " ")
        if normalized_token in normalized_text:
            return token

    for hint, token in NODE_TYPE_COMPONENT_HINTS.items():
        if hint in normalized_node_type:
            return token

    return ""


def _extract_identifier_from_url(url: str) -> str:
    parsed = urlparse(_safe_text(url))
    host = (parsed.netloc or "").lower()
    path = unquote(parsed.path or "").strip("/")
    if not path:
        return ""

    path_parts = [part for part in path.split("/") if part]
    if "huggingface.co" in host and len(path_parts) >= 2:
        repo_path = "/".join(path_parts[:2])
        file_name = next((part for part in reversed(path_parts) if "." in part), "")
        return f"{repo_path} :: {file_name}" if file_name else repo_path

    if "liblib.art" in host:
        return path

    file_match = FILE_WITH_EXTENSION_PATTERN.search(path)
    if file_match:
        return file_match.group(0)
    return path


def _extract_remote_filename(url: str) -> str:
    parsed = urlparse(_safe_text(url))
    if not parsed.scheme or not parsed.netloc:
        return ""

    basename = unquote(os.path.basename(parsed.path or ""))
    extension = os.path.splitext(basename)[1].lower()
    if not re.fullmatch(r"\.[a-z0-9]{2,16}", extension):
        return ""
    return basename


def _is_hf_like_url(url: str) -> bool:
    parsed = urlparse(_safe_text(url))
    host = (parsed.netloc or "").lower()
    return "huggingface.co" in host or "hf-mirror.com" in host


def _extract_file_hints(text: str):
    lowered = _safe_text(text).lower()
    return sorted({match.group(0).lower() for match in FILE_WITH_EXTENSION_PATTERN.finditer(lowered)})


def _has_strong_name_match(normalized_name: str, original_name: str, evidence_text: str) -> bool:
    normalized_stem = _normalize_text(os.path.splitext(normalized_name)[0])
    original_stem = _normalize_text(os.path.splitext(original_name)[0])
    evidence_normalized = _normalize_text(evidence_text)

    for stem in (normalized_stem, original_stem):
        if stem and stem in evidence_normalized:
            return True

    distinctive_tokens = [token for token in normalized_stem.split() if len(token) >= 3]
    if not distinctive_tokens:
        distinctive_tokens = [token for token in original_stem.split() if len(token) >= 3]
    if not distinctive_tokens:
        return False

    matched = [token for token in distinctive_tokens if token in evidence_normalized]
    return len(matched) >= min(2, len(distinctive_tokens))


def build_match_evidence(
    *,
    original_name: str,
    normalized_name: str,
    search_term: str,
    node_type: str,
    result_site: str,
    hit_title: str,
    hit_link: str,
    found_url: str,
) -> dict:
    original_name = _safe_text(original_name)
    normalized_name = _safe_text(normalized_name)
    search_term = _safe_text(search_term)
    hit_title = _safe_text(hit_title)
    hit_link = _safe_text(hit_link)
    found_url = _safe_text(found_url)
    result_site = _safe_text(result_site)

    source_label = {
        "hf": "HuggingFace",
        "liblib": "LibLib",
    }.get(result_site.lower(), result_site)

    match_target_url = found_url if _is_hf_like_url(found_url) else hit_link if _is_hf_like_url(hit_link) else ""
    identifier = _extract_identifier_from_url(match_target_url or found_url or hit_link)
    remote_filename = _extract_remote_filename(match_target_url or found_url or hit_link)
    evidence_text = " ".join(part for part in (hit_title, hit_link, found_url, identifier) if part)

    if not match_target_url:
        return {
            COL_HIT_SOURCE: source_label,
            COL_HIT_TITLE: hit_title,
            COL_HIT_LINK: hit_link or found_url,
            COL_REMOTE_FILE: remote_filename,
            COL_HIT_IDENTIFIER: identifier,
            COL_MATCH_REASON: "非HuggingFace下载源，仅记录命中，不参与自动匹配判断" if (hit_link or found_url) else "",
            COL_CONFIDENCE: "",
            COL_SUSPICIOUS: "",
            COL_SUSPICIOUS_REASON: "",
        }

    input_versions = sorted(
        set(_normalize_version_tokens(original_name) + _normalize_version_tokens(normalized_name) + _normalize_version_tokens(search_term))
    )
    hit_versions = _normalize_version_tokens(evidence_text)
    input_precisions = sorted(
        set(_extract_precision_tokens(original_name) + _extract_precision_tokens(normalized_name) + _extract_precision_tokens(search_term))
    )
    hit_precisions = _extract_precision_tokens(evidence_text)

    input_extension = _extract_extension(original_name) or _extract_extension(normalized_name)
    hit_extension = ""
    hit_file_hints = _extract_file_hints(evidence_text)
    if hit_file_hints:
        hit_extension = _extract_extension(hit_file_hints[0])
    if not hit_extension:
        hit_extension = _extract_extension(hit_link) or _extract_extension(found_url)

    input_component = _extract_component_token(" ".join((original_name, normalized_name, search_term)), node_type)
    hit_component = _extract_component_token(evidence_text)

    positive_reasons = []
    suspicious_reasons = []
    confidence = 0.0

    if match_target_url:
        confidence += 0.20
    else:
        suspicious_reasons.append("未找到可验证的命中链接")

    strong_name_match = _has_strong_name_match(normalized_name, original_name, evidence_text)
    if strong_name_match:
        positive_reasons.append("标题或链接中包含强名称证据")
        confidence += 0.35
    elif match_target_url:
        suspicious_reasons.append("仅模糊匹配，未发现强名称证据")

    if input_extension and hit_extension:
        if input_extension == hit_extension:
            positive_reasons.append(f"文件扩展名一致({input_extension})")
            confidence += 0.10
        else:
            suspicious_reasons.append(f"文件扩展名不一致({input_extension} vs {hit_extension})")

    if input_versions and hit_versions:
        if set(input_versions) & set(hit_versions):
            positive_reasons.append(f"版本号一致({', '.join(sorted(set(input_versions) & set(hit_versions)))})")
            confidence += 0.10
        else:
            suspicious_reasons.append(f"版本号不一致({', '.join(input_versions)} vs {', '.join(hit_versions)})")
    elif match_target_url:
        positive_reasons.append("未检测到可比较的版本号")
        confidence += 0.05

    if input_precisions and hit_precisions:
        if set(input_precisions) & set(hit_precisions):
            positive_reasons.append(f"精度/量化标识一致({', '.join(sorted(set(input_precisions) & set(hit_precisions)))})")
            confidence += 0.10
        else:
            suspicious_reasons.append(f"精度/量化标识不一致({', '.join(input_precisions)} vs {', '.join(hit_precisions)})")
    elif match_target_url:
        confidence += 0.05

    if input_component and hit_component:
        if input_component == hit_component:
            positive_reasons.append(f"组件类型一致({input_component})")
            confidence += 0.10
        else:
            suspicious_reasons.append(f"组件类型可疑({input_component} vs {hit_component})")
    elif match_target_url:
        confidence += 0.05

    confidence -= 0.20 * len(suspicious_reasons)
    confidence = max(0.0, min(confidence, 0.99))

    if not positive_reasons and not suspicious_reasons:
        positive_reasons.append("保留基础搜索命中信息，待人工复核")

    match_reason_parts = []
    if positive_reasons:
        match_reason_parts.append("正向证据: " + "；".join(positive_reasons))
    if suspicious_reasons:
        match_reason_parts.append("可疑点: " + "；".join(suspicious_reasons))

    return {
        COL_HIT_SOURCE: source_label,
        COL_HIT_TITLE: hit_title,
        COL_HIT_LINK: hit_link or found_url,
        COL_REMOTE_FILE: remote_filename,
        COL_HIT_IDENTIFIER: identifier,
        COL_MATCH_REASON: " | ".join(match_reason_parts),
        COL_CONFIDENCE: f"{confidence:.2f}",
        COL_SUSPICIOUS: "是" if suspicious_reasons else "否",
        COL_SUSPICIOUS_REASON: "；".join(suspicious_reasons),
    }
