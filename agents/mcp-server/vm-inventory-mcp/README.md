# VM Inventory MCP — Starter Kit (Visual Studio Code guide)

A focused Model Context Protocol (MCP) server, extracted from the full **Azure VM
Capacity Planner (VMCP)**. It exposes a single, genuinely useful tool:

> **`get_vm_inventory(subscriptions)`** — region/zone-wise VM & VM Scale Set SKU
> inventory across your subscriptions, using **Azure Resource Graph**.

Ask an AI assistant *"show me our VM inventory by region and zone"* and it calls this
tool for you.

This guide is written for **Visual Studio Code** and assumes you are **starting from a
clean machine** — no Python, no tools installed yet. Just follow it top to bottom.

> **How this server runs:** it uses the MCP SDK's own HTTP server — you start it with
> **`python server.py`** (there is no uvicorn/app.py here). It serves at
> **http://localhost:8000/mcp**.

---

## What's in this folder

| File              | What it does                                                        |
| ----------------- | ------------------------------------------------------------------- |
| `vmcp.py`         | The Azure Resource Graph logic (`inventory_vm_skus`)                |
| `server.py`       | The MCP server + the `get_vm_inventory` tool (the part you build)   |
| `requirements.txt`| Python dependencies (mcp, azure-identity, azure-mgmt-resourcegraph) |
| `Dockerfile`      | Containerizes the app for the cloud (serves on port 8000)           |
| `test_local.py`   | Local test: lists the tool and runs the inventory (with a negative test) |
| `test_cloud.py`   | Same test for the Entra ID–secured cloud server                     |
| `.vscode/mcp.json`| Connects VS Code / GitHub Copilot to the server                     |

---

## 1. Prerequisites — install these first (one-time setup)

You need four things: **VS Code**, **Python**, the **Azure CLI**, and an **Azure
subscription** you can read.

### 1a. Install Visual Studio Code
Download and install from https://code.visualstudio.com/ (Windows, macOS, or Linux).

### 1b. Install Python 3.11 or 3.12  (please avoid 3.13 / 3.14)
Use **Python 3.11 or 3.12** — they are the versions the MCP SDK and the Azure libraries
have ready-to-install wheels for. **Do not use Python 3.13 or 3.14 yet:** they are so new
that `mcp` and its dependencies don't publish compatible builds, and `pip install` will
fail partway — leaving you with the error
`ModuleNotFoundError: No module named 'mcp.server.fastmcp'`.

