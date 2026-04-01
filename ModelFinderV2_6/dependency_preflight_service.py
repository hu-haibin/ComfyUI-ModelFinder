import os
import tomllib
from collections import defaultdict
from pathlib import Path

from .operation_result import OperationResult

try:
    from packaging.requirements import Requirement
    from packaging.version import InvalidVersion, Version
except ImportError:  # pragma: no cover - fallback for limited environments
    from pip._vendor.packaging.requirements import Requirement
    from pip._vendor.packaging.version import InvalidVersion, Version


class DependencyPreflightService:
    def __init__(self, *, environment_service, rule_service):
        self._environment_service = environment_service
        self._rule_service = rule_service

    def evaluate(self, packages) -> OperationResult:
        rule_result = self._rule_service.load_rules()
        if not rule_result.success:
            return rule_result

        environment_result = self._environment_service.collect_environment_snapshot()
        if not environment_result.success:
            return environment_result

        rules = rule_result.data
        environment = environment_result.data
        package_requirement_map = {}
        requirement_to_packages = defaultdict(set)
        exact_versions_by_requirement = defaultdict(set)
        unresolved_packages = []

        for package in packages or []:
            requirements = self._resolve_requirements_for_package(package, environment.get("comfyui_path", ""))
            package_requirement_map[package["id"]] = requirements
            if not requirements:
                unresolved_packages.append(package["id"])
                continue

            for item in requirements:
                if item.get("kind") != "requirement":
                    continue
                name = item.get("name")
                if not name:
                    continue
                requirement_to_packages[name].add(package["id"])
                specifier = item.get("specifier", "")
                exact_version = self._extract_exact_version(specifier)
                if exact_version:
                    exact_versions_by_requirement[name].add(exact_version)

        rows = []
        blocked_package_ids = set()
        summary = {"safe": 0, "safe_with_policy": 0, "warning": 0, "blocked": 0}

        for package in packages or []:
            requirements = package_requirement_map.get(package["id"], [])
            row = self._build_package_row(package, requirements, rules, environment, exact_versions_by_requirement)
            rows.append(row)
            summary[row["conclusion"]] += 1
            if row["conclusion"] == "blocked":
                blocked_package_ids.add(package["id"])

        rows.sort(key=lambda item: item["title"].lower())
        log_lines = [
            f"规则源: {rules['root_path']}",
            f"环境基线: Python {environment.get('python_version') or 'unknown'}，已安装 {len(environment.get('pip_packages') or {})} 个 pip 包。",
            (
                f"预检完成：{summary['safe']} 个安全，"
                f"{summary['safe_with_policy']} 个需策略安装，"
                f"{summary['warning']} 个警告，"
                f"{summary['blocked']} 个阻断。"
            ),
        ]
        if unresolved_packages:
            log_lines.append(f"有 {len(unresolved_packages)} 个插件未找到本地依赖清单，将保留 Manager 默认安装策略。")

        return OperationResult(
            True,
            "Dependency preflight completed.",
            {
                "rows": rows,
                "summary": summary,
                "blocked_package_ids": sorted(blocked_package_ids),
                "environment": environment,
                "rules": rules,
                "logs": log_lines,
            },
            code="dependency_preflight_completed",
        )

    def _build_package_row(self, package, requirements, rules, environment, exact_versions_by_requirement):
        package_id = package["id"]
        reasons = []
        strategies = []
        source_plugins = [package.get("title", package_id)]
        pip_packages = environment.get("pip_packages") or {}
        special_rules = rules.get("special_package_rules") or {}
        managed_package_names = rules.get("managed_package_names") or set()
        high_risk_binary_packages = rules.get("high_risk_binary_packages") or set()

        if not requirements:
            reasons.append("未找到可解析的 requirements/pyproject，保留 Manager 默认安装策略。")
            conclusion = "warning"
            strategy = "install"
            risk_level = "中"
            return self._build_row_payload(package, source_plugins, strategy, risk_level, conclusion, reasons, 0)

        for item in requirements:
            kind = item.get("kind")
            if kind == "directive":
                strategies.append("install_with_mirror")
                reasons.append(f"检测到 pip 指令: {item.get('rewritten') or item.get('original')}")
                continue
            if kind == "direct_url":
                strategies.append("install_with_wheel")
                reasons.append(f"检测到直链依赖: {item.get('rewritten') or item.get('original')}")
                continue
            if kind != "requirement":
                continue

            name = item.get("name", "")
            specifier = item.get("specifier", "")
            exact_versions = exact_versions_by_requirement.get(name, set())
            if len(exact_versions) > 1 and name not in managed_package_names:
                reasons.append(f"{name} 存在多个精确版本约束: {', '.join(sorted(exact_versions))}")

            special_rule = special_rules.get(name)
            if special_rule:
                strategies.append(special_rule["strategy"])
                reasons.append(f"{name} 将使用 aki 策略: {special_rule['env']}")
            elif name in {"torch", "torchvision", "torchaudio"}:
                strategies.append("install_with_mirror")
                reasons.append(f"{name} 将使用 aki 的 Torch 版本矩阵。")
            elif name in {"onnxruntime", "onnxruntime-gpu"}:
                strategies.append("install_with_mirror")
                reasons.append(f"{name} 将使用 aki 的 ONNX Runtime 预设。")
            elif name in high_risk_binary_packages:
                reasons.append(f"{name} 属于高风险二进制依赖，但未找到 aki 规则。")

            installed_version = pip_packages.get(name)
            exact_version = self._extract_exact_version(specifier)
            if exact_version and installed_version and installed_version != exact_version and name not in managed_package_names:
                reasons.append(f"当前环境已安装 {name}=={installed_version}，与插件要求 {exact_version} 不一致。")

        blocked = any("多个精确版本约束" in reason or "高风险二进制依赖" in reason for reason in reasons)
        if blocked:
            conclusion = "blocked"
            strategy = "defer_manual"
            risk_level = "高"
        elif any(strategy in {"install_with_wheel", "install_with_mirror", "replace_then_install"} for strategy in strategies):
            conclusion = "safe_with_policy"
            strategy = self._pick_strategy(strategies)
            risk_level = "中"
        elif any("不一致" in reason for reason in reasons):
            conclusion = "warning"
            strategy = "install"
            risk_level = "中"
        else:
            conclusion = "safe"
            strategy = "install"
            risk_level = "低"

        return self._build_row_payload(
            package,
            source_plugins,
            strategy,
            risk_level,
            conclusion,
            reasons,
            sum(1 for item in requirements if item.get("kind") == "requirement"),
        )

    @staticmethod
    def _pick_strategy(strategies):
        priority = ["install_with_wheel", "replace_then_install", "install_with_mirror", "install"]
        for strategy in priority:
            if strategy in strategies:
                return strategy
        return "install"

    @staticmethod
    def _build_row_payload(package, source_plugins, strategy, risk_level, conclusion, reasons, dependency_count):
        conclusion_labels = {
            "safe": "可直接安装",
            "safe_with_policy": "需策略安装",
            "warning": "高风险，需人工确认",
            "blocked": "阻断安装",
        }
        return {
            "id": package["id"],
            "title": package.get("title", package["id"]),
            "source_plugins": source_plugins,
            "strategy": strategy,
            "risk_level": risk_level,
            "conclusion": conclusion,
            "conclusion_label": conclusion_labels[conclusion],
            "dependency_count": dependency_count,
            "reasons": reasons,
            "can_install": conclusion in {"safe", "safe_with_policy", "warning"},
        }

    def _resolve_requirements_for_package(self, package, comfyui_path):
        requirement_items = []
        metadata = package.get("metadata") or {}

        for field_name in ("pip", "dependencies", "requirements"):
            value = metadata.get(field_name)
            if isinstance(value, str):
                requirement_items.extend(self._normalize_requirement_lines([value]))
            elif isinstance(value, list):
                requirement_items.extend(self._normalize_requirement_lines(value))

        package_dir = self._find_local_package_dir(package, comfyui_path)
        if package_dir:
            requirement_items.extend(self._read_requirement_files(package_dir))
            requirement_items.extend(self._read_pyproject_dependencies(package_dir))

        normalized = []
        for item in requirement_items:
            result = self._rule_service.apply_requirement_rules(item)
            if result.success:
                normalized.append(result.data)

        deduplicated = {}
        for item in normalized:
            deduplicated[(item.get("kind"), item.get("rewritten"), item.get("name"))] = item
        return list(deduplicated.values())

    @staticmethod
    def _normalize_requirement_lines(lines):
        result = []
        for line in lines or []:
            if not isinstance(line, str):
                continue
            stripped = line.strip()
            if stripped:
                result.append(stripped)
        return result

    def _find_local_package_dir(self, package, comfyui_path):
        if not comfyui_path:
            return None
        custom_nodes_dir = Path(comfyui_path) / "custom_nodes"
        if not custom_nodes_dir.is_dir():
            return None

        candidates = {
            package.get("id", ""),
            package.get("title", ""),
        }
        metadata = package.get("metadata") or {}
        for value in metadata.get("files", []) or []:
            if isinstance(value, str):
                candidates.add(Path(value).stem)
                candidates.add(Path(value).name)

        normalized_candidates = {
            self._normalize_plugin_dir_name(value)
            for value in candidates
            if isinstance(value, str) and value.strip()
        }
        for child in custom_nodes_dir.iterdir():
            if not child.is_dir():
                continue
            if self._normalize_plugin_dir_name(child.name) in normalized_candidates:
                return child
        return None

    @staticmethod
    def _normalize_plugin_dir_name(value):
        return str(value or "").strip().lower().replace(" ", "").replace("_", "").replace("-", "")

    @staticmethod
    def _read_requirement_files(package_dir):
        result = []
        for requirement_path in sorted(package_dir.glob("requirements*.txt")):
            try:
                for line in requirement_path.read_text(encoding="utf-8-sig").splitlines():
                    stripped = line.strip()
                    if stripped and not stripped.startswith("#"):
                        result.append(stripped)
            except Exception:
                continue
        return result

    @staticmethod
    def _read_pyproject_dependencies(package_dir):
        pyproject_path = Path(package_dir) / "pyproject.toml"
        if not pyproject_path.exists():
            return []
        try:
            data = tomllib.loads(pyproject_path.read_text(encoding="utf-8-sig"))
        except Exception:
            return []

        project = data.get("project") or {}
        result = list(project.get("dependencies") or [])
        optional = project.get("optional-dependencies") or {}
        for values in optional.values():
            result.extend(values or [])
        return [item for item in result if isinstance(item, str) and item.strip()]

    @staticmethod
    def _extract_exact_version(specifier):
        if not specifier:
            return ""
        for chunk in str(specifier).split(","):
            piece = chunk.strip()
            if piece.startswith("==") and "*" not in piece:
                return piece[2:].strip()
            if piece.startswith("==="):
                return piece[3:].strip()
        return ""
