"""Bounded read-only U-Connect REST gateway for the experimental UQA MCP server.

Not a PASS oracle, not a replacement for UQA Core permissions. Route selection
is fixed in trusted code; neither model nor caller can provide arbitrary URLs.
"""
from __future__ import annotations

import re
from urllib.parse import urlsplit

import httpx


class GatewayConfigurationError(ValueError):
    pass


class ReadOnlyGateway:
    ROUTES = {
        "collections": "ci-collection",
        "policies": "policy",
        "procedures": "procedures",
    }
    PUBLIC_FIELDS = frozenset({"id", "uid", "name", "type", "active", "is_active"})
    MAX_RESPONSE_BYTES = 256 * 1024
    MAX_LIMIT = 50

    def __init__(
        self,
        origin: str,
        api_prefix: str,
        *,
        bearer_token: str | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        parsed = urlsplit(origin)
        if (
            parsed.scheme != "https" or not parsed.hostname
            or parsed.username or parsed.password or parsed.query or parsed.fragment
            or parsed.path not in ("", "/") or origin.rstrip("/") !=
            f"{parsed.scheme}://{parsed.netloc}"
        ):
            raise GatewayConfigurationError("exact_https_origin_required")
        if not isinstance(api_prefix, str) or not re.fullmatch(
            r"/[A-Za-z0-9_-]+(?:/[A-Za-z0-9_-]+)*", api_prefix
        ):
            raise GatewayConfigurationError("operator_pinned_api_prefix_required")

        self.origin = origin.rstrip("/")
        self.api_prefix = api_prefix
        self._owned_client = client is None
        if client is not None:
            self._client = client
        else:
            if not bearer_token or not bearer_token.strip():
                raise GatewayConfigurationError("operator_auth_not_configured")
            self._client = httpx.Client(
                base_url=self.origin,
                headers={"Authorization": "Bearer " + bearer_token},
                timeout=httpx.Timeout(15.0, connect=5.0),
                follow_redirects=False,
                verify=True,
                trust_env=False,
            )

    def close(self) -> None:
        if self._owned_client:
            self._client.close()

    def __enter__(self) -> "ReadOnlyGateway":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    @staticmethod
    def unavailable(kind: str, reason: str, http_status: int | None = None) -> dict:
        answer = {
            "observation_status": "unavailable",
            "resource": kind,
            "reason": reason,
            "mutation_executed": False,
            "business_pass": False,
        }
        if http_status is not None:
            answer["http_status"] = http_status
        return answer

    def list_resources(self, kind: str, *, limit: int = 20, offset: int = 0) -> dict:
        if kind not in self.ROUTES:
            return self.unavailable(kind, "unregistered_business_operation")
        if (type(limit) is not int or not 1 <= limit <= self.MAX_LIMIT
                or type(offset) is not int or not 0 <= offset <= 100_000):
            return self.unavailable(kind, "invalid_pagination")

        # Explicitly pinned API gateway root, not an inferred route or URL.
        path = f"{self.api_prefix}/{self.ROUTES[kind]}"
        try:
            response = self._client.get(
                path, params={"limit": limit, "offset": offset},
                follow_redirects=False,
            )
        except httpx.RequestError:
            return self.unavailable(kind, "api_transport_unavailable")

        if response.status_code != 200:
            reason = (
                "api_authorization_failed" if response.status_code in (401, 403)
                else "api_redirect_refused" if 300 <= response.status_code < 400
                else "api_non_200"
            )
            return self.unavailable(kind, reason, response.status_code)
        if len(response.content) > self.MAX_RESPONSE_BYTES:
            return self.unavailable(kind, "api_response_too_large")
        content_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
        if content_type != "application/json" and not content_type.endswith("+json"):
            return self.unavailable(kind, "api_non_json_response")
        try:
            data = response.json()
        except (ValueError, RecursionError):
            return self.unavailable(kind, "api_invalid_json")

        if isinstance(data, dict):
            rows = data.get("items")
            total = data.get("total")
            if total is None:
                total = data.get("count")
        elif isinstance(data, list):
            rows, total = data, None
        else:
            return self.unavailable(kind, "api_unexpected_response_shape")
        if not isinstance(rows, list) or len(rows) > self.MAX_LIMIT:
            return self.unavailable(kind, "api_unexpected_response_shape")
        if total is not None and (type(total) is not int or total < 0):
            return self.unavailable(kind, "api_unexpected_pagination_shape")

        redacted = []
        for row in rows:
            if not isinstance(row, dict):
                return self.unavailable(kind, "api_unexpected_item_shape")
            item = {}
            for key in self.PUBLIC_FIELDS:
                value = row.get(key)
                if isinstance(value, str) and len(value) <= 256:
                    item[key] = value
                elif type(value) in (bool, int):
                    item[key] = value
            redacted.append(item)

        return {
            "observation_status": "observed",
            "resource": kind,
            "source": "uconnect_api_readonly",
            "items": redacted,
            "returned_count": len(redacted),
            "total": total,
            "limit": limit,
            "offset": offset,
            "mutation_executed": False,
            "business_pass": False,
        }