- **Windows:** `winget install Python.Python.3.12` (or download 3.12 from
  https://www.python.org/downloads/). **On the installer's first screen, tick
  "Add python.exe to PATH."**
- **macOS:** `brew install python@3.12`, or install 3.12 from python.org.
- **Linux:** `sudo apt update && sudo apt install python3.12 python3.12-venv python3-pip`

Verify — open a **new** terminal and run:
```bash
python --version      # macOS/Linux may use: python3 --version
```
You should see `Python 3.11.x` or `3.12.x`. If it shows 3.13/3.14, install 3.12 and build
the environment with it explicitly (step 3).

### 1c. Install the Azure CLI
The server signs in to Azure through the Azure CLI.
- **Windows:** `winget install Microsoft.AzureCLI`
- **macOS:** `brew install azure-cli`
- **Linux:** `curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash`

Verify: `az version`

### 1d. An Azure subscription with Reader access
You need at least the read-only **Reader** role on one subscription. The tool only lists
resources — it never changes anything. Note your **Subscription ID** (Azure Portal →
Subscriptions).

### 1e. Install the VS Code extensions
Open VS Code → **Extensions** (`Ctrl+Shift+X` / `Cmd+Shift+X`) and install:
- **Python** (publisher: Microsoft).
- **GitHub Copilot** and **GitHub Copilot Chat** (optional; needed for Agent-mode testing).

---

## 2. Open the project in VS Code
1. Unzip this starter kit anywhere.
2. **File → Open Folder…** and pick the `$AppName` folder.
3. **Terminal → New Terminal** (`` Ctrl+` ``). Everything below runs in this terminal.

---

## 3. Create the Python environment and install dependencies
From the `$AppName` folder:

```bash
python -m venv .venv
```

> **On Windows, pin the version** so you don't accidentally build the venv from 3.13/3.14:
> `py -3.12 -m venv .venv`  (macOS/Linux: `python3.12 -m venv .venv`).

**Activate** it:
- **Windows (PowerShell):** `.venv\Scripts\Activate.ps1`
- **Windows (Command Prompt):** `.venv\Scripts\activate.bat`
- **macOS/Linux:** `source .venv/bin/activate`

> If PowerShell blocks the activate script, run once:
> `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`, then try again.

When VS Code offers to select the new environment, click **Yes** (or `Ctrl+Shift+P` →
**Python: Select Interpreter** → the one under `.venv`). Confirm the version:
```bash
python --version      # should say 3.11.x or 3.12.x
```

Install the dependencies:
```bash
pip install -r requirements.txt
```

Watch for any red **ERROR** lines. Confirm the key packages imported:
```bash
python -c "import mcp.server.fastmcp; from azure.mgmt.resourcegraph import ResourceGraphClient; print('deps OK')"
```
It should print `deps OK`. If not, see **Troubleshooting** below.

---

## 4. Sign in to Azure
The server signs in with whatever identity is available where it runs: **locally** it uses
your Azure CLI login, and **in Azure Container Apps** it uses the app's **managed identity**
(see section 8) — no code change either way. For local testing, just log in:
```bash
az login
```
## 5. Variables
```
$SubscrptionID= "00000000-0000-0000-0000-000000000000"
$AppName = "vm-inventory-mcp"
$RESOURCE_GROUP = "rg-vm-inventory"
$LOCATION="centralindia"
$ENVIRONMENT="vm-inventory-env"
$ACR = "vminventoryacr"
```
Sign in with the account that has **Reader** on your subscription.

---

## 6. Run the server
```bash
python server.py
```
Leave this running. Your MCP server is now live at **http://localhost:8000/mcp**.

---

## 7. Test it — two ways, both inside VS Code

### Option A — Run the test script (quickest)
Open a **second** terminal in VS Code (the first is busy running the server). With the
`.venv` active, set your subscription and run the test:

- **macOS/Linux:**
  ```bash
  export AZURE_SUBSCRIPTION_IDS="$SubscrptionID"
  python test_local.py
  ```
- **Windows (PowerShell):**
  ```powershell
  $env:AZURE_SUBSCRIPTION_IDS="$SubscrptionID"
  python test_local.py
  ```

  (Use your own subscription GUID in place of the example above.)

Replace the zeros with your real Subscription ID. You should see `get_vm_inventory`
listed, then a region/zone SKU summary, then a negative test (a bogus subscription that
fails cleanly). Leave `AZURE_SUBSCRIPTION_IDS` unset to run in **list-only** mode (proves
the server works without calling Azure).

> You can also point the test at another URL: `python test_local.py http://localhost:8000/mcp`

### Option B — Ask GitHub Copilot in Agent mode
1. Open **Copilot Chat** and switch the mode selector to **Agent**.
2. This folder ships `.vscode/mcp.json`, so VS Code sees the server. Open it and click the
   **Start** button above the server entry (or `Ctrl+Shift+P` → **MCP: List Servers** →
   start `$AppName`).
3. Click **Tools** in Copilot Chat and confirm `get_vm_inventory` is listed.
4. Type *"Show me our VM inventory by region and zone"* and approve the tool call.

---

## 8. (Optional) Browse the tool visually with the MCP Inspector
With Node.js installed, in a VS Code terminal:
```bash
npx @modelcontextprotocol/inspector
```
Choose **HTTP**, enter `http://localhost:8000/mcp`, and click **Connect**.

---

## 9. Deploy to Azure Container Apps (optional)

> **This deployment's values** (used in the examples below — replace with your own):
>
> | Setting | Value |
> | --- | --- |
> | App name | `$AppName` |
> | Resource group | `$RESOURCE_GROUP` |
> | Region | `$LOCATION` |
> | MCP endpoint | `https://$APP_URL/mcp` |
> | Subscription to inventory | `$SubscrptionID` |
>
> **Already deployed?** Find your app's real name and resource group with
> `az containerapp list -o table`, then skip straight to *"Give the app a read-only
> managed identity"* below — the identity `-g` MUST match the group your app is in.

Build in the cloud (no local Docker needed) and deploy. Run from inside this folder:

```bash
az login
az account set --subscription "$SubscrptionID"
az group create -n $RESOURCE_GROUP -l $LOCATION
az acr create -g $RESOURCE_GROUP -n $ACR --sku Basic

# build the image from THIS folder
az acr build -r $ACR -t vm-inventory:v1 .

# deploy to Azure Container Apps (serves on port 8000)
az containerapp up -n $AppName -g $RESOURCE_GROUP \
  --environment $ENVIRONMENT \
  --image $ACR.azurecr.io/vm-inventory:v1 \
  --registry-server $ACR.azurecr.io \
  --ingress external --target-port 8000
# prints a URL; your MCP endpoint is that URL + /mcp

# keep one instance warm to avoid cold starts
az containerapp update -n $AppName -g $RESOURCE_GROUP --min-replicas 1
```

### Ship a code change later (update the running app)
A running Container App keeps serving its **old** image until you tell it to update — so any
edit to `server.py` / `vmcp.py` goes live only after you rebuild and re-point the app. Run
these from inside the project folder, bumping the tag each time (`v2`, `v3`, …) so you can
tell builds apart and roll back:

```powershell
# 1) build a NEW image tag in your registry from the current code
az acr build -r $ACR -t vm-inventory:v2 .

# 2) point the container app at the new image (creates a new revision, shifts traffic to it)
az containerapp update -n $AppName -g $RESOURCE_GROUP `
  --image $ACR.azurecr.io/vm-inventory:v2
```

> **If step 2 fails with "can't pull image" / unauthorized**, let the app's managed identity
> pull from the registry (keyless), then retry:
> ```powershell
> $PRINCIPAL = az containerapp identity show -n $AppName -g $RESOURCE_GROUP --query principalId -o tsv
> $ACR_ID    = az acr show -n $ACR --query id -o tsv
> az role assignment create --assignee $PRINCIPAL --role AcrPull --scope $ACR_ID
> az containerapp registry set -n $AppName -g $RESOURCE_GROUP `
>   --server $ACR.azurecr.io --identity system
> ```

> **Changed an environment variable instead of code?** Env vars aren't baked into the image —
> set them directly (this also makes a new revision), e.g.
> `az containerapp update -n $AppName -g $RESOURCE_GROUP --set-env-vars AZURE_CLIENT_ID=<client-id>`.

**Verify the update, and roll back if needed:**
```powershell
$FQDN = az containerapp show -n $AppName -g $RESOURCE_GROUP --query "properties.configuration.ingress.fqdn" -o tsv
curl https://$FQDN/health          # {"status":"healthy"}

# list revisions (newest first); reactivate an older one if a build misbehaves
az containerapp revision list -n $AppName -g $RESOURCE_GROUP -o table
az containerapp revision activate -n $AppName -g $RESOURCE_GROUP --revision <old-revision-name>
```

### Give the app a read-only managed identity
In the cloud the server signs in with a **managed identity** — an identity Azure manages
for the app, with **no secrets or keys in your code**. `server.py` detects it
automatically (via the `IDENTITY_ENDPOINT` env var) and uses `ManagedIdentityCredential`;
locally, with no managed identity, it falls back to your `az login`.

**Use a system-assigned identity — this is the recommended path for almost everyone.** It's
a single identity tied to this app, with nothing extra to configure in code. These three
commands are all you need:

```powershell
# PowerShell (Windows)
az containerapp identity assign -n $AppName -g $RESOURCE_GROUP --system-assigned
$PRINCIPAL = az containerapp identity show -n $AppName -g $RESOURCE_GROUP --query principalId -o tsv

# grant it read-only Reader on each subscription you want it to inventory
az role assignment create --assignee $PRINCIPAL --role Reader `
  --scope /subscriptions/$SubscrptionID
```

```bash
# macOS/Linux (same commands)
az containerapp identity assign -n $AppName -g $RESOURCE_GROUP --system-assigned
$PRINCIPAL=$(az containerapp identity show -n $AppName -g $RESOURCE_GROUP --query principalId -o tsv)
az role assignment create --assignee $PRINCIPAL --role Reader \
  --scope /subscriptions/$SubscrptionID
```

That's it — no code change, no `AZURE_CLIENT_ID`, no extra resource. Skip the advanced
option below unless you specifically need it.

---

<details>
<summary><b>Advanced (optional): user-assigned identity</b> — only if you want to reuse ONE
identity across multiple apps. Most people should NOT do this.</summary>

A user-assigned identity is a standalone resource you attach to the app, then point the code
at with the `AZURE_CLIENT_ID` env var. Note the **`-l` (location) flag** on
`az identity create` — leaving it out gives `Missing required field: --location`.

```bash
# create (or reuse) a user-assigned identity and read its ids  (-l is REQUIRED)
az identity create -g $RESOURCE_GROUP -n id-vm-inventory -l $LOCATION
$CLIENT_ID=$(az identity show -g $RESOURCE_GROUP -n id-vm-inventory --query clientId -o tsv)
$PRINCIPAL=$(az identity show -g $RESOURCE_GROUP -n id-vm-inventory --query principalId -o tsv)
$RES_ID=$(az identity show -g $RESOURCE_GROUP -n id-vm-inventory --query id -o tsv)

# attach it to the container app and expose its client id to the code
az containerapp identity assign -n $AppName -g $RESOURCE_GROUP --user-assigned $RES_ID
az containerapp update -n $AppName -g $RESOURCE_GROUP \
  --set-env-vars AZURE_CLIENT_ID=$CLIENT_ID

# grant it read-only Reader on each target subscription
az role assignment create --assignee $PRINCIPAL --role Reader \
  --scope /subscriptions/$SubscrptionID
```

</details>

> Either way, the credential is picked automatically at runtime — you never put a key in
> the image. Role assignments can take a minute to propagate; if the first call says
> "authorization failed", wait ~60s and retry.

### Verify the deployed server
```bash
# health check (no auth needed)
$APP_URL=$(az containerapp show --name $APP_NAME --resource-group $RESOURCE_GROUP --query "properties.configuration.ingress.fqdn" -o tsv)
curl https://$APP_URL/health
# expect: {"status":"healthy"}
```
Then run the full end-to-end cloud test (section 9).

---

## 10. Run the cloud test (and optionally secure it with Microsoft Entra ID)
Point `test_cloud.py` at your deployed URL. It always reads an `MCP_TOKEN` env var; if you
have NOT enabled Entra auth, any placeholder works (the server ignores it). If you HAVE
enabled built-in auth, use a real token for your app's API scope.

- **Windows (PowerShell):**
  ```powershell
  # auth OFF (unsecured test app): a placeholder is fine
  $env:MCP_TOKEN = "none"
  # auth ON (Entra): get a real token instead —
  # $env:MCP_TOKEN = az account get-access-token --resource api://<YOUR_APP_ID> --query accessToken -o tsv
  $env:AZURE_SUBSCRIPTION_IDS = "$SubscrptionID"
  python test_cloud.py https://$APP_URL/mcp
  ```
- **macOS/Linux:**
  ```bash
  export MCP_TOKEN="none"   # or a real token if Entra auth is enabled:
  # export MCP_TOKEN=$(az account get-access-token --resource api://<YOUR_APP_ID> --query accessToken -o tsv)
  export AZURE_SUBSCRIPTION_IDS="$SubscrptionID"
  python test_cloud.py https://$APP_URL/mcp
  ```

Seeing the tool listed **and** a JSON inventory block means the deployed server works
end-to-end. With Entra auth on, a valid token returns inventory while a missing/expired
one returns **401 Unauthorized** — proof that your protection is working.
`<YOUR_APP_ID>` is your Entra **app registration** Application (client) ID.

---

## Connect it to Copilot Studio
Copilot Studio → your agent → **Tools → Add a tool → Model Context Protocol** → paste
`https://$APP_URL/mcp` →
enable `get_vm_inventory`. Then ask
"Show me VM inventory across these subscriptions by region and zone."
See **Copilot-Studio-Agent-Instructions.md** for the full dialog values and agent prompt.

---

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `ModuleNotFoundError: No module named 'mcp.server.fastmcp'` (locally) | Two possible causes: (a) you're on Python 3.13/3.14 (`python --version`) — recreate the venv on 3.12; or (b) pip installed **mcp 2.x** (`pip show mcp`), which removed that import path. This code targets mcp 1.x, so `requirements.txt` pins `mcp[cli]>=1.2.0,<2.0.0`. Fix now with `pip install "mcp[cli]>=1.2.0,<2.0.0"` then verify `python -c "import mcp.server.fastmcp; print('OK')"`. |
| Same error **in the container** (health check times out; logs show the traceback on startup) | The image installed the wrong `mcp` (usually 2.x). The pinned `requirements.txt` (`mcp[cli]>=1.2.0,<2.0.0`) prevents this — rebuild with a **new tag** so no stale layer is reused: `az acr build -r $ACR -t vm-inventory:v2 .` then `az containerapp update -n $AppName -g $RESOURCE_GROUP --image $ACR.azurecr.io/vm-inventory:v2`. Check startup logs with `az containerapp logs show -n $AppName -g $RESOURCE_GROUP --tail 50`. |
| `Could not import azure-mgmt-resourcegraph` / `azure-mgmt-resourcegraph is not installed` | The library isn't in the server's venv, or you installed it while the server was already running. Run `pip install azure-mgmt-resourcegraph`, then **stop (`Ctrl+C`) and restart** `python server.py`. Verify: `python -c "from azure.mgmt.resourcegraph import ResourceGraphClient; print('arg OK')"`. |
| `python` or `pip` "not found" | Reopen the terminal (or VS Code) so PATH reloads. On macOS/Linux try `python3`. |
| PowerShell won't run `Activate.ps1` | `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`, then activate again. |
| VS Code runs the wrong Python | `Ctrl+Shift+P` → **Python: Select Interpreter** → pick the `.venv` one. |
| Inventory is empty or errors | Confirm `az login` succeeded (local) or the managed identity has **Reader** (cloud) on that Subscription ID. |
| Cloud app: `DefaultAzureCredential`/`ManagedIdentityCredential` auth fails or "no managed identity" | System-assigned: make sure `az containerapp identity assign --system-assigned` ran. User-assigned: also set `AZURE_CLIENT_ID` to the identity's **client id** (`--set-env-vars AZURE_CLIENT_ID=...`). Then confirm the **Reader** role assignment exists and has had ~60s to propagate. |
| `az identity create` → `Missing required field: --location` | Add `-l <region>`, e.g. `az identity create -g $RESOURCE_GROUP -n id-vm-inventory -l $LOCATION`. (You only need this for the advanced user-assigned path — system-assigned needs no `az identity create` at all.) |
| `test_local.py` can't connect | Make sure `python server.py` is running in the other terminal and the URL ends with `/mcp` (default `http://localhost:8000/mcp`). |
| Port 8000 already in use | Start on another port: `PORT=8090 python server.py` (Windows PS: `$env:PORT="8090"; python server.py`) and update the URL in `.vscode/mcp.json`. |

### Fix: recreate the environment on Python 3.12
```powershell
# Windows (PowerShell) — run from the project folder
deactivate                        # if the venv is active
Remove-Item -Recurse -Force .venv
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python --version                  # confirm 3.12.x
pip install -r requirements.txt
python -c "import mcp.server.fastmcp; from azure.mgmt.resourcegraph import ResourceGraphClient; print('deps OK')"
```
```bash
# macOS/Linux
deactivate                        # if the venv is active
rm -rf .venv
python3.12 -m venv .venv
source .venv/bin/activate
python --version                  # confirm 3.12.x
pip install -r requirements.txt
python -c "import mcp.server.fastmcp; from azure.mgmt.resourcegraph import ResourceGraphClient; print('deps OK')"
```

---
Extracted from the Azure VM Capacity Planner (VMCP). Grant the server only **Reader** on
the subscriptions you want it to see — least privilege keeps an AI-facing tool safe.
