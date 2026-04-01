import json
from pathlib import Path
import urllib.error
import urllib.request
from typing import Callable, Optional

from .operation_result import OperationResult


class ComfyUIManagerApiService:
    def __init__(
        self,
        *,
        base_url_provider: Callable[[], str],
        comfyui_path_provider: Optional[Callable[[], str]] = None,
        http_requester: Optional[Callable[..., tuple[int, str]]] = None,
        timeout: float = 2.0,
    ):
        self._base_url_provider = base_url_provider
        self._comfyui_path_provider = comfyui_path_provider or (lambda: "")
        self._http_requester = http_requester or self._default_http_requester
        self._timeout = timeout
        self._api_prefix: Optional[str] = None

    def is_available(self) -> OperationResult:
        version_result = self.get_version()
        if not version_result.success:
            return OperationResult(False, version_result.message, code="manager_unavailable")

        return OperationResult(True, "ComfyUI-Manager is available.", version_result.data, code="manager_available")

    def get_version(self) -> OperationResult:
        return self._request_text_candidates(
            "GET",
            ["/manager/version", "/v2/manager/version"],
            code="manager_version_loaded",
            remember_prefix=True,
        )

    def get_db_mode(self) -> OperationResult:
        return self._request_text_candidates(
            "GET",
            self._versioned_candidates("/manager/db_mode"),
            code="manager_db_mode_loaded",
        )

    def get_node_mappings(self, mode: str) -> OperationResult:
        return self._request_json_candidates(
            "GET",
            self._versioned_candidates(f"/customnode/getmappings?mode={mode}"),
            code="manager_mappings_loaded",
        )

    def get_custom_node_list(self, mode: str) -> OperationResult:
        result = self._request_json_candidates(
            "GET",
            self._versioned_candidates(f"/customnode/getlist?mode={mode}&skip_update=true"),
            code="manager_node_list_loaded",
        )
        if result.success:
            return result

        fallback_result = self._load_custom_node_list_from_disk(mode)
        if fallback_result.success:
            return fallback_result
        return result

    def get_installed_nodes(self, mode: str = "default") -> OperationResult:
        return self._request_json_candidates(
            "GET",
            self._versioned_candidates(f"/customnode/installed?mode={mode}"),
            code="manager_installed_loaded",
        )

    def get_alternatives(self, mode: str) -> OperationResult:
        return self._request_json_candidates(
            "GET",
            self._versioned_candidates(f"/customnode/alternatives?mode={mode}"),
            code="manager_alternatives_loaded",
        )

    def get_import_fail_info_bulk(self, *, cnr_ids=None, urls=None) -> OperationResult:
        payload = {}
        if cnr_ids:
            payload["cnr_ids"] = list(cnr_ids)
        if urls:
            payload["urls"] = list(urls)
        if not payload:
            return OperationResult(True, "No import-fail targets requested.", {}, code="manager_import_fail_info_empty")

        return self._request_json_candidates(
            "POST",
            ["/v2/customnode/import_fail_info_bulk", "/customnode/import_fail_info_bulk"],
            payload=payload,
            code="manager_import_fail_info_loaded",
        )

    def queue_install(
        self,
        node_package_metadata: dict,
        selected_version: Optional[str] = None,
        skip_post_install: bool = False,
    ) -> OperationResult:
        payload = dict(node_package_metadata or {})
        payload.setdefault("ui_id", payload.get("id") or payload.get("name") or payload.get("title") or "batch-install")
        if selected_version is not None:
            payload["selected_version"] = selected_version
        if skip_post_install:
            payload["skip_post_install"] = True

        return self._request_json_candidates(
            "POST",
            self._versioned_candidates("/manager/queue/install"),
            payload=payload,
            code="manager_install_queued",
            allow_empty_json=True,
        )

    def queue_fix(self, node_package_metadata: dict) -> OperationResult:
        payload = dict(node_package_metadata or {})
        payload.setdefault("ui_id", payload.get("id") or payload.get("name") or payload.get("title") or "batch-fix")
        return self._request_json_candidates(
            "POST",
            self._versioned_candidates("/manager/queue/fix"),
            payload=payload,
            code="manager_fix_queued",
            allow_empty_json=True,
        )

    def queue_reinstall(self, node_package_metadata: dict) -> OperationResult:
        payload = dict(node_package_metadata or {})
        payload.setdefault("ui_id", payload.get("id") or payload.get("name") or payload.get("title") or "batch-reinstall")
        return self._request_json_candidates(
            "POST",
            self._versioned_candidates("/manager/queue/reinstall"),
            payload=payload,
            code="manager_reinstall_queued",
            allow_empty_json=True,
        )

    def queue_update(self, node_package_metadata: dict) -> OperationResult:
        payload = dict(node_package_metadata or {})
        payload.setdefault("ui_id", payload.get("id") or payload.get("name") or payload.get("title") or "batch-update")
        return self._request_json_candidates(
            "POST",
            self._versioned_candidates("/manager/queue/update"),
            payload=payload,
            code="manager_update_queued",
            allow_empty_json=True,
        )

    def start_queue(self) -> OperationResult:
        return self._request_json_candidates(
            "GET",
            self._versioned_candidates("/manager/queue/start"),
            code="manager_queue_started",
            allow_empty_json=True,
        )

    def get_queue_status(self) -> OperationResult:
        return self._request_json_candidates(
            "GET",
            self._versioned_candidates("/manager/queue/status"),
            code="manager_queue_status_loaded",
        )

    def _request_text_candidates(
        self,
        method: str,
        paths: list[str],
        *,
        code: str,
        remember_prefix: bool = False,
    ) -> OperationResult:
        last_error = None
        for path in self._dedupe_paths(paths):
            result = self._request_text(method, path, code=code)
            if result.success:
                if remember_prefix:
                    self._remember_api_prefix(path)
                return result
            last_error = result
            if result.code != "manager_http_error" or result.data.get("status") not in {404, 405}:
                return result
        return last_error or OperationResult(False, "Manager request failed.", code="manager_request_failed")

    def _request_json_candidates(
        self,
        method: str,
        paths: list[str],
        *,
        payload=None,
        code: str,
        allow_empty_json: bool = False,
    ) -> OperationResult:
        last_error = None
        for path in self._dedupe_paths(paths):
            result = self._request_json(method, path, payload=payload, code=code, allow_empty_json=allow_empty_json)
            if result.success:
                self._remember_api_prefix(path)
                return result
            last_error = result
            if result.code != "manager_http_error" or result.data.get("status") not in {404, 405}:
                return result
        return last_error or OperationResult(False, "Manager request failed.", code="manager_request_failed")

    def _request_text(self, method: str, path: str, *, code: str) -> OperationResult:
        status, body, exc = self._perform_request(method, path, payload=None)
        if exc is not None:
            return OperationResult(False, f"请求 Manager 服务失败: {exc}", code="manager_request_failed")
        return self._build_text_result(status, body, code=code)

    def _request_json(self, method: str, path: str, *, payload=None, code: str, allow_empty_json: bool = False) -> OperationResult:
        status, body, exc = self._perform_request(method, path, payload=payload)
        if exc is not None:
            return OperationResult(False, f"请求 Manager 服务失败: {exc}", code="manager_request_failed")
        return self._build_json_result(status, body, code=code, allow_empty_json=allow_empty_json)

    def _perform_request(self, method: str, path: str, *, payload=None) -> tuple[Optional[int], str, Optional[Exception]]:
        try:
            status, body = self._http_requester(
                method=method,
                url=f"{self._base_url_provider().rstrip('/')}{path}",
                payload=payload,
                timeout=self._timeout,
            )
            return status, body, None
        except Exception as exc:
            return None, "", exc

    @staticmethod
    def _build_text_result(status: int, body: str, *, code: str) -> OperationResult:
        if status >= 400:
            detail = body.strip() if body else ""
            message = f"Manager 服务返回错误状态码: {status}"
            if detail:
                message = f"{message} - {detail}"
            return OperationResult(False, message, {"status": status, "body": detail}, code="manager_http_error")

        return OperationResult(True, "Request succeeded.", {"value": body.strip()}, code=code)

    @staticmethod
    def _build_json_result(status: int, body: str, *, code: str, allow_empty_json: bool = False) -> OperationResult:
        if status >= 400:
            detail = body.strip() if body else ""
            message = f"Manager 服务返回错误状态码: {status}"
            if detail:
                message = f"{message} - {detail}"
            return OperationResult(False, message, {"status": status, "body": detail}, code="manager_http_error")

        if not body.strip():
            if allow_empty_json:
                return OperationResult(True, "Request succeeded.", {}, code=code)
            return OperationResult(False, "Manager 返回了空响应。", code="manager_empty_response")

        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            if allow_empty_json:
                return OperationResult(True, "Request succeeded.", {"raw": body}, code=code)
            return OperationResult(False, "Manager 返回了无法解析的 JSON。", code="manager_invalid_json")

        return OperationResult(True, "Request succeeded.", data, code=code)

    def _versioned_candidates(self, legacy_path: str) -> list[str]:
        if self._api_prefix == "/v2":
            return [f"/v2{legacy_path}", legacy_path]
        if self._api_prefix == "":
            return [legacy_path, f"/v2{legacy_path}"]
        return [legacy_path, f"/v2{legacy_path}"]

    @staticmethod
    def _dedupe_paths(paths: list[str]) -> list[str]:
        ordered = []
        seen = set()
        for path in paths:
            if path not in seen:
                ordered.append(path)
                seen.add(path)
        return ordered

    def _remember_api_prefix(self, path: str) -> None:
        self._api_prefix = "/v2" if path.startswith("/v2/") else ""

    def _load_custom_node_list_from_disk(self, mode: str) -> OperationResult:
        for path in self._local_custom_node_list_candidates():
            if not path.exists():
                continue
            try:
                with path.open("r", encoding="utf-8") as handle:
                    data = json.load(handle)
            except Exception:
                continue

            normalized = self._normalize_local_custom_node_list(data, mode)
            if normalized["node_packs"]:
                return OperationResult(
                    True,
                    "Loaded custom node list from local Manager cache.",
                    normalized,
                    code="manager_node_list_loaded",
                )

        return OperationResult(False, "未找到可用的 Manager 插件列表缓存。", code="manager_node_list_unavailable")

    def _local_custom_node_list_candidates(self) -> list[Path]:
        comfyui_path = Path((self._comfyui_path_provider() or "").strip())
        if not comfyui_path:
            return []

        candidates = []
        cache_dir = comfyui_path / "user" / "__manager" / "cache"
        if cache_dir.exists():
            candidates.extend(sorted(cache_dir.glob("*_custom-node-list.json"), reverse=True))

        manager_root = comfyui_path / "custom_nodes" / "ComfyUI-Manager"
        candidates.extend(
            [
                manager_root / "comfyui_manager" / "custom-node-list.json",
                manager_root / "build" / "lib" / "comfyui_manager" / "custom-node-list.json",
                manager_root / "node_db" / "new" / "custom-node-list.json",
                manager_root / "node_db" / "legacy" / "custom-node-list.json",
            ]
        )
        return candidates

    @staticmethod
    def _normalize_local_custom_node_list(data, mode: str) -> dict:
        if isinstance(data, dict) and "node_packs" in data:
            normalized = dict(data)
            normalized.setdefault("channel", "default")
            normalized.setdefault("mode", mode or "default")
            return normalized

        if isinstance(data, dict):
            entries = data.get("custom_nodes") or []
        elif isinstance(data, list):
            entries = data
        else:
            entries = []

        node_packs = {}
        for entry in entries:
            if not isinstance(entry, dict):
                continue

            pack_id = str(entry.get("id") or "").strip()
            if not pack_id:
                continue

            pack = dict(entry)
            reference = pack.get("reference")
            files = [item for item in (pack.get("files") or []) if isinstance(item, str) and item.strip()]
            if not files and isinstance(reference, str) and reference.strip():
                files = [reference.strip()]

            pack.setdefault("title", pack.get("name") or pack_id)
            pack["files"] = files
            if isinstance(reference, str) and reference.strip():
                pack.setdefault("repository", reference.strip())
            pack.setdefault("state", "not-installed")
            pack.setdefault("channel", "default")
            pack.setdefault("mode", mode or "default")
            node_packs[pack_id] = pack

        return {"channel": "default", "mode": mode or "default", "node_packs": node_packs}

    @staticmethod
    def _default_http_requester(*, method: str, url: str, payload=None, timeout: float = 2.0) -> tuple[int, str]:
        data = None
        headers = {}
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"

        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.getcode(), response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read().decode("utf-8", errors="replace")
