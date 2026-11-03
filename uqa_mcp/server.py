"""Experimental stdio MCP service.

The service is NOT currently wired into uqa.py / Ollama. It runs as a
separate process under an explicitly configured, dedicated read-only identity.
No mutations, operator shell, arbitrary HTTP, or automatic browser fallback.
"""
from __future__ import annotations

import os

from mcp.server import MCPServer

from uqa_mcp.gateway import ReadOnlyGateway, GatewayConfigurationError


mcp = MCPServer("uqa-uconnect-readonly")


def _read(kind: str, limit: int, offset: int) -> dict:
    # No default environment or inferred auth. Fail closed if not configured.
    origin = os.environ.get("UQA_MCP_UC_ORIGIN", "")
    prefix = os.environ.get("UQA_MCP_UC_API_PREFIX", "")
    token = os.environ.get("UQA_MCP_UC_READONLY_TOKEN", "")
    if not origin or not prefix or not token:
        return ReadOnlyGateway.unavailable(kind, "operator_configuration_required")
    try:
        with ReadOnlyGateway(origin, prefix, bearer_token=token) as gateway:
            return gateway.list_resources(kind, limit=limit, offset=offset)
    except GatewayConfigurationError:
        return ReadOnlyGateway.unavailable(kind, "invalid_operator_configuration")


@mcp.tool()
def uconnect_list_collections(limit: int = 20, offset: int = 0) -> dict:
    """Read U-Connect CI collections. No UI actions, create, update, delete or PASS."""
    return _read("collections", limit, offset)


@mcp.tool()
def uconnect_list_policies(limit: int = 20, offset: int = 0) -> dict:
    """Read U-Connect policy definitions, not policy jobs or job execution."""
    return _read("policies", limit, offset)


@mcp.tool()
def uconnect_list_procedures(limit: int = 20, offset: int = 0) -> dict:
    """Read U-Connect procedure templates, not launch or execution."""
    return _read("procedures", limit, offset)


if __name__ == "__main__":
    mcp.run(transport="stdio")
