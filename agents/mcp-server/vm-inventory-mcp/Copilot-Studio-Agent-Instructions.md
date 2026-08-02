# Connect the VM Inventory MCP server to a Copilot Studio agent

This kit exposes one tool — **`get_vm_inventory(subscriptions)`** — which returns a
region/zone-wise VM & VMSS SKU inventory across Azure subscriptions (read-only, via Azure
Resource Graph). Below are (1) the values for the **Add MCP server** dialog and (2) the
**agent instructions** to paste into your Copilot Studio agent.

> Prerequisite: your server must be reachable over HTTPS. Deploy it to Azure Container
> Apps first (see README section 8) so you have a URL like
> `https://vm-inventory-mcp.<region>.azurecontainerapps.io/mcp`. A `http://localhost`
> URL will NOT work from Copilot Studio — it runs in the cloud, not on your machine.
> The deployed app reads Azure through its **managed identity** (granted `Reader`), so
> there are no secrets in the container — see README section 8 for the one-time setup.

---

## 1. Add the server — "Add MCP server" dialog

In Copilot Studio: open your agent → **Tools** → **Add a tool** → **Model Context
Protocol** (or **+ New tool → Model Context Protocol**). Fill the dialog with:

| Field | Value to enter |
| --- | --- |
| **Server name** | `VM Inventory` |
| **Server description** | *(paste the description below)* |
| **Server URL** / **Streamable endpoint** | `https://<your-app-fqdn>/mcp` *(use your own app's FQDN + `/mcp`)* |
| **Transport** (if asked) | `Streamable HTTP` |
| **Authentication** | For an Entra-secured app: **OAuth 2.0** (use your app registration's client ID / scope `api://<YOUR_APP_ID>/access_as_user`). For an unauthenticated test app: **No authentication**. |

**Server description — copy/paste this:**
```
Read-only Azure VM capacity tool. Returns a region- and availability-zone-wise
inventory of virtual machines and VM Scale Sets, with SKU counts, across one or
more Azure subscriptions. Backed by Azure Resource Graph. Use it to answer
questions about what VM sizes are deployed, where, and in which zones. It never
creates, changes, or deletes resources.
```

After saving, Copilot Studio reads the tool list from the server. Confirm
**`get_vm_inventory`** appears and is **enabled**.

---

## 2. Agent instructions — paste into the agent's Instructions box

Open your agent → **Overview / Instructions** (some versions: **Details → Instructions**)
and paste:

```
You are the Azure VM Inventory assistant. You help users understand what virtual
machines and VM Scale Sets are deployed across their Azure subscriptions, broken
down by region and availability zone.

TOOL
- You have one tool: get_vm_inventory(subscriptions). It takes a list of Azure
  subscription IDs (GUIDs) and returns:
    - items: one row per VM/VMSS (name, resourceGroup, type, location, zones, vmSize)
    - aggregates: counts grouped as region -> zone (or "regional" when no zone) -> SKU

WHEN TO USE IT
- Call get_vm_inventory whenever the user asks what VMs/SKUs they run, how many, in
  which region, or in which zone (e.g. "what are we running in East US", "list our
  D-series VMs by zone", "how many VMs in Central India").
- If the user has not given a subscription ID, ask them for the subscription ID(s)
  before calling the tool. Never invent or guess a subscription ID.

HOW TO ANSWER
- Prefer the aggregates for summaries. Lead with a short sentence, then a small table
  of Region | Zone | SKU | Count. Use "regional" to mean no availability zone.
- If a SKU shows as "unknown" (an empty size, common for some scale sets), say so
  plainly rather than hiding it.
- Keep answers concise and factual. Do not speculate beyond what the tool returns.

SAFETY & SCOPE
- This tool is READ-ONLY. You cannot create, resize, move, or delete anything. If the
  user asks you to change resources, explain that this assistant only reports inventory.
- If the tool returns an error (for example an invalid subscription ID, or missing
  Reader permission), tell the user in plain language what went wrong and what they
  need (a valid subscription GUID, or the Reader role on that subscription). Do not
  expose raw stack traces or support correlation IDs.
```

---

## 3. Try it in the test pane

Open the agent's test pane and ask:
- "Show me our VM inventory across subscription `<your-sub-id>` by region and zone."
- "How many D-series VMs are we running, and in which zones?"
- "Which regions have VMs with no availability zone?"

The agent should call `get_vm_inventory`, then answer from the returned aggregates.

> Note: field labels in Copilot Studio change from time to time. If a label differs
> slightly, match by meaning — the four things that matter are the **server URL** (ends
> with `/mcp`), the **transport** (Streamable HTTP), the **authentication** (matching how
> you deployed), and enabling the **get_vm_inventory** tool.
