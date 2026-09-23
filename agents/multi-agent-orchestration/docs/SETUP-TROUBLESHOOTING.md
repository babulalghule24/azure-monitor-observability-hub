# Setup & Troubleshooting

**Run this before step 1. It will save you twenty minutes.**

```bash
python src/_doctor.py      # what SDK do I have?
python src/_preflight.py   # can I actually reach my Foundry project?
```

If `_preflight.py` ends with **ALL CHECKS PASSED**, every step in this lab will run.
If it fails, find your error below — these are the four real failures, in the order
people hit them.

---

## Quick reference: the four traps

| Symptom | Cause | Fix |
|---|---|---|
| `ImportError: cannot import name 'AzureAIAgentClient'` | Foundry rebrand renamed the client | `pip install agent-framework-foundry` |
| `400 - Token tenant <guid> does not match resource tenant` | Signed in to the wrong Entra directory | `az login --tenant <owning-tenant>` + set `AZURE_TENANT_ID` |
| `403 PermissionDenied` | Missing data-plane role, or a **stale token** | Assign `Cognitive Services User` + `Cognitive Services OpenAI User`, then **re-login for a fresh token** |
| `404 - Workspace not found` | Wrong project name, or a knock-on of the tenant issue | Copy the endpoint verbatim from the portal |
| `AgentCard has no "url" field` | a2a-sdk 1.0 installed; lab targets 0.3 | `pip install "a2a-sdk<1.0"` |

---

## 1. ImportError: cannot import name 'AzureAIAgentClient'

```
ImportError: cannot import name 'AzureAIAgentClient' from 'agent_framework.azure'
```

The Microsoft Foundry rebrand moved the client:

| Old | Current |
|---|---|
| `from agent_framework.azure import AzureAIAgentClient` | `from agent_framework.foundry import FoundryChatClient` |
| `client.create_agent(...)` | `client.as_agent(...)` |
| `async_credential=` | `credential=` |
| `model_deployment_name=` | `model=` |

`src/common.py` detects which generation you have and adapts, so you do not need to
change lab code. You just need the provider package:

```bash
pip install agent-framework-foundry
python src/_doctor.py        # confirm FoundryChatClient shows "yes"
```

---

## 2. Token tenant does not match resource tenant

```
400 - Token tenant 18b34117-... does not match resource tenant.
```

**The most common failure on a corporate or AVD machine.** You are signed in to more
than one Entra directory, and `DefaultAzureCredential` handed back a token from the
wrong one. It authenticates fine — it just authenticates to the wrong place.

Find the tenant that owns your Foundry resource:

```bash
az account list --query "[?id=='<YOUR-SUB-ID>'].{sub:name, tenant:tenantId}" -o table
```

Sign in against it, and pin it:

```bash
az login --tenant <TENANT_ID>
az account set --subscription <SUB_ID>
```

`.env`:

```
AZURE_TENANT_ID=<TENANT_ID>
LAB_USE_CLI_CREDENTIAL=1
```

`common.py` uses `AZURE_TENANT_ID` to pin the credential and to exclude the managed
identity and shared-token-cache sources, which are usually the ones returning the
foreign token.

---

## 3. 403 PermissionDenied

Subscription **Owner is not enough**. Azure AI has a separate data plane that needs its
own role assignment.

### The two roles that work

```bash
upn=$(az ad signed-in-user show --query userPrincipalName -o tsv)
acct="/subscriptions/<SUB>/resourceGroups/<RG>/providers/Microsoft.CognitiveServices/accounts/<ACCOUNT>"

az role assignment create --assignee $upn --role "Cognitive Services User" --scope $acct
az role assignment create --assignee $upn --role "Cognitive Services OpenAI User" --scope $acct
```

These two are sufficient. You may also see **Azure AI User** referenced in Microsoft
docs — it is a newer role that **does not exist in every tenant**, and
`az role assignment create` will fail with *"role not found"*. That is fine. Do not
chase it; the two Cognitive Services roles above cover what this lab needs.

To see which AI roles your tenant actually has:

```bash
az role definition list --query "[?contains(roleName, 'Azure AI')].roleName" -o tsv
```

Check what you currently hold:

```bash
az role assignment list --assignee $upn --all \
  --query "[].{role:roleDefinitionName, scope:scope}" -o table
```

### Then refresh your token — this is the real fix, and the step everybody misses

