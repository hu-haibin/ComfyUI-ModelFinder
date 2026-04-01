import json
import urllib.error
import urllib.request
from typing import Callable, Optional

from .operation_result import OperationResult


class ComfyUIManagerApiService:
    def __init__(
        self,
        *,
        base_url_provider: Callable[[], str],
        http_requester: Optional[Callable[..., tuple[int, str]]] = None,
        timeout: float = 2.0,
    ):
        self._base_url_provider = base_url_provider
        self._http_requester = http_requester or self._default_http_requester
        self._timeout = timeout

    def is_available(self) -> OperationResult:
        version_result = self.get_version()
        if not version_result.success:
            return OperationResult(False, version_result.message, code="manager_unavailable")

        return OperationResult(True, "ComfyUI-Manager is available.", version_result.data, code="manager_available")

    def get_version(self) -> OperationResult:
        return self._request_text("GET", "/manager/version", code="manager_version_loaded")

    def get_db_mode(self) -> OperationResult:
        return self._request_text("GET", "/manager/db_mode", code="manager_db_mode_loaded")

    def get_node_mappings(self, mode: str) -> OperationResult:
        return self._request_json("GET", f"/customnode/getmappings?mode={mode}", code="manager_mappings_loaded")

    def get_custom_node_list(self, mode: str) -> OperationResult:
        return self._request_json("GET", f"/customnode/getlist?mode={mode}&skip_update=true", code="manager_node_list_loaded")

    def get_installed_nodes(self, mode: str = "default") -> OperationResult:
        return self._request_json("GET", f"/customnode/installed?mode={mode}", code="manager_installed_loaded")

    def get_alternatives(self, mode: str) -> OperationResult:
        return self._request_json("GET", f"/customnode/alternatives?mode={mode}", code="manager_alternatives_loaded")

    def get_import_fail_info_bulk(self, *, cnr_ids=None, urls=None) -> OperationResult:
        payload = {}
        if cnr_ids:
            payload["cnr_ids"] = list(cnr_ids)
        if urls:
            payload["urls"] = list(urls)
        if not payload:
            return OperationResult(True, "No import-fail targets requested.", {}, code="manager_import_fail_info_empty")

        return self._request_json(
            "POST",
            "/v2/customnode/import_fail_info_bulk",
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

        return self._request_json(
            "POST",
            "/manager/queue/install",
            payload=payload,
            code="manager_install_queued",
            allow_empty_json=True,
        )

    def queue_fix(self, node_package_metadata: dict) -> OperationResult:
        payload = dict(node_package_metadata or {})
        payload.setdefault("ui_id", payload.get("id") or payload.get("name") or payload.get("title") or "batch-fix")
        return self._request_json(
            "POST",
            "/manager/queue/fix",
            payload=payload,
            code="manager_fix_queued",
            allow_empty_json=True,
        )

    def queue_reinstall(self, node_package_metadata: dict) -> OperationResult:
        payload = dict(node_package_metadata or {})
        payload.setdefault("ui_id", payload.get("id") or payload.get("name") or payload.get("title") or "batch-reinstall")
        return self._request_json(
            "POST",
            "/manager/queue/reinstall",
            payload=payload,
            code="manager_reinstall_queued",
            allow_empty_json=True,
        )

    def queue_update(self, node_package_metadata: dict) -> OperationResult:
        payload = dict(node_package_metadata or {})
        payload.setdefault("ui_id", payload.get("id") or payload.get("name") or payload.get("title") or "batch-update")
        return self._request_json(
            "POST",
            "/manager/queue/update",
            payload=payload,
            code="manager_update_queued",
            allow_empty_json=True,
        )

    def start_queue(self) -> OperationResult:
        return self._request_json("GET", "/manager/queue/start", code="manager_queue_started", allow_empty_json=True)

    def get_queue_status(self) -> OperationResult:
        return self._request_json("GET", "/manager/queue/status", code="manager_queue_status_loaded")

    def _request_text(self, method: str, path: str, *, code: str) -> OperationResult:
        try:
            status, body = self._http_requester(
                method=method,
                url=f"{self._base_url_provider().rstrip('/')}{path}",
                payload=None,
                timeout=self._timeout,
            )
        except Exception as exc:
            return OperationResult(False, f"请求 Manager 服务失败: {exc}", code="manager_request_failed")

        if status >= 400:
            detail = body.strip() if body else ""
            message = f"Manager 服务返回错误状态码: {status}"
            if detail:
                message = f"{message} - {detail}"
            return OperationResult(False, message, {"status": status, "body": detail}, code="manager_http_error")

        return OperationResult(True, "Request succeeded.", {"value": body.strip()}, code=code)

    def _request_json(self, method: str, path: str, *, payload=None, code: str, allow_empty_json: bool = False) -> OperationResult:
        try:
            status, body = self._http_requester(
                method=method,
                url=f"{self._base_url_provider().rstrip('/')}{path}",
                payload=payload,
                timeout=self._timeout,
            )
        except Exception as exc:
            return OperationResult(False, f"请求 Manager 服务失败: {exc}", code="manager_request_failed")

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
