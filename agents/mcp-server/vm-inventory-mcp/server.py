"""MCP server — Azure VM Capacity Planner: VM Inventory sample.

A focused starter kit extracted from the full capacity-planning MCP server. It
exposes a single tool, get_vm_inventory, which reports region/zone-wise VM & VMSS
SKU inventory across subscriptions using Azure Resource Graph.

- Transport: streamable HTTP (so Copilot Studio / VS Code / Agent Framework can reach it).
- Auth to Azure:
    * In Azure Container Apps -> the container's MANAGED IDENTITY (no secrets in code).
      System-assigned works out of the box; for a user-assigned identity also set the
      env var AZURE_CLIENT_ID to that identity's client id.
    * Locally -> your `az login` (DefaultAzureCredential).
- Access needed: Reader on the target subscription(s), granted to that identity.
- Endpoint: http://localhost:8000/mcp
"""
from __future__ import annotations

import os
from typing import List

from mcp.server.fastmcp import FastMCP
from azure.identity import DefaultAzureCredential, ManagedIdentityCredential

import vmcp

# host/port so it binds correctly inside the container (honors the Dockerfile ENV).
mcp = FastMCP(
    "vm-inventory-mcp",
    host=os.environ.get("HOST", "0.0.0.0"),
    port=int(os.environ.get("PORT", "8000")),
)

def _build_credential():
    """Choose the right Azure credential for wherever this runs.

    In Azure Container Apps a managed identity is injected (IDENTITY_ENDPOINT is set),
    so we use ManagedIdentityCredential DIRECTLY -- no secrets, no keys.
      - SYSTEM-assigned identity: nothing else to set.
      - USER-assigned identity: also set the env var AZURE_CLIENT_ID to that identity's
        client id, so we bind to the correct one.
    Locally (no managed identity) we fall back to your `az login` via DefaultAzureCredential.
    """
    client_id = os.environ.get("AZURE_CLIENT_ID")  # set only for a user-assigned identity
    if os.environ.get("IDENTITY_ENDPOINT"):
        if client_id:
            return ManagedIdentityCredential(client_id=client_id)
        return ManagedIdentityCredential()
    return DefaultAzureCredential()


# Managed identity in the cloud, az login locally.
_cred = _build_credential()


@mcp.tool()
def get_vm_inventory(subscriptions: List[str]) -> dict:
    """Region/zone-wise VM & VMSS SKU inventory across subscriptions (Azure Resource Graph).
    Needs azure-mgmt-resourcegraph + Reader on the subscriptions. (VMCP 'inventory')."""
    return vmcp.inventory_vm_skus(_cred, subscriptions)


if __name__ == "__main__":
    # Remote hosting: expose over HTTP so Copilot Studio / Agent Framework can reach it.
    # Your MCP endpoint will be  http://localhost:8000/mcp  (https://<app-url>/mcp in the cloud)
    mcp.run(transport="streamable-http")
