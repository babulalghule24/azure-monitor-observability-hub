"""Cloud tester for the SECURED VM Inventory MCP server (Microsoft Entra ID protected).

This is the same as test_local.py, plus a bearer token on every request.

HOW TO RUN
  # 1) get a token for your app's API scope and store it (never hard-code it):
  #    macOS/Linux : export MCP_TOKEN=$(az account get-access-token --resource api://<YOUR_APP_ID> --query accessToken -o tsv)
  #    Windows PS  : $env:MCP_TOKEN = az account get-access-token --resource api://<YOUR_APP_ID> --query accessToken -o tsv
  # 2) tell it which subscriptions to inventory:
  #    export AZURE_SUBSCRIPTION_IDS="00000000-0000-0000-0000-000000000000"
  # 3) run it, passing your app URL:
  #    python test_cloud.py https://<your-app-fqdn>/mcp

A valid token lists the tool (and returns inventory); a missing/expired one -> 401 Unauthorized,
which is the proof that your Entra ID protection is switched on.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

# ------------------------- CONFIG ---------------------------------
SERVER_URL = sys.argv[1] if len(sys.argv) > 1 else "https://<your-app-fqdn>/mcp"
TOKEN = os.environ["MCP_TOKEN"]              # read the token from the environment
SUBSCRIPTIONS = [s for s in os.environ.get("AZURE_SUBSCRIPTION_IDS", "").split(",") if s.strip()]
# ------------------------------------------------------------------


def _show(title, result):
    print(f"\n--- {title} ---")
    if getattr(result, "structuredContent", None):
        print(json.dumps(result.structuredContent, indent=2)[:2500])
    else:
        for c in result.content:
            print(getattr(c, "text", c))


async def main():
    # This one extra line is the only real difference from the local test:
    headers = {"Authorization": f"Bearer {TOKEN}"}

    print(f"Connecting to {SERVER_URL} ...")
    async with streamablehttp_client(SERVER_URL, headers=headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("Authenticated - MCP handshake OK.\n")

            tools = await session.list_tools()
            print(f"Server exposes {len(tools.tools)} tool(s):")
            for t in tools.tools:
                print(f"  - {t.name}")

            if SUBSCRIPTIONS:
                r = await session.call_tool("get_vm_inventory", {"subscriptions": SUBSCRIPTIONS})
                _show(f"get_vm_inventory({len(SUBSCRIPTIONS)} subscription(s))", r)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as ex:
        print(f"\nERROR: {ex}")
        print("Checklist:  (1) MCP_TOKEN set and not expired?  (2) URL correct (ends with /mcp)?  "
              "(3) built-in auth enabled on the Container App?")
