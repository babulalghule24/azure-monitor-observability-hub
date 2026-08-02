"""Local tester for the VM Inventory MCP server.

WHAT IT DOES
  1. Connects to your running server over MCP (streamable HTTP).
  2. Lists the tool it exposes  -> proves the server works. NEEDS NO AZURE LOGIN.
  3. Calls get_vm_inventory end-to-end -> this DOES call Azure (needs `az login` + Reader).
  4. Runs a negative test with a bogus subscription id -> should fail cleanly, not hang.

HOW TO RUN
  Terminal 1:  python server.py            # leave it running (serves http://localhost:8000/mcp)
  Terminal 2:  az login                    # so DefaultAzureCredential has an identity
               # tell it which subscriptions to inventory:
               #   macOS/Linux : export AZURE_SUBSCRIPTION_IDS="00000000-0000-0000-0000-000000000000"
               #   Windows PS  : $env:AZURE_SUBSCRIPTION_IDS="00000000-0000-0000-0000-000000000000"
               python test_local.py

You can also pass a different URL:  python test_local.py http://localhost:8000/mcp
"""
from __future__ import annotations

import asyncio
import json
import os
import sys

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

# ------------------------- CONFIG ---------------------------------
SERVER_URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000/mcp"
SUBSCRIPTIONS = [s for s in os.environ.get("AZURE_SUBSCRIPTION_IDS", "").split(",") if s.strip()]
# ------------------------------------------------------------------


def _show(title, result):
    print(f"\n--- {title} ---")
    if getattr(result, "isError", False):
        print("(the tool reported an error)")
    # FastMCP returns your dict as structured content; fall back to text if needed.
    if getattr(result, "structuredContent", None):
        print(json.dumps(result.structuredContent, indent=2)[:2500])
    else:
        for c in result.content:
            print(getattr(c, "text", c))


async def main():
    print(f"Connecting to {SERVER_URL} ...")
    async with streamablehttp_client(SERVER_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("Connected - MCP handshake OK.\n")

            # ---- 1. List the tool (no Azure needed) ----
            tools = await session.list_tools()
            print(f"Server exposes {len(tools.tools)} tool(s):")
            for t in tools.tools:
                first_line = (t.description or "").strip().splitlines()[0] if t.description else ""
                print(f"  - {t.name}: {first_line}")

            # ---- 2. Call get_vm_inventory for real (calls Azure) ----
            if not SUBSCRIPTIONS:
                print("\nList-only mode (no Azure calls). Set AZURE_SUBSCRIPTION_IDS and run")
                print("`az login`, then re-run to call get_vm_inventory.")
                return

            r = await session.call_tool("get_vm_inventory", {"subscriptions": SUBSCRIPTIONS})
            _show(f"get_vm_inventory({len(SUBSCRIPTIONS)} subscription(s))", r)

            # ---- 3. Negative test: a bogus subscription id should fail cleanly ----
            # Azure rejects the invalid GUID with a long "support" message; that's the
            # EXPECTED behaviour, so we just confirm isError and print one clean line
            # instead of dumping the whole error body.
            bogus = await session.call_tool("get_vm_inventory", {"subscriptions": ["not-a-real-subscription"]})
            if getattr(bogus, "isError", False):
                print("\nNegative test (bogus subscription): PASS - server rejected it cleanly (isError=True)")
            else:
                print("\nNegative test (bogus subscription): UNEXPECTED - expected an error but got a result")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as ex:
        print(f"\nERROR: {ex}")
        print("Checklist:  (1) is server.py running in another terminal?  "
              "(2) is the URL right (default http://localhost:8000/mcp)?  "
              "(3) same venv activated (so 'mcp' is installed)?")
