import re
from collections import defaultdict

from .operation_result import OperationResult


class MissingNodeInstallOrchestrator:
    ACTIONABLE_STATES = {"not-installed", "unknown", "import-fail", "invalid-installation", "disabled", "enabled", "updatable"}

    def __init__(self, runtime_api_service, manager_api_service, workflow_missing_node_service):
        self._runtime_api_service = runtime_api_service
        self._manager_api_service = manager_api_service
        self._workflow_missing_node_service = workflow_missing_node_service

    def prepare_install_plan(self, workflow_paths) -> OperationResult:
        files_result = self._workflow_missing_node_service.collect_workflow_files(workflow_paths)
        if not files_result.success:
            return files_result

        runtime_result = self._runtime_api_service.get_registered_node_types()
        if not runtime_result.success:
            return OperationResult(False, "ComfyUI 未就绪，无法分析缺失节点。", code="runtime_unavailable")

        manager_result = self._manager_api_service.is_available()
        if not manager_result.success:
            return OperationResult(False, "ComfyUI-Manager 未就绪，无法生成安装计划。", code="manager_unavailable")

        db_mode_result = self._manager_api_service.get_db_mode()
        if not db_mode_result.success:
            return OperationResult(False, db_mode_result.message, code="manager_db_mode_unavailable")
        mode = db_mode_result.data["value"] or "default"

        analysis_result = self._workflow_missing_node_service.analyze_missing_node_types(
            files_result.data["workflow_files"],
            runtime_result.data["node_types"],
        )
        if not analysis_result.success:
            return analysis_result

        mappings_result = self._manager_api_service.get_node_mappings(mode)
        if not mappings_result.success:
            return mappings_result

        custom_nodes_result = self._manager_api_service.get_custom_node_list(mode)
        if not custom_nodes_result.success:
            return custom_nodes_result

        installed_result = self._manager_api_service.get_installed_nodes(mode)
        installed_nodes = installed_result.data if installed_result.success else {}

        node_packs = custom_nodes_result.data.get("node_packs", {})
        channel = custom_nodes_result.data.get("channel", "default")
        normalized_packs = self._normalize_node_packs(node_packs, installed_nodes, channel, mode)
        missing_match = self._collect_missing_match(
            analysis_result.data["missing_nodes"],
            normalized_packs,
            mappings_result.data,
        )
        candidate_rows, manual_items = self._build_candidate_rows(
            normalized_packs,
            missing_match,
        )

        return OperationResult(
            True,
            "Install plan prepared.",
            {
                "workflow_files": files_result.data["workflow_files"],
                "analysis": analysis_result.data,
                "mode": mode,
                "install_plan": candidate_rows,
                "manual_items": manual_items,
                "installed_nodes": installed_nodes,
                "outdated_comfyui": missing_match["outdated_comfyui"],
            },
            code="install_plan_prepared",
        )

    def execute_install_plan(self, selected_packages) -> OperationResult:
        queued_packages = []
        failed_packages = []

        for package in selected_packages or []:
            action = package.get("queue_action")
            metadata = dict(package.get("metadata") or {})

            if action == "fix":
                queue_result = self._manager_api_service.queue_fix(metadata)
            elif action == "install":
                queue_result = self._manager_api_service.queue_install(metadata)
            elif action == "enable":
                queue_result = self._manager_api_service.queue_install(metadata, skip_post_install=True)
            elif action == "reinstall":
                queue_result = self._manager_api_service.queue_reinstall(metadata)
            elif action == "update":
                queue_result = self._manager_api_service.queue_update(metadata)
            else:
                failed_packages.append(
                    {
                        "id": package.get("id", ""),
                        "title": package.get("title", ""),
                        "message": "当前插件项不支持批量操作。",
                    }
                )
                continue

            if queue_result.success:
                queued_packages.append(package["id"])
            else:
                failed_packages.append({"id": package["id"], "title": package["title"], "message": queue_result.message})

        if not queued_packages:
            return OperationResult(
                False,
                "没有可入队的插件包。",
                {"queued_package_ids": [], "failed_packages": failed_packages},
                code="install_queue_empty",
            )

        start_result = self._manager_api_service.start_queue()
        if not start_result.success:
            return OperationResult(
                False,
                start_result.message,
                {"queued_package_ids": queued_packages, "failed_packages": failed_packages},
                code="install_queue_start_failed",
            )

        return OperationResult(
            True,
            "批量安装任务已提交到 Manager 队列。",
            {
                "queued_package_ids": queued_packages,
                "failed_packages": failed_packages,
                "restart_required": True,
            },
            code="install_queue_started",
        )

    def recheck_after_restart(self, workflow_paths) -> OperationResult:
        result = self.prepare_install_plan(workflow_paths)
        if not result.success:
            return result

        return OperationResult(True, "重启后的复检已完成。", result.data, code="install_plan_rechecked")

    def _collect_missing_match(self, missing_nodes, normalized_packs, mappings):
        matched_hashes = set()
        matched_nodes_by_hash = defaultdict(set)
        unresolved_types = set()
        unresolved_aux_ids = defaultdict(set)
        unresolved_cnr_ids = set()
        outdated_comfyui = False

        pack_by_aux = self._build_aux_id_map(normalized_packs)

        for descriptor in missing_nodes or []:
            node_type = (descriptor.get("type") or "").strip()
            if not node_type:
                continue

            cnr_id = (descriptor.get("cnr_id") or "").strip()
            if cnr_id:
                if cnr_id == "comfy-core":
                    outdated_comfyui = True

                package = normalized_packs.get(cnr_id)
                if package:
                    self._mark_package_match(package, node_type, matched_hashes, matched_nodes_by_hash)
                else:
                    unresolved_aux_ids[cnr_id].add(node_type)
                    unresolved_cnr_ids.add(cnr_id)
                continue

            aux_id = (descriptor.get("aux_id") or "").strip().lower()
            if aux_id:
                unresolved_aux_ids[aux_id].add(node_type)
                continue

            unresolved_types.add(node_type)

        for aux_id, node_types in unresolved_aux_ids.items():
            package = pack_by_aux.get(aux_id)
            if package:
                for node_type in node_types:
                    self._mark_package_match(package, node_type, matched_hashes, matched_nodes_by_hash)
            else:
                unresolved_types.update(node_types)

        unresolved_types, legacy_match = self._resolve_legacy_missing_nodes(
            unresolved_types,
            normalized_packs,
            mappings,
        )
        matched_hashes.update(legacy_match["matched_hashes"])
        for pack_hash, node_types in legacy_match["matched_nodes_by_hash"].items():
            matched_nodes_by_hash[pack_hash].update(node_types)

        return {
            "matched_hashes": matched_hashes,
            "matched_nodes_by_hash": {key: sorted(value) for key, value in matched_nodes_by_hash.items()},
            "unresolved_types": sorted(unresolved_types),
            "unresolved_cnr_ids": sorted(unresolved_cnr_ids),
            "outdated_comfyui": outdated_comfyui,
        }

    def _resolve_legacy_missing_nodes(self, missing_node_types, normalized_packs, mappings):
        if not missing_node_types:
            return set(), {"matched_hashes": set(), "matched_nodes_by_hash": {}}

        regex_to_ref = []
        for package in normalized_packs.values():
            pattern = package.get("nodename_pattern")
            file_ref = self._get_primary_file(package)
            if not pattern or not file_ref:
                continue
            try:
                regex_to_ref.append((re.compile(pattern), file_ref))
            except re.error:
                continue

        name_to_refs = defaultdict(list)
        for mapping_key, mapping_value in (mappings or {}).items():
            if not isinstance(mapping_value, list) or not mapping_value:
                continue
            names = mapping_value[0]
            if isinstance(names, dict):
                iterable = names.values()
            elif isinstance(names, list):
                iterable = names
            else:
                continue

            for node_name in iterable:
                if isinstance(node_name, str) and node_name.strip():
                    name_to_refs[node_name.strip()].append(mapping_key)

        unresolved_refs = set()
        unresolved_types = set()
        node_types_by_ref = defaultdict(set)

        for node_type in missing_node_types:
            refs = name_to_refs.get(node_type.strip())
            if refs:
                for ref in refs:
                    unresolved_refs.add(ref)
                    node_types_by_ref[ref].add(node_type)
                continue

            matched = False
            for regex, ref in regex_to_ref:
                if regex.search(node_type):
                    unresolved_refs.add(ref)
                    node_types_by_ref[ref].add(node_type)
                    matched = True
            if not matched:
                unresolved_types.add(node_type)

        matched_hashes = set()
        matched_nodes_by_hash = defaultdict(set)
        for package in normalized_packs.values():
            match = False
            if package["id"] in unresolved_refs:
                matched_node_types = node_types_by_ref.get(package["id"], set())
                match = True
            else:
                matched_node_types = set()
                for file_ref in package.get("files", []) or []:
                    if file_ref in unresolved_refs:
                        matched_node_types.update(node_types_by_ref.get(file_ref, set()))
                        match = True

            if not match:
                continue

            package_hash = package.get("hash")
            if not package_hash:
                continue
            matched_hashes.add(package_hash)
            matched_nodes_by_hash[package_hash].update(matched_node_types)

        return unresolved_types, {
            "matched_hashes": matched_hashes,
            "matched_nodes_by_hash": {key: sorted(value) for key, value in matched_nodes_by_hash.items()},
        }

    def _build_candidate_rows(self, normalized_packs, missing_match):
        matched_hashes = missing_match["matched_hashes"]
        matched_nodes_by_hash = missing_match["matched_nodes_by_hash"]

        packages_by_hash = {
            package.get("hash"): package
            for package in normalized_packs.values()
            if package.get("hash")
        }
        import_fail_lookup = self._load_import_fail_lookup(
            [packages_by_hash[pack_hash] for pack_hash in matched_hashes if pack_hash in packages_by_hash]
        )

        candidate_rows = []
        for pack_hash in matched_hashes:
            package = packages_by_hash.get(pack_hash)
            if not package:
                continue

            action_state = self._resolve_action_state(package, import_fail_lookup)
            queue_action = self._resolve_queue_action(action_state)
            candidate_rows.append(
                {
                    "id": package["id"],
                    "hash": pack_hash,
                    "title": package["title"],
                    "state": action_state,
                    "raw_state": package.get("state", "unknown"),
                    "status": self._resolve_status_label(action_state),
                    "selected": bool(queue_action),
                    "selectable": bool(queue_action),
                    "queue_action": queue_action,
                    "missing_nodes": list(matched_nodes_by_hash.get(pack_hash, [])),
                    "missing_count": len(matched_nodes_by_hash.get(pack_hash, [])),
                    "conflict_count": int(package.get("conflicts") or 0),
                    "metadata": package["metadata"],
                }
            )

        manual_items = []
        if missing_match["outdated_comfyui"]:
            manual_items.append({"node_type": "comfy-core", "reason": "ComfyUI 内置节点缺失，可能需要升级 ComfyUI。"})
        for cnr_id in missing_match["unresolved_cnr_ids"]:
            manual_items.append({"node_type": cnr_id, "reason": "未在当前 Manager 列表中找到对应的 ComfyRegistry 插件。"})
        for node_type in missing_match["unresolved_types"]:
            manual_items.append({"node_type": node_type, "reason": "未找到可自动映射的插件包。"})

        candidate_rows.sort(key=lambda item: (item["title"].lower(), item["id"].lower()))
        manual_items.sort(key=lambda item: item["node_type"].lower())
        return candidate_rows, manual_items

    def _load_import_fail_lookup(self, packages):
        cnr_ids = []
        urls = []

        for package in packages:
            state = (package.get("state") or "").strip()
            if state not in {"installed", "enabled", "updatable", "disabled"}:
                continue

            if package.get("version") == "unknown":
                repository_url = self._get_primary_repository(package)
                if repository_url:
                    urls.append(repository_url)
            else:
                cnr_ids.append(package.get("id"))

        result = self._manager_api_service.get_import_fail_info_bulk(
            cnr_ids=sorted(set(filter(None, cnr_ids))),
            urls=sorted(set(filter(None, urls))),
        )
        if not result.success:
            return {}
        return result.data or {}

    def _resolve_action_state(self, package, import_fail_lookup):
        if package.get("invalid-installation"):
            return "invalid-installation"

        import_fail = self._resolve_import_fail(package, import_fail_lookup)
        if import_fail or package.get("import-fail"):
            return "import-fail"

        if package.get("update-state") == "true":
            return "updatable"

        state = (package.get("state") or "").strip()
        return state or "unknown"

    def _resolve_import_fail(self, package, import_fail_lookup):
        keys = []
        if package.get("version") != "unknown" and package.get("id"):
            keys.append(package["id"])

        repository_url = self._get_primary_repository(package)
        if repository_url:
            keys.append(repository_url)

        for key in keys:
            info = import_fail_lookup.get(key)
            if info:
                return info
        return None

    @staticmethod
    def _resolve_queue_action(action_state):
        if action_state in {"not-installed", "unknown"}:
            return "install"
        if action_state == "import-fail":
            return "fix"
        if action_state == "invalid-installation":
            return "reinstall"
        if action_state == "disabled":
            return "enable"
        if action_state in {"enabled", "updatable"}:
            return "update"
        return ""

    @staticmethod
    def _resolve_status_label(action_state):
        return {
            "not-installed": "待安装",
            "unknown": "待安装",
            "import-fail": "待修复",
            "invalid-installation": "待重装",
            "disabled": "待启用",
            "enabled": "待更新",
            "updatable": "待更新",
        }.get(action_state, "当前状态")

    @staticmethod
    def _normalize_node_packs(node_packs, installed_nodes, channel, mode):
        installed_by_id = {}
        for key, value in (installed_nodes or {}).items():
            if isinstance(value, dict):
                installed_by_id[str(key).strip()] = dict(value)
                if value.get("id"):
                    installed_by_id[str(value["id"]).strip()] = dict(value)

        normalized = {}
        for key, raw_item in (node_packs or {}).items():
            item = dict(raw_item or {})
            item.setdefault("id", key)
            item.setdefault("title", item.get("name") or item.get("title") or key)
            item.setdefault("files", [])
            item.setdefault("channel", channel or "default")
            item.setdefault("mode", mode or "default")
            item.setdefault("version", item.get("version") or "unknown")
            item.setdefault("hash", item.get("hash") or item["id"])

            installed_item = installed_by_id.get(str(item["id"]).strip())
            if installed_item:
                for installed_key, installed_value in installed_item.items():
                    item.setdefault(installed_key, installed_value)
                if item.get("state") in {"not-installed", "", None}:
                    if installed_item.get("state"):
                        item["state"] = installed_item.get("state")
                    elif "enabled" in installed_item:
                        item["state"] = "enabled" if bool(installed_item.get("enabled")) else "disabled"
                    else:
                        item["state"] = "installed"

            item["metadata"] = dict(item)
            item["metadata"]["ui_id"] = item.get("hash") or item["id"]
            normalized[key] = item
        return normalized

    @staticmethod
    def _build_aux_id_map(normalized_packs):
        aux_id_to_pack = {}
        for package in normalized_packs.values():
            aux_id = MissingNodeInstallOrchestrator._extract_aux_id(package)
            if aux_id:
                aux_id_to_pack[aux_id] = package
        return aux_id_to_pack

    @staticmethod
    def _mark_package_match(package, node_type, matched_hashes, matched_nodes_by_hash):
        package_hash = package.get("hash")
        if not package_hash:
            return
        matched_hashes.add(package_hash)
        matched_nodes_by_hash[package_hash].add(node_type)

    @staticmethod
    def _extract_aux_id(package):
        repository = MissingNodeInstallOrchestrator._get_primary_repository(package)
        if not repository:
            return ""

        normalized = repository.strip().rstrip("/")
        if normalized.lower().startswith("https://github.com/"):
            parts = normalized.split("/")
            if len(parts) >= 2:
                return "/".join(parts[-2:]).lower()
        return normalized.split("/")[-1].lower()

    @staticmethod
    def _get_primary_repository(package):
        repository = package.get("repository")
        if isinstance(repository, str) and repository.strip():
            return repository.strip()
        return MissingNodeInstallOrchestrator._get_primary_file(package)

    @staticmethod
    def _get_primary_file(package):
        files = package.get("files", []) or []
        if files:
            first = files[0]
            if isinstance(first, str) and first.strip():
                return first.strip()
        return ""