**A token minted before the role assignment still carries the old permissions.** Retrying
immediately returns the same 403, and you conclude the role did not work. It did — your
token is just stale. This is the single most common reason people give up at this point.

```bash
az account clear
az login --tenant <TENANT_ID>
az account set --subscription <SUB_ID>
python src/_preflight.py
```

Role assignments can also take a few minutes to propagate. If it still fails after a
fresh login, wait five minutes and retry **before** changing anything else.

## 4. 404 Workspace not found

```
404 - {'code': 'UserError', 'message': 'Workspace not found.'}
```

Either the project name in your endpoint is wrong, or this is a knock-on of the tenant
problem in §2 — **fix the tenant first and retry before chasing this one.**

Do not hand-build the endpoint. Copy it verbatim:
Foundry portal → your project → **Overview** → **Azure AI Foundry project endpoint**.

Expected shape:

```
https://<resource>.services.ai.azure.com/api/projects/<project-name>
```

Confirm the project actually exists:

```bash
az rest --method get --url "https://management.azure.com/subscriptions/<SUB>/resourceGroups/<RG>/providers/Microsoft.CognitiveServices/accounts/<ACCOUNT>/projects?api-version=2025-04-01-preview" --query "value[].name" -o tsv
```

If that returns nothing, the resource is a plain Azure OpenAI account rather than a
Foundry project — create a Foundry project in the portal.

---

## 5. Deployment not found

The value in `AZURE_AI_MODEL_DEPLOYMENT_NAME` is the **deployment** name, which is
often not the model name. List what actually exists:

```bash
az cognitiveservices account deployment list \
  --name <ACCOUNT> --resource-group <RG> \
  --query "[].{deployment:name, model:properties.model.name, version:properties.model.version}" -o table
```

---

## 6. ValueError: Protocol message AgentCard has no "url" field

```
ValueError: Protocol message AgentCard has no "url" field.
```

You have **a2a-sdk 1.0**, which migrated its types from Pydantic to Protobuf. This lab's
A2A code targets the 0.3 line.

**Fix — pin to 0.3:**

```bash
pip install "a2a-sdk<1.0"
```

`requirements.txt` already pins this; you only hit it if you upgraded manually or
installed before the pin was added.

### What actually changed in a2a-sdk 1.0

| Area | 0.3 | 1.0 |
|---|---|---|
| Types | Pydantic models | Protobuf messages |
| Agent card | `AgentCard(url=...)` | `url` removed; `icon_url` + `supported_interfaces` |
| Text part | `Part(root=TextPart(text=...))` | `Part(text=...)` |
| Role | `Role.user` | `Role.ROLE_USER` |
| Task state | `TaskState.submitted` | `TaskState.TASK_STATE_SUBMITTED` |
| Server | `A2AStarletteApplication` | Starlette route factory functions |

**The protocol concepts are unchanged.** Agent cards, discovery, the task lifecycle and
opacity across a trust boundary work the same way in both. Only the Python type system
moved. Migration guide:
<https://github.com/a2aproject/a2a-python/blob/main/docs/migrations/v1_0/README.md>

---

## Still stuck? Probe every combination

```bash
python src/_endpoint_test2.py
```

This tries every client class installed against four endpoint forms — the project path,
the services root, the `openai.azure.com` host and the `cognitiveservices.azure.com`
host — and prints the real service message for each. It ends by telling you the exact
`.env` line to use.

---

## Setup checklist

Work down this list; each line is a thing that has actually broken for someone.

- [ ] `pip install -r requirements.txt` completed without errors
- [ ] `python src/_doctor.py` shows `FoundryChatClient` = yes
- [ ] `.env` exists (copied from `.env.example`) and is **not** committed
- [ ] Endpoint copied verbatim from the portal, including `/api/projects/<name>`
- [ ] Deployment name verified against `az cognitiveservices account deployment list`
- [ ] `az login --tenant <owning tenant>` — not just `az login`
- [ ] `AZURE_TENANT_ID` set in `.env`
- [ ] `Cognitive Services User` + `Cognitive Services OpenAI User` assigned on the account
- [ ] Token refreshed **after** the role assignment (`az account clear` then `az login --tenant ...`)
- [ ] `pip show a2a-sdk` reports a 0.3.x version (not 1.x)
- [ ] `python src/_preflight.py` ends with ALL CHECKS PASSED
