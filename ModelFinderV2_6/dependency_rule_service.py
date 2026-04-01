import json
from pathlib import Path
from typing import Iterable, Optional

from .operation_result import OperationResult

try:
    from packaging.requirements import Requirement
except ImportError:  # pragma: no cover - fallback for limited environments
    from pip._vendor.packaging.requirements import Requirement


class DependencyRuleService:
    DEFAULT_RULE_ROOT_CANDIDATES = (
        r"E:\ComfyUI-aki-v2\launcher_dependency_system_src",
    )
    SPECIAL_ENV_PACKAGE_NAMES = {
        "XFORMERS_WINDOWS_PACKAGE": ("xformers",),
        "HANDREFINER_WHEEL": ("handrefinerportable", "handrefiner"),
        "INSIGHTFACE_WHEEL": ("insightface",),
        "DEPTH_ANYTHING_WHEEL": ("depth_anything", "depth-anything"),
    }
    MANAGED_PACKAGE_NAMES = {
        "torch",
        "torchvision",
        "torchaudio",
        "xformers",
        "onnxruntime",
        "onnxruntime-gpu",
        "insightface",
        "depth_anything",
        "depth-anything",
        "handrefinerportable",
        "handrefiner",
    }
    HIGH_RISK_BINARY_PACKAGES = {
        "bitsandbytes",
        "deepspeed",
        "flash-attn",
        "flash_attn",
        "mamba-ssm",
        "mamba_ssm",
        "onnxruntime-gpu",
        "pyav",
        "triton",
        "xformers",
    }

    def __init__(self, *, rule_root_candidates: Optional[Iterable[str]] = None):
        self._rule_root_candidates = tuple(rule_root_candidates or self.DEFAULT_RULE_ROOT_CANDIDATES)
        self._cached_rules = None

    def load_rules(self) -> OperationResult:
        if self._cached_rules is not None:
            return OperationResult(True, "Dependency rules loaded.", self._cached_rules, code="dependency_rules_loaded")

        root_path = self._discover_rule_root()
        if not root_path:
            return OperationResult(
                False,
                "未找到 aki 依赖策略目录。",
                {"candidates": list(self._rule_root_candidates)},
                code="dependency_rules_missing",
            )

        data_path = Path(root_path) / "data.json"
        try:
            data = self._load_json_with_fallback(data_path)
        except Exception as exc:
            return OperationResult(False, f"读取 aki 规则失败: {exc}", code="dependency_rules_read_failed")

        mirrors = data.get("mirrors") or {}
        additional_mirror_envs = self._normalize_additional_mirror_envs(mirrors.get("additional_mirror_envs") or [])
        extra_pip_index = list(mirrors.get("extra_pip_index") or [])
        pip_find_links = list(mirrors.get("pip_find_links") or [])
        torch_versions = list(data.get("torch_versions") or [])
        onnxruntime_releases = list(data.get("onnxruntime_releases") or [])

        rules = {
            "root_path": str(root_path),
            "data_path": str(data_path),
            "additional_mirror_envs": additional_mirror_envs,
            "extra_pip_index": extra_pip_index,
            "pip_find_links": pip_find_links,
            "torch_versions": torch_versions,
            "onnxruntime_releases": onnxruntime_releases,
            "special_package_rules": self._build_special_package_rules(additional_mirror_envs),
            "managed_package_names": set(self.MANAGED_PACKAGE_NAMES),
            "high_risk_binary_packages": set(self.HIGH_RISK_BINARY_PACKAGES),
        }
        self._cached_rules = rules
        return OperationResult(True, "Dependency rules loaded.", rules, code="dependency_rules_loaded")

    @staticmethod
    def _load_json_with_fallback(path: Path):
        raw_bytes = path.read_bytes()
        decoder = json.JSONDecoder()
        decode_errors = []

        for encoding in ("utf-8-sig", "utf-8"):
            try:
                return json.loads(raw_bytes.decode(encoding))
            except Exception as exc:
                decode_errors.append(f"{encoding}: {exc}")

        for encoding in ("utf-8-sig", "utf-8"):
            try:
                text = raw_bytes.decode(encoding, errors="replace")
                parsed, _ = decoder.raw_decode(text)
                return parsed
            except Exception as exc:
                decode_errors.append(f"{encoding} (replace): {exc}")

        raise ValueError("; ".join(decode_errors))

    def apply_requirement_rules(
        self,
        requirement_text: str,
        *,
        skip_packages=None,
        replace_packages=None,
        replace_packages_pre=None,
        remove_packages_extra=None,
    ) -> OperationResult:
        raw_text = (requirement_text or "").strip()
        if not raw_text or raw_text.startswith("#"):
            return OperationResult(True, "Empty requirement.", {"kind": "empty", "original": raw_text}, code="requirement_rule_applied")

        replace_packages_pre = dict(replace_packages_pre or {})
        replace_packages = {self._normalize_package_name(key): value for key, value in (replace_packages or {}).items()}
        remove_packages_extra = {self._normalize_package_name(item) for item in (remove_packages_extra or [])}
        skip_packages = {self._normalize_package_name(item) for item in (skip_packages or [])}

        rewritten = raw_text
        for source, target in replace_packages_pre.items():
            rewritten = rewritten.replace(source, target)

        lowered = rewritten.lower()
        if lowered.startswith(("--extra-index-url", "--find-links", "-f ", "--trusted-host")):
            return OperationResult(
                True,
                "Requirement directive preserved.",
                {"kind": "directive", "original": raw_text, "rewritten": rewritten, "name": ""},
                code="requirement_rule_applied",
            )

        if lowered.startswith(("git+", "http://", "https://")):
            return OperationResult(
                True,
                "Direct URL requirement preserved.",
                {"kind": "direct_url", "original": raw_text, "rewritten": rewritten, "name": ""},
                code="requirement_rule_applied",
            )

        try:
            requirement = Requirement(rewritten)
        except Exception as exc:
            return OperationResult(
                False,
                f"无法解析依赖声明: {raw_text} ({exc})",
                {"kind": "invalid", "original": raw_text, "rewritten": rewritten},
                code="requirement_rule_invalid",
            )

        normalized_name = self._normalize_package_name(requirement.name)
        if normalized_name in replace_packages:
            replacement = replace_packages[normalized_name]
            requirement = Requirement(rewritten.replace(requirement.name, replacement, 1))
            normalized_name = self._normalize_package_name(requirement.name)

        removed_extras = []
        if normalized_name in remove_packages_extra and requirement.extras:
            removed_extras = sorted(requirement.extras)
            requirement.extras.clear()

        if normalized_name in skip_packages:
            return OperationResult(
                True,
                "Requirement skipped by policy.",
                {
                    "kind": "requirement",
                    "original": raw_text,
                    "rewritten": str(requirement),
                    "name": normalized_name,
                    "specifier": str(requirement.specifier),
                    "skipped": True,
                    "removed_extras": removed_extras,
                },
                code="requirement_rule_applied",
            )

        return OperationResult(
            True,
            "Requirement normalized.",
            {
                "kind": "requirement",
                "original": raw_text,
                "rewritten": str(requirement),
                "name": normalized_name,
                "specifier": str(requirement.specifier),
                "skipped": False,
                "removed_extras": removed_extras,
            },
            code="requirement_rule_applied",
        )

    def _discover_rule_root(self) -> Optional[str]:
        for candidate in self._rule_root_candidates:
            path = Path(candidate)
            if path.is_dir() and (path / "data.json").exists():
                return str(path)
        return None

    @staticmethod
    def _normalize_additional_mirror_envs(items):
        result = {}
        for item in items or []:
            env_name = (item or {}).get("env")
            url = (item or {}).get("url")
            if env_name and url:
                result[str(env_name).strip()] = str(url).strip()
        return result

    def _build_special_package_rules(self, additional_mirror_envs):
        rules = {}
        for env_name, target in (additional_mirror_envs or {}).items():
            strategy = "install_with_wheel" if str(target).lower().endswith(".whl") else "install_with_mirror"
            for package_name in self.SPECIAL_ENV_PACKAGE_NAMES.get(env_name, ()):
                rules[self._normalize_package_name(package_name)] = {
                    "env": env_name,
                    "target": target,
                    "strategy": strategy,
                }

        for package_name in ("torch", "torchvision", "torchaudio"):
            rules.setdefault(
                package_name,
                {
                    "env": "TORCH_MATRIX",
                    "target": "torch_versions",
                    "strategy": "install_with_mirror",
                },
            )

        for package_name in ("onnxruntime", "onnxruntime-gpu"):
            rules.setdefault(
                package_name,
                {
                    "env": "ONNXRUNTIME_RELEASES",
                    "target": "onnxruntime_releases",
                    "strategy": "install_with_mirror",
                },
            )

        return rules

    @staticmethod
    def _normalize_package_name(value: str) -> str:
        return str(value or "").strip().lower().replace("_", "-")
