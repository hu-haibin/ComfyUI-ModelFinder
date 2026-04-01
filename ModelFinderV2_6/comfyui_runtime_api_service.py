import json
import urllib.error
import urllib.request
from typing import Callable, Optional

from .operation_result import OperationResult


class ComfyUIRuntimeApiService:
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
        result = self.get_registered_node_types()
        if not result.success:
            return OperationResult(False, result.message, code="runtime_unavailable")

        return OperationResult(True, "ComfyUI runtime is available.", result.data, code="runtime_available")

    def get_registered_node_types(self) -> OperationResult:
        response = self._request_json("GET", "/object_info")
        if not response.success:
            return response

        payload = response.data
        if not isinstance(payload, dict):
            return OperationResult(False, "ComfyUI 返回了无效的节点信息。", code="invalid_object_info")

        node_types = sorted(payload.keys())
        return OperationResult(
            True,
            "Registered node types loaded.",
            {"node_types": node_types, "count": len(node_types)},
            code="registered_node_types_loaded",
        )

    def _request_json(self, method: str, path: str, payload=None) -> OperationResult:
        try:
            status, body = self._http_requester(
                method=method,
                url=f"{self._base_url_provider().rstrip('/')}{path}",
                payload=payload,
                timeout=self._timeout,
            )
        except Exception as exc:
            return OperationResult(False, f"请求 ComfyUI 服务失败: {exc}", code="runtime_request_failed")

        if status >= 400:
            return OperationResult(False, f"ComfyUI 服务返回错误状态码: {status}", code="runtime_http_error")

        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            return OperationResult(False, "ComfyUI 返回了无法解析的 JSON。", code="runtime_invalid_json")

        return OperationResult(True, "Request succeeded.", data, code="runtime_request_succeeded")

    @staticmethod
    def _default_http_requester(*, method: str, url: str, payload=None, timeout: float = 2.0) -> tuple[int, str]:
        data = None
        headers = {}
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"

        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.getcode(), response.read().decode("utf-8")
