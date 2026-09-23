# Hands-On Lab — Build the SfMC Mission-Critical Operations Desk

**A complete, self-contained walkthrough.** Every step below carries its narrative, the
full source code, what to run, what you should see, and questions to check your
understanding. If you only read one file in this repo, read this one.

Platform: **Microsoft Foundry (Azure AI Foundry) + Python + Microsoft Agent Framework + A2A**
Level: **400** · Time: **25 minutes live, ~90 minutes at your own pace**

> **Start in 30 seconds, no Azure account:**
> `pip install -r requirements.txt` then
> `LAB_OFFLINE=1 python src/step1_signal_agent.py`
> (PowerShell: `$env:LAB_OFFLINE=1`)
> Every pattern behaves identically offline. Set up Foundry when you want real model
> reasoning — same code, same files.

---

## Contents

- [Set the stage](#set-the-stage)
- [What you are building](#what-you-are-building)
- [The de-identification rule](#the-de-identification-rule)
- [Step 0 — Setup](#step-0--setup)
- [The shared foundations file](#the-shared-foundations-file)
- [Step 1 — A plain agent on Foundry](#step-1--a-plain-agent-on-foundry)
- [Step 2 — Wrap it into an A2A server](#step-2--wrap-it-into-an-a2a-server)
- [Step 3 — Call it from an A2A client](#step-3--call-it-from-an-a2a-client)
- [Step 4 — A second A2A server](#step-4--a-second-a2a-server)
- [Step 5 — Sequential: Reporter then Redactor](#step-5--sequential-reporter-then-redactor)
- [Step 6 — Concurrent: three specialists at once](#step-6--concurrent-three-specialists-at-once)
- [Step 7 — The CoE Baseline Advisor](#step-7--the-coe-baseline-advisor)
- [Step 8 — Handoff: dynamic routing](#step-8--handoff-dynamic-routing)
- [Step 9 — Group Chat: refine until APPROVED](#step-9--group-chat-refine-until-approved)
- [Step 10 — Assemble the full desk](#step-10--assemble-the-full-desk)
- [Step 11 — Harden it](#step-11--harden-it)
- [The decision framework](#the-decision-framework)

---

## Set the stage

You are the Cloud Solution Architect on a **Support for Mission Critical (SfMC)**
engagement. It is Monday. The weekly **Open Case / Incident Review** is on Thursday, and
you have to walk in with a defensible picture of the week for `CUSTOMER-A`:

> Since Tuesday the public endpoint has returned intermittent 5xx errors and backend
> latency is up. There was no deployment. Log ingestion cost has risen. What happened,
> what do we think the cause is, and what are we asking the customer to do?

That answer lives in four systems that do not talk to each other:

| Source | What it knows |
|---|---|
| Azure Monitor / Log Analytics | Which alert rules fired, when, how often |
| Support cases | What is open, at what severity, for how long |
| Consolidated Assessment backlog | Which architectural risks were already known |
| Reporting template | How to say it so a customer can act on it |

One engineer opens four tools and stitches this together by hand. It takes hours, it
varies by engineer, and risks surface late — which in mission critical is the expensive
kind of late.

**Is this actually a multi-agent problem?** Apply the three tests. It only qualifies if it
passes at least one, and this passes all three:

1. **Separation of expertise** — alert analysis, case management and architecture risk are
   genuinely different skills working on different data.
2. **Separation of trust** — the monitoring baseline is owned by a different team (the
   Monitoring & Observability CoE) in a different Foundry project.
3. **Parallelism** — those three reads do not depend on each other.

If your problem fails all three, you wanted a better single agent, not a second agent.

---

## What you are building

```
   ORCHESTRATOR — Foundry project A  (Microsoft Agent Framework)
     Intake agent ──dynamic hand-off of tasks──▶  3 × A2A Client
     in-process:  Reporter ⇄ Redactor   (Group Chat until APPROVED, no HTTP hop)
                    │              │              │
              ┌─────┴────┐   ┌─────┴────┐   ┌─────┴──────────────────┐
              │A2A SERVER│   │A2A SERVER│   │A2A SERVER              │
              │ Signal   │   │CaseReview│   │ CoE Baseline Advisor   │
              │  ↓ MCP   │   │  ↓ MCP   │   │ Foundry project B      │
              │ Azure    │   │ Support  │   │ DIFFERENT TEAM         │
              │ Monitor  │   │ cases    │   │                        │
              └──────────┘   └──────────┘   └────────────────────────┘
                 step 2         step 4              step 7

              MCP = agent → tools.    A2A = agent → agent.    Both, in one system.
```

**The most important sentence in this lab: the architecture is not the code. The
architecture is the decision about which agents got A2A and which stayed in-process.**
Reporter and Redactor share a process because they do not need a network between them.
The CoE advisor is remote because it belongs to someone else. Those two decisions are the
design — everything else is syntax.

### The build path

| # | Step | What it adds | Time |
|---|---|---|---|
| 1 | Plain Signal agent on Foundry | One specialist, no protocol | 3 min |
| 2 | Wrap it into an A2A server | An agent card — it becomes callable | 3 min |
| 3 | Call it from an A2A client | Discover → delegate → observe | 3 min |
| 4 | Second A2A server: CaseReview | A multi-agent system | 2 min |
| 5 | Sequential: Reporter → Redactor | First pattern + the confidentiality gate | 3 min |
| 6 | Concurrent: three at once | Fan-out / fan-in | 3 min |
| 7 | CoE Baseline Advisor | Another team, another project | 3 min |
| 8 | Handoff orchestrator | Dynamic routing + human escalation | 3 min |
| 9 | Group Chat | Refinement + iteration cap | 3 min |
| 10 | Assemble the full desk | The whole diagram, running | 3 min |
| 11 | Harden it | Identity, egress, budgets, tracing | homework |

Steps **1–3 are the A2A core**. Steps **5, 6, 8, 9** are the orchestration patterns.
Step **11** is the difference between a demo and an engagement.

---

## The de-identification rule

Everything in SfMC is Microsoft Confidential and customer-identifying. So this lab uses
**synthetic data only**: the customer is always `CUSTOMER-A`, subscription GUIDs are
fabricated, case IDs invented, and there are no names, email addresses or IP addresses
anywhere.

That is a design lesson, not repo hygiene:

- The **Redactor is a first-class agent with a veto**, not a filter bolted on at the end.
- It runs on the **outbound** path — before anything crosses a boundary, not after.
- Secure by design, secure by default, secure operations.

**Never commit real alert exports, case exports, assessment outputs or `.env` files.**

---

## Step 0 — Setup

### The fast path: no Azure account needed

```bash
pip install -r requirements.txt

LAB_OFFLINE=1 python src/step1_signal_agent.py     # PowerShell: $env:LAB_OFFLINE=1
```

That is the whole setup. Offline mode answers every agent from a script instead of a
model — no credentials, no network, no waiting. **Every pattern behaves identically**:
who speaks, in what order, who decides, and where the boundaries are. That is what this
lab teaches, and it does not need a live model.

Work through all eleven steps this way if you like. Then, when you want to see real
model reasoning, set up a Foundry project and unset the variable — same code, same
files.

### The live path: your own Microsoft Foundry project

```bash
git clone https://github.com/babulalghule24/azure-monitor-observability-hub.git
cd azure-monitor-observability-hub/agents/multi-agent-orchestration

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env               # Windows: copy .env.example .env
```

Fill in `.env`:

```
AZURE_AI_PROJECT_ENDPOINT=https://<your-foundry-resource>.services.ai.azure.com/api/projects/<your-project>
AZURE_AI_MODEL_DEPLOYMENT_NAME=gpt-4o-mini

A2A_HOST=127.0.0.1
PORT_SIGNAL=9001
PORT_CASES=9002
PORT_COE=9003
```

Sign in — there are no keys in this repo, authentication is Entra ID:

```bash
az login
```

Verify:

```bash
python -c "import agent_framework, agent_framework_orchestrations; print('ready')"
```

> **If an import or builder name has drifted:** the framework ships fast. Match your
> installed version against the official Python samples at
> <https://github.com/microsoft/agent-framework/tree/main/python/samples/03-workflows/orchestrations>
> and adjust one line. Reading the samples rather than blog posts is a Level 400 habit.

### The synthetic data

Three fixtures under `data/`. Skim them now so the agent output means something to you:

- `alerts.json` — a week of Azure Monitor activity, including one rule firing 228 times on
  a static threshold (noise) and a Sev1 rule firing three times inside an incident window
  (signal), plus three monitoring coverage gaps.
- `cases.json` — four open support cases, one Sev A with the product group, one stalled at
  31 days.
- `risks.json` — four unmitigated Consolidated Assessment findings, two of which already
  predicted this week's symptoms.

---

## The shared foundations file

Read this once. Every step file afterwards is short because the plumbing — the Foundry
client, the data tools, the agent instructions and two small A2A helpers — lives here.

Four things to notice as you read:

1. **`get_client()`** — every agent in this repo runs in a Microsoft Foundry project, and
   authenticates with `DefaultAzureCredential`. There is no API key anywhere in this repo.
2. **The tools** read synthetic fixtures. In production these would be MCP servers over
   Azure Monitor / Log Analytics, Azure DevOps and SharePoint — the shape of the lesson is
   identical either way.
3. **The instruction blocks** are the actual design work. Read `REDACTOR` closely: it is
   the confidentiality control expressed as an agent, and it is told to reply with exactly
   `APPROVED` so a selection function can terminate on it.
4. **`serve()` and `ask_a2a()`** are thin wrappers so the step files stay about the
   protocol rather than about plumbing.

<details>
<summary><b>src/common.py</b> (click to expand)</summary>

```python
"""SfMC Mission-Critical Operations Desk - shared foundations.

Platform: Microsoft Foundry (Azure AI Foundry) + Python + Microsoft Agent Framework.

Read this file once, at the start. Every numbered step file afterwards is short, because
the boring parts - the Foundry client, the data tools, the agent instructions, and two
small A2A helpers - all live here.

DE-IDENTIFICATION RULE
Everything is synthetic. The customer is always "CUSTOMER-A", subscription GUIDs are
fabricated, case IDs are invented, and there are no names, emails or IP addresses
anywhere. That is a design rule of this architecture, not repo hygiene - see the Redactor.

VERSION COMPATIBILITY
The Agent Framework renamed its Azure client during the Microsoft Foundry rebrand:

    OLD:  from agent_framework.azure   import AzureAIAgentClient   (create_agent, async_credential=)
    NEW:  from agent_framework.foundry import FoundryChatClient    (as_agent,     credential=)

This file detects which one you have and adapts. If something still fails, run:

    python src/_doctor.py

which prints exactly what your installed version exposes.
"""

import json
import os
from pathlib import Path
from typing import Annotated

from dotenv import load_dotenv
from pydantic import Field

load_dotenv()

DATA = Path(__file__).resolve().parent.parent / "data"


# =====================================================================================
# 1. The Foundry client - where every agent in this repo actually runs
# =====================================================================================

# The async credential lives in azure.identity.aio, not azure.identity.
try:
    from azure.identity.aio import AzureCliCredential, DefaultAzureCredential
except ImportError:                                            # very old azure-identity
    from azure.identity import AzureCliCredential, DefaultAzureCredential  # type: ignore

_FLAVOUR = None       # "foundry" | "azure-ai" | "azure-openai"

try:
    # Current SDK (post-Foundry-rebrand). This is what you should be on.
    from agent_framework.foundry import FoundryChatClient as _ChatClient
    _FLAVOUR = "foundry"
except ImportError:
    try:
        # Older SDK, pre-rebrand.
        from agent_framework.azure import AzureAIAgentClient as _ChatClient  # type: ignore
        _FLAVOUR = "azure-ai"
    except ImportError:
        try:
            from agent_framework.azure import AzureAIClient as _ChatClient   # type: ignore
            _FLAVOUR = "azure-ai"
        except ImportError as exc:
            if os.environ.get("LAB_OFFLINE") == "1":
                _ChatClient, _FLAVOUR = None, "offline"
            else:
                    raise ImportError(
                    "No Microsoft Foundry chat client found.\n"
                    "Install the Foundry provider:\n"
                    "    pip install agent-framework agent-framework-foundry agent-framework-orchestrations\n"
                    "Then run:  python src/_doctor.py\n"
                    f"Original error: {exc}"
                ) from exc


def get_credential():
    """Entra ID. No keys, ever.

    TENANT TRAP (this bites on corporate / AVD machines):
    DefaultAzureCredential tries several sources in order - environment, managed
    identity, shared token cache, Azure CLI, VS Code. On a machine signed in to more
    than one directory it often returns a token from the WRONG tenant, and the service
    replies:

        400 - Token tenant <guid> does not match resource tenant.

    Fix: set AZURE_TENANT_ID in .env to the tenant that OWNS the Foundry resource.
    Find it with:
        az account list --query "[?id=='<your-sub-id>'].{sub:name, tenant:tenantId}" -o table
    Then:
        az login --tenant <that-tenant-id>

    With AZURE_TENANT_ID set we pin the credential to that tenant and skip the
    credential sources most likely to hand back a foreign token.
    """
    tenant = os.environ.get("AZURE_TENANT_ID", "").strip() or None

    # Explicit opt-in to the CLI credential - simplest and most predictable.
    if os.environ.get("LAB_USE_CLI_CREDENTIAL") == "1":
        return AzureCliCredential(tenant_id=tenant) if tenant else AzureCliCredential()

    if tenant:
        # Pin the tenant and exclude the sources that commonly cache another
        # directory's token on corporate desktops.
        try:
            return DefaultAzureCredential(
                tenant_id=tenant,
                exclude_managed_identity_credential=True,
                exclude_shared_token_cache_credential=True,
            )
        except TypeError:
            return DefaultAzureCredential(tenant_id=tenant)

    return DefaultAzureCredential()


def get_client():
    """Build the Foundry client, whichever SDK generation is installed.

    OFFLINE MODE: set LAB_OFFLINE=1 and this returns a scripted stand-in instead.
    No Azure, no credentials, no network. Every step file still runs, and the
    orchestration - who speaks, in what order, who decides - is identical.
    Use it to learn the patterns in 30 seconds, then unset it for the real thing.
    """
    if os.environ.get("LAB_OFFLINE") == "1":
        from offline import OfflineClient
        print("  [OFFLINE MODE] scripted answers, no Azure calls. "
              "Unset LAB_OFFLINE to use your Foundry project.\n")
        return OfflineClient()

    endpoint = os.environ.get("AZURE_AI_PROJECT_ENDPOINT")
    if not endpoint:
        raise RuntimeError(
            "AZURE_AI_PROJECT_ENDPOINT is not set.\n"
            "  Either copy .env.example to .env and fill it in,\n"
            "  or run with no setup at all:   LAB_OFFLINE=1 python src/step1_signal_agent.py\n"
            "  (PowerShell:  $env:LAB_OFFLINE=1)"
        )
    model = os.environ.get("AZURE_AI_MODEL_DEPLOYMENT_NAME", "gpt-4o-mini")
    cred = get_credential()

    if _FLAVOUR == "foundry":
        return _ChatClient(project_endpoint=endpoint, model=model, credential=cred)

    try:
        return _ChatClient(project_endpoint=endpoint, model_deployment_name=model,
                           async_credential=cred)
    except TypeError:
        return _ChatClient(project_endpoint=endpoint, model_deployment_name=model,
                           credential=cred)


def make(client, name: str, instructions: str, tools=None):
    """Create one agent. `as_agent` on the current SDK, `create_agent` on older ones."""
    kwargs = {"name": name, "instructions": instructions}
    if tools:
        kwargs["tools"] = tools

    factory = getattr(client, "as_agent", None) or getattr(client, "create_agent", None)
    if factory is None:
        raise AttributeError(
            f"{type(client).__name__} has neither as_agent() nor create_agent(). "
            "Run: python src/_doctor.py"
        )
    return factory(**kwargs)


def sdk_flavour() -> str:
    """Which SDK generation we detected - handy when a step file misbehaves."""
    if os.environ.get("LAB_OFFLINE") == "1":
        return "OFFLINE (scripted answers, no Azure)"
    tenant = os.environ.get("AZURE_TENANT_ID", "").strip()
    suffix = f", tenant={tenant}" if tenant else ", tenant=(not pinned)"
    return f"{_FLAVOUR} ({_ChatClient.__module__}.{_ChatClient.__name__}{suffix})"


# =====================================================================================
# 2. Tools - the desk's data sources
# In production these are MCP servers over Azure Monitor / Log Analytics, Azure DevOps
# and SharePoint. Here they read synthetic fixtures, so the shape of the lesson is
# identical and nothing real leaves your machine.
# =====================================================================================

def _load(name: str) -> dict:
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def get_monitor_signals(
    week: Annotated[str, Field(description="Review week, e.g. FY27-W12")] = "FY27-W12",
) -> str:
    """Azure Monitor alert activity and monitoring coverage gaps for the review week."""
    return json.dumps(_load("alerts.json"))


def get_open_cases(
    week: Annotated[str, Field(description="Review week, e.g. FY27-W12")] = "FY27-W12",
) -> str:
    """Open Microsoft support cases with severity, age and state for the review week."""
    return json.dumps(_load("cases.json"))


def get_assessment_risks(
    pillar: Annotated[str, Field(description="Optional WAF pillar filter")] = "",
) -> str:
    """Unmitigated risk items from the Consolidated Assessment backlog."""
    risks = _load("risks.json")
    if pillar:
        risks["open_risks"] = [r for r in risks["open_risks"] if r["pillar"].lower() == pillar.lower()]
    return json.dumps(risks)


# =====================================================================================
# 3. The cast - one instruction block per agent, all in one place
# =====================================================================================

INTAKE = (
    "You are the Intake agent for the SfMC Mission-Critical Operations Desk. "
    "You prepare the weekly Open Case / Incident Review for CUSTOMER-A. "
    "Read the situation, decide which single specialist should own it next, and route to "
    "them. Never analyse the problem yourself. If the situation needs a human decision - "
    "a severity call, a customer commitment, or anything contractual - route to the TCL "
    "escalation queue instead of guessing."
)

SIGNAL = (
    "You are the Monitoring Signal agent. Use get_monitor_signals. Separate REAL signal "
    "from alert noise: call out rules that fire constantly on static thresholds, rules "
    "that correlate in time with an incident, and monitoring coverage gaps. Always state "
    "which alert rule each conclusion came from. Never invent a metric value."
)

RESILIENCE = (
    "You are the Resilience agent. Use get_assessment_risks. Report unmitigated "
    "Consolidated Assessment findings, ordered by rating then age, and say explicitly "
    "which of this week's symptoms a known open risk already predicted. Cite the risk ID "
    "for every statement."
)

CASE_REVIEW = (
    "You are the Case Review agent. Use get_open_cases. Summarise open cases by severity "
    "and age, flag anything stalled or awaiting customer data, and link each case to the "
    "alert rule it relates to where one exists. Cite case IDs."
)

REPORTER = (
    "You are the service review writer. Turn the specialists' findings into the weekly "
    "service review summary for the TCL: (1) one-line health statement, (2) what happened "
    "this week, (3) what we believe the cause is, (4) three numbered recommended actions "
    "with an owner, (5) risks needing customer decision. Under 350 words, plain English, "
    "no internal tool names. Never state a number that was not in the findings."
)

REDACTOR = (
    "You are the confidentiality and quality gate for anything leaving this desk. "
    "REJECT the draft if it contains any customer name, person's name, email address, IP "
    "address, real subscription or tenant GUID, case URL, or any personal data - the "
    "customer must appear only as CUSTOMER-A. Also reject if a figure appears that is not "
    "in the findings, or if a recommended action has no owner. If the draft is clean and "
    "accurate, reply with exactly APPROVED and nothing else. Otherwise reply with "
    "numbered corrections only."
)

COE_BASELINE = (
    "You are the SfMC Monitoring & Observability CoE Baseline Advisor. For a given Azure "
    "service, state the recommended alert baseline: which signals must be alerted, which "
    "should use dynamic thresholds rather than static ones, and what availability testing "
    "is expected for a mission-critical workload. Answer only from established monitoring "
    "practice. Never accept or repeat customer-identifying data - if the caller sends any, "
    "answer the general question and say the identifying detail was ignored."
)

TCL_QUEUE = (
    "You are the human TCL escalation queue. Do not diagnose. Summarise the situation in "
    "five lines for a human Technical Customer Lead, state exactly what decision is needed "
    "from them, and stop."
)


def build_desk(client):
    """All in-process agents, for the steps that do not need A2A."""
    return {
        "intake": make(client, "Intake", INTAKE),
        "signal": make(client, "Signal", SIGNAL, [get_monitor_signals]),
        "resilience": make(client, "Resilience", RESILIENCE, [get_assessment_risks]),
        "cases": make(client, "CaseReview", CASE_REVIEW, [get_open_cases]),
        "reporter": make(client, "Reporter", REPORTER),
        "redactor": make(client, "Redactor", REDACTOR),
        "tcl_queue": make(client, "TCL_Escalation", TCL_QUEUE),
    }


# =====================================================================================
# 4. Two small A2A helpers, so the step files stay about the protocol, not plumbing
# =====================================================================================

def agent_card(name: str, description: str, skill_id: str, skill_name: str,
               skill_description: str, base_url: str, examples=None, tags=None):
    """Build the JSON document other agents fetch to decide whether to trust you."""
    from a2a.types import AgentCapabilities, AgentCard, AgentSkill

    return AgentCard(
        name=name,
        description=description,
        url=f"{base_url}/",
        version="1.0.0",
        default_input_modes=["text"],
        default_output_modes=["text"],
        capabilities=AgentCapabilities(streaming=True, push_notifications=False),
        skills=[AgentSkill(
            id=skill_id, name=skill_name, description=skill_description,
            tags=tags or [], examples=examples or [],
        )],
    )


class _FrameworkAgentExecutor:
    """Bridge: expose a Microsoft Agent Framework agent as an A2A AgentExecutor.

    The A2A server does not know about Agent Framework. It speaks its own interface -
    execute(context, event_queue) - so this tiny adapter is what makes any agent you
    build A2A-callable. This IS the 'wrap it into an A2A server' step, in 20 lines.
    """

    def __init__(self, agent):
        self.agent = agent

    async def execute(self, context, event_queue) -> None:
        # Pull the caller's text out of the request context.
        try:
            query = context.get_user_input()
        except Exception:
            query = str(getattr(context, "message", ""))

        result = await self.agent.run(query)
        text = str(result)

        from a2a.utils import new_agent_text_message
        event = new_agent_text_message(text)

        # enqueue_event is async in some 0.3.x builds, sync in others.
        maybe = event_queue.enqueue_event(event)
        if hasattr(maybe, "__await__"):
            await maybe

    async def cancel(self, context, event_queue) -> None:
        raise NotImplementedError("cancel is not supported in this lab agent")


def serve(agent, card, host: str, port: int):
    """Wrap any agent in an A2A server and run it.

    Three pieces, and they map exactly onto the protocol:
      * AgentExecutor  - runs your agent when a task arrives
      * TaskStore      - remembers tasks through their lifecycle
      * AgentCard      - what callers fetch to decide whether to trust you
    """
    import uvicorn
    from a2a.server.apps import A2AStarletteApplication
    from a2a.server.request_handlers import DefaultRequestHandler
    from a2a.server.tasks import InMemoryTaskStore

    # Prefer the official Agent Framework bridge if it is installed AND compatible;
    # otherwise use our own 20-line executor above.
    executor = None
    try:
        from agent_framework_a2a import AgentFrameworkExecutor  # type: ignore
        executor = AgentFrameworkExecutor(agent)
    except Exception:
        executor = _FrameworkAgentExecutor(agent)

    handler = DefaultRequestHandler(
        agent_executor=executor,
        task_store=InMemoryTaskStore(),
    )
    app = A2AStarletteApplication(agent_card=card, http_handler=handler)

    print(f"\nServing '{card.name}' at http://{host}:{port}")
    print(f"Agent card: http://{host}:{port}/.well-known/agent-card.json")
    print(f"Executor:   {type(executor).__name__}\n")

    uvicorn.run(app.build(), host=host, port=port)


async def ask_a2a(base_url: str, question: str, message_id: str = "sfmc-001", verbose: bool = True):
    """Discover -> delegate -> observe. The three moves of every A2A call."""
    import httpx
    from a2a.client import A2ACardResolver

    async with httpx.AsyncClient(timeout=120) as http:
        # ---- 1. DISCOVER -------------------------------------------------------------
        card = await A2ACardResolver(http, base_url).get_agent_card()
        if verbose:
            print(f"Discovered : {card.name} v{card.version}")
            print(f"Skills     : {[s.id for s in card.skills]}")
            print(f"Streaming  : {card.capabilities.streaming}")

        # ---- 2. DELEGATE -------------------------------------------------------------
        from a2a.types import Message, Part, Role, TextPart

        try:
            part = Part(root=TextPart(text=question))       # 0.3.x
        except Exception:
            part = Part(text=question)                      # 1.x shape, just in case

        message = Message(role=Role.user, message_id=message_id, parts=[part])

        # ClientFactory in newer 0.3.x; A2AClient in older builds.
        client = None
        try:
            from a2a.client import ClientFactory
            try:
                from a2a.client import ClientConfig
                client = ClientFactory(ClientConfig(httpx_client=http)).create(card)
            except Exception:
                client = ClientFactory(httpx_client=http).create(card)
        except Exception:
            from a2a.client import A2AClient
            client = A2AClient(httpx_client=http, agent_card=card)

        # ---- 3. OBSERVE --------------------------------------------------------------
        out = []
        try:
            async for event in client.send_message(message):
                if verbose:
                    print(event)
                out.append(str(event))
        except TypeError:
            # Older A2AClient wants a params object and returns a single response.
            from a2a.types import MessageSendParams, SendMessageRequest
            req = SendMessageRequest(
                id=message_id,
                params=MessageSendParams(message=message),
            )
            response = await client.send_message(req)
            if verbose:
                print(response)
            out.append(str(response))

        return "\n".join(out)



# =====================================================================================
# 4b. Orchestration builder helpers
#
# The builders have changed shape across releases: some take `participants` as a
# constructor keyword, others expose a fluent .participants([...]) method. These
# helpers try both so the step files stay readable and you are not debugging a
# builder signature during a lab.
#
# If one of these still fails, print the real signature:
#     python -c "import inspect; from agent_framework.orchestrations import SequentialBuilder; print(inspect.signature(SequentialBuilder.__init__))"
# =====================================================================================

def _build(builder_cls, agents, **extra):
    """Construct a workflow from a builder class, whichever API shape it has."""
    errors = []

    # Shape A: participants as a constructor keyword
    try:
        return builder_cls(participants=agents, **extra).build()
    except Exception as exc:
        errors.append(f"  participants= kwarg: {type(exc).__name__}: {exc}")

    # Shape B: fluent .participants([...])
    try:
        b = builder_cls(**extra)
        if hasattr(b, "participants"):
            return b.participants(agents).build()
    except Exception as exc:
        errors.append(f"  fluent .participants(): {type(exc).__name__}: {exc}")

    # Shape C: positional
    try:
        return builder_cls(agents, **extra).build()
    except Exception as exc:
        errors.append(f"  positional: {type(exc).__name__}: {exc}")

    import inspect
    raise RuntimeError(
        f"Could not construct {builder_cls.__name__}. Attempts:\n"
        + "\n".join(errors)
        + f"\n\n  Real signature: {inspect.signature(builder_cls.__init__)}"
    )


def build_sequential(agents):
    """Pipeline: each agent consumes what the previous one produced."""
    from agent_framework.orchestrations import SequentialBuilder
    return _build(SequentialBuilder, agents)


def build_concurrent(agents):
    """Fan-out / fan-in: every agent answers the same prompt at once."""
    from agent_framework.orchestrations import ConcurrentBuilder
    return _build(ConcurrentBuilder, agents)


def build_group_chat(agents, max_iterations: int = 6):
    """Star topology. An orchestrator decides who speaks next. ALWAYS capped.

    This builder has NO default orchestrator - you must pass one of
    orchestrator_agent, orchestrator, or selection_func. That is deliberate:
    speaker selection IS the design of a group chat, so the framework makes you
    state it rather than guessing for you.

    We pass a selection_func doing round-robin by participant NAME. The function must
    return a name that exists in the participant list - an index or None is rejected.

    max_rounds is the hard cap, and it is a BUDGET, not a tuning knob. An uncapped
    group chat is an uncapped bill. Set it to 2 and watch the loop stop mid-refinement.

    STRETCH GOAL (the constructor supports it): round-robin keeps talking even after
    the Redactor says APPROVED. Pass a `termination_condition` to stop as soon as the
    work is approved - that typically halves the token cost of the loop.
    """
    from agent_framework.orchestrations import GroupChatBuilder

    names = [getattr(a, "name", None) or f"agent{i}" for i, a in enumerate(agents)]

    def select_next(*args, **kwargs):
        """Round-robin by name. Must return a participant NAME."""
        messages = None
        for candidate in list(args) + list(kwargs.values()):
            if isinstance(candidate, (list, tuple)) and candidate:
                messages = candidate
                break
            for attr in ("messages", "conversation", "history"):
                got = getattr(candidate, attr, None)
                if isinstance(got, (list, tuple)):
                    messages = got
                    break
            if messages:
                break
        messages = messages or []
        return names[len(messages) % len(names)]

    return GroupChatBuilder(
        participants=agents,
        selection_func=select_next,
        max_rounds=max_iterations,
    ).build()


def build_handoff(coordinator, specialists, human_target=None):
    """Decentralised routing. The current agent picks the next, via a tool call."""
    from agent_framework.orchestrations import HandoffBuilder

    targets = list(specialists) + ([human_target] if human_target else [])
    everyone = [coordinator] + targets

    try:
        b = HandoffBuilder(participants=everyone)
    except TypeError:
        b = HandoffBuilder(everyone)

    if hasattr(b, "set_coordinator"):
        b = b.set_coordinator(coordinator)

    if hasattr(b, "add_handoff"):
        b = b.add_handoff(coordinator, targets)
        for s in specialists:
            if human_target:
                b = b.add_handoff(s, [coordinator, human_target])
            else:
                b = b.add_handoff(s, [coordinator])
    return b.build()



def _text_of(obj) -> str:
    """Dig readable text out of whatever the framework handed us.

    Workflow events carry Message / AgentResponse objects whose repr is a memory
    address. For a lab you need to SEE what each agent said, so this walks the
    common shapes and pulls the text out.
    """
    if obj is None:
        return ""
    if isinstance(obj, str):
        return obj

    # Direct text attribute
    for attr in ("text", "content"):
        val = getattr(obj, attr, None)
        if isinstance(val, str) and val.strip():
            return val

    # A response wrapping messages
    for attr in ("messages", "parts", "contents"):
        seq = getattr(obj, attr, None)
        if isinstance(seq, (list, tuple)):
            chunks = [_text_of(x) for x in seq]
            joined = "\n".join(c for c in chunks if c)
            if joined.strip():
                return joined

    # A response wrapping a response
    for attr in ("agent_response", "response", "value", "result"):
        inner = getattr(obj, attr, None)
        if inner is not None and inner is not obj:
            got = _text_of(inner)
            if got.strip():
                return got

    if isinstance(obj, (list, tuple)):
        chunks = [_text_of(x) for x in obj]
        joined = "\n".join(c for c in chunks if c)
        if joined.strip():
            return joined

    return ""


def _print_event(event, seen: set) -> str:
    """Print one workflow event in a form a human can read. Returns the text."""
    etype = getattr(event, "type", None) or getattr(event, "kind", None) or ""
    who = getattr(event, "executor_id", None) or getattr(event, "source_id", "") or ""
    data = getattr(event, "data", None)

    # Only the events that carry agent output are worth showing in a lab.
    if etype not in ("executor_completed", "output", "agent_response", "message"):
        return ""

    text = _text_of(data).strip()
    if not text:
        return ""

    key = (who, text[:200])
    if key in seen:          # executor_completed and output often duplicate
        return ""
    seen.add(key)

    label = who or etype
    print(f"\n{'=' * 70}\n  {label}\n{'=' * 70}\n{text}")
    return text


async def run_workflow(workflow, message, verbose: bool = True) -> str:
    """Run a workflow and narrate it - one labelled block per agent turn.

    The framework emits raw event objects. For a lab that is useless, so this pulls
    out who spoke and what they said, and prints it as a readable transcript.
    """
    STREAMING = ("run_stream", "run_streaming", "run_stream_async",
                 "stream", "invoke_stream", "stream_async")
    SINGLE = ("run", "run_async", "invoke", "invoke_async", "execute")

    try:
        from narrate import turn as _turn, event as _event
    except ImportError:                       # narrate.py not on the path
        def _turn(speaker, text, note=""):
            print(f"\\n--- {speaker} ---\\n{text}")

        def _event(label, detail=""):
            print(f"  >> {label}{': ' + detail if detail else ''}")

    collected: list[str] = []
    seen: set = set()
    order: list[str] = []

    def _handle(ev) -> None:
        etype = getattr(ev, "type", None) or getattr(ev, "kind", None) or ""
        who = getattr(ev, "executor_id", None) or getattr(ev, "source_id", "") or ""
        data = getattr(ev, "data", None)

        # Call out the protocol / control-flow moments, quietly.
        if etype == "executor_invoked" and who and who not in order:
            order.append(who)
            if who.lower() not in ("input-conversation", "input"):
                _event("handing the turn to", who)

        if etype not in ("executor_completed", "output", "agent_response", "message"):
            return

        text = _text_of(data).strip()
        if not text or who.lower() in ("input-conversation", "input"):
            return

        key = (who, text[:200])
        if key in seen:                       # completed + output often duplicate
            return
        seen.add(key)

        note = ""
        upper = text.upper()
        if upper.startswith("APPROVED") or upper == "APPROVED":
            note = "approved - nothing leaves the desk until this"
        elif "handoff_to" in text:
            note = "routing decision made by the model"

        if verbose:
            _turn(who or etype, text, note)
        collected.append(f"[{who}] {text}")

    for name in STREAMING:
        fn = getattr(workflow, name, None)
        if fn is None:
            continue
        try:
            async for ev in fn(message):
                _handle(ev)
            if collected:
                return "\\n\\n".join(collected)
        except TypeError:
            continue
        except AttributeError:
            continue

    for name in SINGLE:
        fn = getattr(workflow, name, None)
        if fn is None:
            continue
        try:
            result = fn(message)
            if hasattr(result, "__await__"):
                result = await result
            text = _text_of(result) or str(result)
            if verbose:
                _turn("result", text)
            return text
        except TypeError:
            continue

    available = ", ".join(n for n in dir(workflow) if not n.startswith("_"))
    raise RuntimeError(
        "Could not find a run method on this Workflow.\\n"
        f"Available members: {available}"
    )


# Ports, so the three A2A servers can run side by side on one laptop.
PORT_SIGNAL = int(os.environ.get("PORT_SIGNAL", "9001"))
PORT_CASES = int(os.environ.get("PORT_CASES", "9002"))
PORT_COE = int(os.environ.get("PORT_COE", "9003"))
HOST = os.environ.get("A2A_HOST", "127.0.0.1")

URL_SIGNAL = f"http://{HOST}:{PORT_SIGNAL}"
URL_CASES = f"http://{HOST}:{PORT_CASES}"
URL_COE = f"http://{HOST}:{PORT_COE}"


# =====================================================================================
# 5. The week we are working
# =====================================================================================

THIS_WEEK = (
    "Prepare the FY27-W12 service review for CUSTOMER-A. Since Tuesday the public "
    "endpoint has been returning intermittent 5xx errors and backend latency is up, there "
    "was no deployment, and log ingestion cost has risen. Tell the TCL what happened, what "
    "we think the cause is, and what we are asking the customer to do."
)

LIVE_INCIDENT = (
    "Escalation just came in for CUSTOMER-A: the public endpoint is failing about one "
    "request in ten and the on-call team wants to know within the hour whether this is a "
    "monitoring gap, a known assessment risk, or an open case already with the product "
    "group. Where does this go first?"
)
```

</details>

---

## Step 1 — A plain agent on Foundry

> **Adds:** One working specialist. No protocol, no orchestration, nothing clever.

We start here deliberately. The single most important idea in A2A is that
**it does not change how you build an agent** — and you can only see that if you build the
agent first and add the protocol second. Start with the protocol and people conclude it is
a framework, which is wrong and expensive.

This is also the smallest thing that can fail. If this does not run, nothing later will.

### The code — `src/step1_signal_agent.py`

```python
"""STEP 1 - A plain agent on Foundry. No protocol. No orchestration."""

import asyncio

import narrate
from common import SIGNAL, get_client, get_monitor_signals, make, sdk_flavour

QUESTION = (
    "For FY27-W12 on CUSTOMER-A: which alerts are real signal and which are noise, "
    "and what monitoring coverage is missing?"
)


async def main():
    narrate.step_header(
        1, "One agent, one tool",
        adds="The first box on our architecture diagram - a single working specialist. "
             "No protocol, no orchestration, nothing clever. This is deliberately the "
             "smallest thing that works: if this does not run, nothing later will.",
        watch_for="The agent reads a week of synthetic Azure Monitor data and separates "
                  "SIGNAL from NOISE. Watch whether it JUSTIFIES each call - an agent "
                  "that cannot say why is not usable in mission-critical support.",
    )

    narrate.event("SDK in use", sdk_flavour())
    narrate.event("the week", "CUSTOMER-A, FY27-W12 - 5xx errors since Tuesday, "
                              "latency up, no deployment")

    signal = make(get_client(), "Signal", SIGNAL, [get_monitor_signals])
    result = await signal.run(QUESTION)

    narrate.turn("Signal", str(result), "one agent, one tool, no orchestration")

    narrate.takeaway(
        "You authenticated to a Foundry project with Entra ID. There is no API key "
        "anywhere in this repo.",
        "The model chose to call get_monitor_signals because its DESCRIPTION said it "
        "could. Tool selection is a writing problem before it is a coding problem.",
        "Nothing here is multi-agent yet - and for this one question, it did not need "
        "to be. That is the discipline: add an agent only when you can name the "
        "expertise, the trust boundary, or the parallelism it buys you.",
    )

    narrate.ask(
        "AKS-NodePool-CPU-High fired 228 times. Did the agent call it noise, and did "
        "it say WHY?",
        "Would a second agent have made this particular answer better? Be honest.",
    )


if __name__ == "__main__":
    asyncio.run(main())
```

### Run it

```bash
python src/step1_signal_agent.py
```

### What you should see

A few paragraphs of analysis naming specific alert rules. You are looking for
three things:

- `AKS-NodePool-CPU-High` identified as **noise** — 228 firings on a static 70% threshold
- `Frontdoor-5xx-RateSpike` identified as **signal** — Sev1, three firings inside the
  Tuesday 09:14–09:58 UTC window
- The three monitoring **coverage gaps** called out explicitly

### Check your understanding

- Did the agent say *why* `AKS-NodePool-CPU-High` is noise, or just assert it? **An agent that cannot justify a conclusion is not usable in mission-critical support.**
- Nothing here is multi-agent yet. Honestly: for this one question, would a second agent have made the answer better?
- The tool was selected by the model from its description alone. Re-read the docstring of `get_monitor_signals` — would *you* pick it from that description?

---

## Step 2 — Wrap it into an A2A server

> **Adds:** An **agent card**. The agent becomes callable by anyone who speaks A2A — a different framework, a different team, a different cloud.

Compare this file with step 1. The agent is **identical** — same instructions, same
tool, same Foundry project. All we added is a card and a server.

**A2A does not change how you build an agent. It changes who can reach it.** Most of the
confusion in this space dissolves the moment that lands.

The agent card is a **contract, not documentation**. It is how a caller decides whether to
delegate to you at all.

### The code — `src/step2_signal_a2a_server.py`

```python
"""STEP 2 - Wrap the Signal agent into an A2A server. It gets an agent card."""

import narrate
from common import (
    HOST, PORT_SIGNAL, SIGNAL, URL_SIGNAL,
    agent_card, get_client, get_monitor_signals, make, serve,
)

card = agent_card(
    name="sfmc-signal-agent",
    description="Azure Monitor alert analysis for a mission-critical workload review week.",
    skill_id="analyse_alert_week",
    skill_name="Analyse a review week's alerts",
    skill_description="Separates real signal from alert noise and reports coverage gaps.",
    base_url=URL_SIGNAL,
    tags=["monitoring", "azure-monitor", "sfmc"],
    examples=["Which alerts in FY27-W12 are noise?", "What monitoring coverage is missing?"],
)


def main():
    narrate.step_header(
        2, "Wrap it into an A2A server",
        adds="An AGENT CARD. The agent becomes callable by anyone who speaks A2A - a "
             "different framework, a different team, a different cloud. Compare this "
             "file with step 1: the agent is IDENTICAL. Same instructions, same tool, "
             "same Foundry project. All we added is a card and a server.",
        watch_for="This is the single most important idea in the protocol: A2A does "
                  "not change how you BUILD an agent. It changes who can REACH it.",
    )

    narrate.event("next", f"fetch the card:  curl {URL_SIGNAL}/.well-known/agent-card.json")
    narrate.event("then", "in another terminal:  python src/step3_a2a_client.py")
    narrate.event("leave this running", "the server must stay up for steps 3 and 10")

    agent = make(get_client(), "Signal", SIGNAL, [get_monitor_signals])
    serve(agent, card, HOST, PORT_SIGNAL)


if __name__ == "__main__":
    main()

# READ THE AGENT CARD BEFORE YOU MOVE ON
# It advertises: name, version, the skills you offer, whether you stream, what input
# and output types you take, and which auth schemes you accept. This is how a caller
# decides whether to delegate to you AT ALL. It is a CONTRACT, not documentation.
#
# And notice what is NOT in it: your instructions, your tool, your Foundry project.
# That omission is the point.
```

### Run it

```bash
# Terminal 1 — leave this running
python src/step2_signal_a2a_server.py

# Terminal 2 — look at what you just published
curl http://127.0.0.1:9001/.well-known/agent-card.json
```

### What you should see

A JSON document advertising `name`, `version`, `skills`, `capabilities`
(streaming, push notifications), `defaultInputModes` / `defaultOutputModes`, and the
authentication schemes the agent accepts.

A2A v1.0 also supports **signed agent cards** using JSON Web Signature, so a caller can
cryptographically verify the identity behind the card.

### Check your understanding

- Your instructions, your tool and your Foundry project are **not** in the card. Why is that the point rather than a limitation?
- The card lists auth schemes. Nothing in the protocol enforces them — **who does?** (You do. Enforcement is the implementer's job.)
- If a caller fetched this card from an attacker-controlled URL, what would they believe? (This is why you pin identities and verify signatures.)

---

## Step 3 — Call it from an A2A client

> **Adds:** The first arrow on the diagram. You are now a client of a remote agent.

These three moves are the **entire protocol**. Everything else in A2A is a
variation on them:

1. **Discover** — fetch the agent card. Decide whether to trust it.
2. **Delegate** — send a `Message`. The remote agent opens a **Task**.
3. **Observe** — the task moves through its lifecycle and emits **Artifacts**.

The task lifecycle:

```
submitted ──▶ working ──▶ input_required ──▶ working ──▶ completed
                  │                                          
                  ├──▶ failed                                 
                  └──▶ canceled                               
```

Note `input_required`. The protocol has a built-in notion of *"I need to ask a human
something"* — that is not an afterthought bolted on by frameworks.

Transports: JSON-RPC 2.0, gRPC, or HTTP+JSON. Server-Sent Events for streaming, webhooks
for push notification on tasks that run for hours.

### The code — `src/step3_a2a_client.py`

```python
"""STEP 3 - Call the Signal agent over A2A. Discover, delegate, observe."""

import asyncio

import narrate
from common import URL_SIGNAL, ask_a2a

QUESTION = (
    "For the current review week: which alert rules are noise rather than signal, which "
    "correlate with an incident window, and what monitoring coverage is missing?"
)


async def main():
    narrate.step_header(
        3, "Call it from an A2A client",
        adds="The first arrow on the diagram. You are now a CLIENT of a remote agent - "
             "one you did not build, running in a process you do not control.",
        watch_for="Three moves, and they are the entire protocol. DISCOVER the agent "
                  "card and decide whether to trust it. DELEGATE by sending a message. "
                  "OBSERVE what comes back. Also notice what you CANNOT see.",
    )

    narrate.event("step 1", "DISCOVER - fetch the agent card")
    text = await ask_a2a(URL_SIGNAL, QUESTION, message_id="step-3-001", verbose=False)

    narrate.event("step 2", "DELEGATE - send a Message; the remote agent does the work")
    narrate.event("step 3", "OBSERVE - read what comes back")

    narrate.turn("Signal (remote, over A2A)", text,
                 "same agent as step 1 - but you reached it over HTTP")

    narrate.takeaway(
        "You never saw the remote agent's instructions, its tool, its model deployment "
        "or its data. That OPACITY is not a limitation - it is the feature that makes "
        "A2A safe across an organisational boundary.",
        "For short synchronous work the agent replies with a Message. For long-running "
        "work it opens a TASK with a lifecycle - submitted, working, input_required, "
        "completed / failed / canceled - and streams status or calls you back on a "
        "webhook. Same protocol, two shapes.",
        "Note input_required in that lifecycle. The protocol has a built-in notion of "
        "'I need to ask a human something'. That is not an afterthought.",
    )

    narrate.ask(
        "Kill the server and re-run this. What comes back, and did your code handle it? "
        "failed and canceled are states you must code for, not just completed.",
        "What would you have to strip from a real engagement's context before sending "
        "it across this boundary?",
    )


if __name__ == "__main__":
    asyncio.run(main())
```

### Run it

```bash
# step 2 must still be running
python src/step3_a2a_client.py
```

### What you should see

The discovered card details, then a stream of task events ending in the
completed task and its artifacts.

**Notice what you cannot see:** the remote agent's instructions, its tool, its model
deployment or its data. That opacity is the feature that makes A2A safe across an
organisational boundary.

### Check your understanding

- Which state would a long-running research task sit in for minutes — and how would you be told when it finished? (Streaming over SSE, or a webhook push notification.)
- Kill the server and re-run this. What comes back, and did your code handle it? `failed` and `canceled` are states you must code for, not just `completed`.
- You sent plain text. What would you have to strip before sending real engagement context across this boundary?

---

## Step 4 — A second A2A server

> **Adds:** A multi-agent *system*. Two independent specialists, neither knowing the other exists.

Notice how little ceremony this took: a new agent, a new card, a new port. That
cheapness is a trap as much as a feature — it makes it easy to add agents you did not need.

**Rule of thumb: agents-as-tools inside a crew, A2A between crews.** Do not add an HTTP hop
where a function call will do.

### The code — `src/step4_case_a2a_server.py`

```python
"""STEP 4 - A second A2A server: the CaseReview agent."""

import narrate
from common import (
    CASE_REVIEW, HOST, PORT_CASES, URL_CASES,
    agent_card, get_client, get_open_cases, make, serve,
)

card = agent_card(
    name="sfmc-case-review-agent",
    description="Open Microsoft support case review for a mission-critical workload.",
    skill_id="review_open_cases",
    skill_name="Review open support cases",
    skill_description="Summarises open cases by severity and age and flags stalled ones.",
    base_url=URL_CASES,
    tags=["support-cases", "sfmc", "service-review"],
    examples=["Which cases are stalled?", "What is open at Sev A and how old is it?"],
)


def main():
    narrate.step_header(
        4, "A second A2A server",
        adds="The second bottom box on the diagram. Two independent specialists, each "
             "reachable over the protocol, NEITHER knowing the other exists. This is "
             "where a multi-agent SYSTEM starts.",
        watch_for="How little ceremony that took: a new agent, a new card, a new port. "
                  "That cheapness is a trap as much as a feature - it makes it easy to "
                  "add agents you did not need.",
    )

    narrate.event("rule of thumb", "agents-as-tools inside a crew, A2A between crews")
    narrate.event("leave this running", "step 10 needs all three servers up")

    agent = make(get_client(), "CaseReview", CASE_REVIEW, [get_open_cases])
    serve(agent, card, HOST, PORT_CASES)


if __name__ == "__main__":
    main()

# CHECK YOUR UNDERSTANDING
# * In production, who owns each server? If the SAME team owns both, should they have
#   been A2A at all? Do not add an HTTP hop where a function call will do.
```

### Run it

```bash
# Terminal 3 — leave this running
python src/step4_case_a2a_server.py

# from anywhere
curl http://127.0.0.1:9002/.well-known/agent-card.json
```

### What you should see

A second agent card, on port 9002, advertising the `review_open_cases` skill.

### Check your understanding

- In production, who owns each server? If the **same** team owns both, should they have been A2A at all?
- Both cards are unauthenticated right now. List what you would add before either could be reached from outside your laptop.

---

## Step 5 — Sequential: Reporter then Redactor

> **Adds:** The first orchestration pattern, and the confidentiality gate.

These two agents are **in-process, not A2A** — the side box on the diagram. Same
process, no HTTP hop, because they do not need one.

Sequential is a pipeline: fixed order, you wrote the order, each agent consumes what the
previous produced. Here order is the whole point — the Reporter cannot write before the
findings exist, and nothing leaves the desk before the Redactor has seen it.

By default each agent sees the **whole conversation**, not just the last message. That is
correct here, because the Redactor must check the draft against the original findings. For
a pure transform stage, `SequentialBuilder` offers `chain_only_agent_responses=True` —
fewer tokens, less contamination.

**If you were about to write a `for` loop over your agents, this is that loop — plus
streaming events and tool approval for free.**

### The code — `src/step5_sequential_report.py`

```python
"""STEP 5 - Sequential: findings -> Reporter -> Redactor."""

import asyncio

import narrate
from common import build_desk, build_sequential, get_client, run_workflow

FINDINGS = (
    "FINDINGS for CUSTOMER-A, FY27-W12 (synthetic):\n"
    "- Frontdoor-5xx-RateSpike fired Sev1 three times Tuesday 09:14-09:58 UTC.\n"
    "- AppGateway-BackendLatency-P95 active since Tuesday 09:12 UTC, 41 firings.\n"
    "- AKS-NodePool-CPU-High fired 228 times on a static 70% threshold - noise.\n"
    "- LogIngestion-VolumeSpike active since Wednesday; CASE-1003 open on ingestion cost.\n"
    "- RISK-03 (High, open 45 days): no synthetic availability monitoring on the primary "
    "customer-facing endpoint.\n"
    "- RISK-02 (Medium, open 60 days): static-threshold alerting, no dynamic baselines.\n"
    "- CASE-1001 (Sev A, 4 days) with the product group on the 5xx errors.\n"
    "- CASE-0987 (Sev C, 31 days) stalled: diagnostic settings missing on two data services."
)


async def main():
    narrate.step_header(
        5, "Sequential — write it, then gate it",
        adds="The first orchestration pattern, and the confidentiality gate. These two "
             "agents are IN-PROCESS, not A2A — same process, no HTTP hop, because they "
             "do not need one. Order is the whole point: the Reporter cannot write "
             "before the findings exist, and nothing leaves the desk before the "
             "Redactor has seen it.",
        watch_for="Two turns, in a fixed order you wrote. The Reporter drafts the "
                  "customer-ready summary; the Redactor either approves it or returns "
                  "numbered corrections. The Redactor sees the ORIGINAL findings too, "
                  "which is how it can catch a number that was never in them.",
    )

    desk = build_desk(get_client())
    workflow = build_sequential([desk["reporter"], desk["redactor"]])
    await run_workflow(workflow, FINDINGS)

    narrate.takeaway(
        "Sequential is a pipeline: fixed order, each agent consumes what the previous "
        "one produced. If you were about to write a for-loop over your agents, this is "
        "that loop — plus streaming events and tool approval for free.",
        "By default every agent sees the WHOLE conversation, not just the last message. "
        "Correct here, because the Redactor must check the draft against the findings. "
        "For a pure transform stage, chain_only_agent_responses=True costs fewer tokens.",
        "The Redactor is a first-class agent with a veto, not a filter bolted on at the "
        "end. That placement is the architecture, not a detail.",
    )

    narrate.ask(
        "Add 'contact is Jane Doe, jane@example.com' to FINDINGS and re-run. Does the "
        "Redactor refuse? If not, your gate is decorative — and a prompt alone is not "
        "a control.",
        "Which stage here would you restrict with chain_only_agent_responses=True, and "
        "what would it save you?",
    )


if __name__ == "__main__":
    asyncio.run(main())
```

### Run it

```bash
python src/step5_sequential_report.py
```

### What you should see

A service review draft from the Reporter, then the Redactor either returning
`APPROVED` or a numbered list of corrections.

### Check your understanding

- **Try to break the gate.** Add `contact is Jane Doe, jane@example.com` to `FINDINGS` and re-run. The Redactor *must* refuse. If it does not, your gate is decorative — and you have just learned first-hand that a prompt alone is not a control.
- Which stage here would you restrict with `chain_only_agent_responses=True`, and what would it save?
- The Redactor also rejects figures that were not in the findings. Why is that check as important as the confidentiality one?

---

## Step 6 — Concurrent: three specialists at once

> **Adds:** Fan-out / fan-in — and the test for when *parallel* is honest.

Signal, Resilience and CaseReview each read a different source. None needs
another's output, so running them serially is pure wasted latency.

**Concurrent is the pattern people reach for and then regret, because "parallel" sounds
efficient.** The test is one sentence: *if agent B should read agent A's answer, this is
the wrong pattern.*

And the default aggregator simply returns one message per participant. **Somebody still has
to merge them** — a custom aggregator, or a summarising agent. That is a design decision
you make, not a default you inherit.

### The code — `src/step6_concurrent_gather.py`

```python
"""STEP 6 - Concurrent: three specialists read the same week at once."""

import asyncio

import narrate
from common import THIS_WEEK, build_concurrent, build_desk, get_client, run_workflow


async def main():
    narrate.step_header(
        6, "Concurrent — three specialists, one week, at once",
        adds="Fan-out / fan-in, and the test for when 'parallel' is honest. Signal "
             "reads the alerts, Resilience reads the assessment risks, CaseReview reads "
             "the open cases. Three different sources, and none of them needs another's "
             "output - so running them one at a time is pure wasted latency.",
        watch_for="Three independent answers, with NO ordering and NO shared "
                  "refinement. Nobody merges them. That is the design decision this "
                  "pattern hands back to you.",
    )

    desk = build_desk(get_client())
    workflow = build_concurrent([desk["signal"], desk["resilience"], desk["cases"]])
    await run_workflow(workflow, THIS_WEEK)

    narrate.takeaway(
        "THE TEST, in one sentence: if agent B should read agent A's answer, this is "
        "the wrong pattern. Concurrent is the one people reach for and then regret, "
        "because 'parallel' sounds efficient.",
        "The default aggregator returns one message per participant. Somebody still has "
        "to merge them - a custom aggregator, or a summarising agent. That is a "
        "decision you make, not a default you inherit.",
        "Here it IS honest: three sources, three skills, no dependency between them.",
    )

    narrate.ask(
        "Signal and Resilience may disagree about the cause. Who reconciles them, and "
        "when do you decide that - now, or in production?",
        "Add the Reporter as a fourth concurrent participant and watch it write a "
        "service review based on nothing. That failure IS the lesson.",
    )


if __name__ == "__main__":
    asyncio.run(main())
```

### Run it

```bash
python src/step6_concurrent_gather.py
```

### What you should see

Three independent answers — alerts, risks and cases — returned together, with
no ordering and no shared refinement between them.

### Check your understanding

- Who should merge the three answers, and what happens when Signal and Resilience contradict each other? Decide now, not in production.
- **Stretch:** add the Reporter as a fourth concurrent participant and watch it write a service review based on nothing. That failure *is* the lesson.
- Compare total wall-clock time against running the three sequentially. Was the saving worth the extra complexity here? Be honest.

---

## Step 7 — The CoE Baseline Advisor

> **Adds:** The reason A2A exists at all.

Steps 2 and 4 served agents **you own**. This one is different in kind.

The SfMC Monitoring & Observability CoE owns the alert baseline for each Azure service.
Your desk needs to ask it a question. You must not need a copy of their prompts; they must
not need access to your engagement's data. **Different team, different Foundry project,
different data boundary.**

That — not convenience, not modularity — is what justifies the HTTP hop.

Notice the instruction block: this agent is told to refuse customer-identifying data even
if a caller sends it. Defence in depth: the caller redacts outbound, *and* the callee
refuses inbound.

### The code — `src/step7_coe_a2a_server.py`

```python
"""STEP 7 - The third A2A server: another team's agent, another Foundry project."""

import narrate
from common import (
    COE_BASELINE, HOST, PORT_COE, URL_COE,
    agent_card, get_client, make, serve,
)

card = agent_card(
    name="sfmc-coe-baseline-advisor",
    description="SfMC Monitoring & Observability CoE alert-baseline guidance for Azure services.",
    skill_id="alert_baseline",
    skill_name="Recommend an alert baseline",
    skill_description="Returns the CoE-recommended alert baseline for an Azure service tier.",
    base_url=URL_COE,
    tags=["monitoring", "azure-monitor", "sfmc", "baseline", "coe"],
    examples=[
        "What is the recommended alert baseline for a public API tier behind Front Door?",
        "Should node CPU use a static threshold or a dynamic baseline?",
    ],
)


def main():
    narrate.step_header(
        7, "The CoE Baseline Advisor — another team's agent",
        adds="The reason A2A exists at all. Steps 2 and 4 served agents YOU own. This "
             "one is different in kind: the Monitoring & Observability CoE owns the "
             "alert baseline for each Azure service. Your desk needs to ask it a "
             "question. You must not need a copy of their prompts; they must not need "
             "access to your engagement's data.",
        watch_for="Different team, different Foundry project, different data boundary. "
                  "THAT - not convenience, not modularity - is what justifies an HTTP "
                  "hop between two agents.",
    )

    narrate.event("defence in depth",
                  "this agent REFUSES customer-identifying data even if a caller sends "
                  "it - the caller redacts outbound, the callee refuses inbound")
    narrate.event("leave this running", "step 10 calls this agent")

    agent = make(get_client(), "CoEBaselineAdvisor", COE_BASELINE)
    serve(agent, card, HOST, PORT_COE)


if __name__ == "__main__":
    main()

# CHECK YOUR UNDERSTANDING
# * Look at the question step 10 sends here: no customer name, no subscription ID, no
#   case URL. Crossing a team boundary is where de-identification stops being a lab
#   rule and becomes a control.
# * What would you need on the wire before calling this with real context? Bearer token
#   enforced, card signature verified, identity pinned, egress policy, Redactor outbound.
```

### Run it

```bash
# Terminal 4 — leave this running
python src/step7_coe_a2a_server.py
```

### What you should see

A third agent card on port 9003, advertising the `alert_baseline` skill.

### Check your understanding

- Look at the question step 10 sends this agent — no customer name, no subscription ID, no case URL. **Crossing a team boundary is where de-identification stops being a lab rule and becomes a control.**
- What would you need on the wire before calling this with real context? (Bearer token enforced, card signature verified, identity pinned, egress policy, Redactor outbound.)
- If this agent were in another tenant entirely, what changes — and what does not?

---

## Step 8 — Handoff: dynamic routing

> **Adds:** The orchestrator, and the *dynamic hand-off* arrow on the diagram.

There is **no orchestrator object** in this file. Read that again.

Intake is a participant that happens to hold the conversation, and when it decides a
specialist should own the work it **calls a generated tool** — `handoff_to_<target>`,
created for you from the handoff graph you declared. The routing decision is made by the
model, inside the agent, not by code you wrote. That is what *decentralised* means.

The most important line in the file is `tcl_queue`. In mission-critical support some
decisions are not the agent's to make — a severity call, a customer commitment, anything
contractual. In a handoff architecture you express that as **a handoff target that is a
human queue, not an agent**. Design it in on day one, not after the first incident.

**Handoff is also the only built-in pattern that is interactive by default** — it pauses
for the user between turns. Right for a support conversation; possibly a latency bug at
2 a.m.

### The code — `src/step8_handoff_orchestrator.py`

```python
"""STEP 8 - Handoff: Intake routes a live incident, dynamically."""

import asyncio

import narrate
from common import LIVE_INCIDENT, build_desk, build_handoff, get_client, run_workflow

MAX_HOPS = 4


async def main():
    narrate.step_header(
        8, "Handoff — the model does the routing",
        adds="The top box on the diagram: the orchestrator, and the 'dynamic hand-off' "
             "arrow. There is NO orchestrator object in this code. Intake is a "
             "participant that happens to hold the conversation, and when it decides a "
             "specialist should own the work it CALLS A TOOL - handoff_to_<target>. "
             "The routing decision is made by the model, inside the agent.",
        watch_for="The handoff_to_<target> tool call, and Intake's stated REASON. Also "
                  "note the TCL escalation queue in the graph: some decisions are not "
                  "the agent's to make, and you express that as an edge to a human.",
    )

    narrate.event("the incident", "public endpoint failing ~1 request in 10; on-call "
                                  "wants to know within the hour where this belongs")

    desk = build_desk(get_client())
    workflow = build_handoff(
        coordinator=desk["intake"],
        specialists=[desk["signal"], desk["resilience"], desk["cases"]],
        human_target=desk["tcl_queue"],
    )

    transcript = await run_workflow(workflow, LIVE_INCIDENT)
    hops = transcript.count("handoff_to")

    narrate.event("handoffs observed", f"{hops}  (budget {MAX_HOPS})")
    if hops > MAX_HOPS:
        narrate.event("HOP BUDGET EXCEEDED",
                      "in production this is where you escalate to a human, not retry")

    narrate.takeaway(
        "DECENTRALISED. You defined what routing is POSSIBLE; the model decided what "
        "actually happened. Compare group chat, where a central orchestrator picks.",
        "This builder made three demands, and each is a design lesson: every agent "
        "needs history persistence (a handoff is a tool call that short-circuits the "
        "turn), you must name a START agent, and you must declare the GRAPH.",
        "Handoff is the only built-in pattern INTERACTIVE BY DEFAULT - it pauses for "
        "the user between turns. Right for a support conversation. At 2 a.m., maybe a "
        "latency bug.",
        "Ping-pong is the number-one handoff failure in production. That is what the "
        "hop budget is for.",
    )

    narrate.ask(
        "Does Intake's stated reason hold up, or did it route on a keyword?",
        "Which of these agents should never trigger a customer-facing action without a "
        "human in between - and how would you ENFORCE that rather than instruct it?",
    )


if __name__ == "__main__":
    asyncio.run(main())
```

### Run it

```bash
python src/step8_handoff_orchestrator.py
```

### What you should see

A tool call to `handoff_to_<target>` with Intake's stated reason, then the
receiving specialist's analysis. The `MAX_HOPS` guard prints and stops if the agents start
handing back and forth.

### Check your understanding

- Find the `handoff_to_<target>` call. Does Intake's stated reason hold up, or did it route on a keyword?
- The incident contains a monitoring question **and** a case question. Did Intake pick the more urgent one, and would you defend that choice to a customer?
- **Stretch:** make two specialists hand back unconditionally and watch `MAX_HOPS` catch the ping-pong. This is the number-one handoff failure in production.
- Which of these agents should never be able to trigger a customer-facing action without a human in between — and how would you *enforce* that rather than instruct it?

---

## Step 9 — Group Chat: refine until APPROVED

> **Adds:** Iterative refinement, and the centralised / decentralised distinction.

Star topology. An orchestrator sits in the middle and decides who speaks next, and
every participant sees the full shared conversation — which is exactly what lets the
Reporter act on the Redactor's corrections.

> **Group chat is centralised** — an orchestrator picks the speaker.
> **Handoff is decentralised** — the current agent picks, by calling a tool.

Speaker selection is the whole design: round-robin (simple, fair, wastes turns),
prompt-based (a model picks), or your own function.

**Whatever you choose, set a maximum iteration count. An uncapped group chat is an
uncapped bill.**

### The code — `src/step9_group_chat.py`

```python
"""STEP 9 - Group Chat: Reporter and Redactor refine until the cap."""

import asyncio

import narrate
from common import build_desk, build_group_chat, get_client, run_workflow
from step5_sequential_report import FINDINGS

TASK = (
    "Write the FY27-W12 service review summary for CUSTOMER-A from these findings, then "
    "revise it until the Redactor approves it.\n\n" + FINDINGS
)

MAX_ROUNDS = 6


async def main():
    narrate.step_header(
        9, "Group Chat — refine until approved",
        adds="Iterative refinement, and the difference between centralised and "
             "decentralised coordination. A star topology: an orchestrator sits in the "
             "middle and decides who speaks next, and every participant sees the full "
             "shared conversation — which is exactly what lets the Reporter act on the "
             "Redactor's corrections.",
        watch_for=f"Draft, critique, revise — alternating turns, capped at {MAX_ROUNDS} "
                  "rounds. Compare with step 5: same two agents, but here they LOOP. "
                  "Sequential ran each agent once; group chat keeps going.",
    )

    desk = build_desk(get_client())
    workflow = build_group_chat([desk["reporter"], desk["redactor"]],
                                max_iterations=MAX_ROUNDS)
    await run_workflow(workflow, TASK)

    narrate.takeaway(
        "GROUP CHAT is centralised — an orchestrator picks the speaker. HANDOFF is "
        "decentralised — the current agent picks, by calling a tool. That is the whole "
        "difference between the two patterns.",
        "This builder has NO default orchestrator. You must pass orchestrator_agent, "
        "orchestrator, or selection_func. That is deliberate: speaker selection IS the "
        "design of a group chat, so the framework makes you state it.",
        f"max_rounds={MAX_ROUNDS} is a BUDGET, not a tuning knob. An uncapped group "
        "chat is an uncapped bill.",
    )

    narrate.ask(
        "Re-run with max_iterations=2. The loop stops mid-refinement. Was that the "
        "right budget, and how would you decide?",
        "Round-robin keeps talking even after the Redactor says APPROVED. The "
        "constructor takes a termination_condition — wire it up and watch the token "
        "cost roughly halve.",
    )


if __name__ == "__main__":
    asyncio.run(main())
```

### Run it

```bash
python src/step9_group_chat.py
```

### What you should see

Draft → critique → revision → `APPROVED`, or the loop hitting its iteration cap
first.

### Check your understanding

- Re-run with `max_iterations=2`. The loop stops mid-refinement. **That cap is a budget, not a tuning knob.**
- Round-robin wastes a turn after `APPROVED`. Write a selection function that terminates on it and watch the token cost roughly halve.
- The Redactor is a **participant with a veto**, not a filter at the end. Why does that placement matter for a mission-critical engagement?

---

## Step 10 — Assemble the full desk

> **Adds:** **Nothing new. That is the point.** This is the first diagram, running end to end.

Three remote agents gathered concurrently over A2A — one of them owned by another
team — and two agents in your own process, because they did not need a network hop.

The payoff of this step is not the code. It is seeing that **the architecture was the set
of boundary decisions**, and the code was almost incidental.

### The code — `src/step10_full_desk.py`

```python
"""STEP 10 - Assemble the whole thing. This is the diagram from slide one, running."""

import asyncio

import narrate
from common import (
    URL_CASES, URL_COE, URL_SIGNAL,
    ask_a2a, build_desk, build_group_chat, get_client, run_workflow,
)

WEEK_Q = (
    "For the current review week on CUSTOMER-A: intermittent 5xx on the public endpoint "
    "since Tuesday, backend latency up, no deployment, log ingestion cost rising. "
    "Report what you see from your source."
)

# Deliberately de-identified: no customer, no subscription, no person.
COE_Q = (
    "For a mission-critical public API tier behind Front Door with an AKS compute tier: "
    "what alert baseline should be in place, which signals should use dynamic thresholds "
    "instead of static ones, and what availability testing is expected? Context: static "
    "70% node CPU alerting produces ~228 firings a week and there is no synthetic "
    "availability test on the customer-facing endpoint."
)


async def main():
    narrate.step_header(
        10, "The whole desk",
        adds="Nothing new. That is the point. This is the architecture from the first "
             "slide, running end to end: three agents reached over A2A - one owned by "
             "another team - and two agents in your own process, because they did not "
             "need a network hop.",
        watch_for="The shape of it. Which agents got A2A and which stayed in-process "
                  "IS the architecture. The code is almost incidental.",
    )

    narrate.event("prerequisite", "steps 2, 4 and 7 must be running on ports 9001/9002/9003")
    narrate.event("gathering", "three A2A calls, concurrently")

    signal, cases, baseline = await asyncio.gather(
        ask_a2a(URL_SIGNAL, WEEK_Q, "desk-signal", verbose=False),
        ask_a2a(URL_CASES, WEEK_Q, "desk-cases", verbose=False),
        ask_a2a(URL_COE, COE_Q, "desk-coe", verbose=False),
    )

    narrate.turn("Signal", signal, "remote, over A2A — port 9001")
    narrate.turn("CaseReview", cases, "remote, over A2A — port 9002")
    narrate.turn("CoE Baseline Advisor", baseline,
                 "ANOTHER TEAM's Foundry project — port 9003")

    findings = (
        "FINDINGS for CUSTOMER-A (gathered over A2A):\n\n"
        f"[Monitoring signal]\n{signal}\n\n"
        f"[Open cases]\n{cases}\n\n"
        f"[CoE recommended baseline]\n{baseline}"
    )

    narrate.event("writing and gating", "in-process group chat, no HTTP hop")

    desk = build_desk(get_client())
    workflow = build_group_chat([desk["reporter"], desk["redactor"]], max_iterations=6)
    await run_workflow(
        workflow,
        "Write the weekly service review pack for CUSTOMER-A from these findings, then "
        "revise until the Redactor approves.\n\n" + findings,
    )

    narrate.takeaway(
        "You just replaced a few hours of manual work across four disconnected systems "
        "with one run - and every figure is traceable to the agent that found it.",
        "Three agents were remote because they belonged elsewhere. Two were local "
        "because they did not. THAT decision was the architecture.",
        "The Redactor ran on the OUTBOUND path. Nothing left the desk unchecked.",
    )

    narrate.ask(
        "Where should the Redactor have run relative to the A2A calls - before, after, "
        "or both?",
        "Which of these five agents could you delete tomorrow without the pack getting "
        "worse? That question is the whole discipline of multi-agent design.",
    )


if __name__ == "__main__":
    asyncio.run(main())
```

### Run it

```bash
# All three servers must be running, each in its own terminal:
python src/step2_signal_a2a_server.py    # port 9001
python src/step4_case_a2a_server.py      # port 9002
python src/step7_coe_a2a_server.py       # port 9003

# then, in a fourth terminal:
python src/step10_full_desk.py
```

### What you should see

Three gathered findings printed under `SIGNAL`, `CASES` and `CoE BASELINE`, then
the group chat writing and gating the weekly review pack until the Redactor approves it.

### Check your understanding

- You just sent findings across a team boundary. Where should the Redactor have run — before the A2A calls, after them, or both? (**Outbound, before anything leaves.**)
- **Which of these agents could you delete tomorrow without the pack getting worse?** That question is the entire discipline of multi-agent design.
- Time the whole run and estimate the token cost. Would you defend that cost against one engineer doing it by hand? Under what volume does the answer change?

---

## Step 11 — Harden it

> **Adds:** The difference between a demo and an engagement.

This file is a **checklist in code**. Work down it against your own build.

Score yourself honestly: **anything unticked is a finding you would raise against a
customer's architecture — so raise it against your own first.**

### The code — `src/step11_hardening.py`

```python
"""STEP 11 - Hardening: what stands between step 10 and a real engagement.

This file is runnable, but it is mostly a CHECKLIST IN CODE. Work down it and implement
each item against your own build. Nothing here is optional for mission-critical work.

Run:  python src/step11_hardening.py
"""

CHECKLIST = [
    ("Identity",
     "Every agent gets its own Entra ID workload identity with scoped tokens. An agent is "
     "a new identity in your tenant - give it the same scrutiny as a service principal."),
    ("A2A trust",
     "Verify agent card signatures (v1.0 supports JSON Web Signature). Pin identities. "
     "Never resolve an arbitrary URL at runtime. Enforce a bearer token or mTLS - the "
     "protocol ADVERTISES auth schemes, it does not ENFORCE them."),
    ("Egress",
     "Know which agents yours may call, and what may leave with the request. Run the "
     "Redactor on the OUTBOUND path, before anything crosses a boundary."),
    ("Untrusted input",
     "Treat every remote agent's response as data, never as instructions. A returned "
     "artifact that says 'ignore your previous rules' is an attack, not a message."),
    ("Budgets",
     "Iteration caps on group chat. Hop budgets on handoff. Per-request token budget. "
     "Enforced in code, not hoped for in a prompt."),
    ("Model tiering",
     "Use a cheap model for routing agents (Intake) and an expensive one for reasoning "
     "agents. Routing is classification, not analysis."),
    ("Observability",
     "One OpenTelemetry span per agent turn, with the routing reason as an attribute, "
     "exported to Application Insights. Without this a multi-agent bug is unfixable - you "
     "cannot reconstruct a conversation from logs."),
    ("Checkpointing",
     "Long workflows must resume, not restart. Checkpoint after each expensive stage."),
    ("Human in the loop",
     "Tool approval on anything irreversible or customer-facing. The agent proposes, the "
     "human commits. Keep the human handoff target in the graph."),
    ("Evaluation",
     "An eval set of at least 10 inputs with expected routing and expected redaction "
     "outcomes. Multi-agent regressions are otherwise invisible: a prompt change in the "
     "Redactor can quietly break the Reporter."),
    ("Data handling",
     "Real engagement data only in an approved, access-controlled environment. Synthetic "
     "fixtures everywhere else. Never in this repo."),
]


def main():
    print("\nSTEP 11 - PRODUCTION HARDENING CHECKLIST\n" + "=" * 60)
    for i, (area, detail) in enumerate(CHECKLIST, 1):
        print(f"\n[ ] {i:2}. {area}\n       {detail}")
    print("\n" + "=" * 60)
    print("Score yourself honestly. Anything unticked is a finding you would raise")
    print("against a customer's architecture - so raise it against your own first.\n")


if __name__ == "__main__":
    main()
```

### Run it

```bash
python src/step11_hardening.py
```

### What you should see

An eleven-point checklist covering identity, A2A trust, egress, untrusted input, budgets, model tiering, observability, checkpointing, human-in-the-loop, evaluation and data handling.

### Check your understanding

- Which three items would you implement first for a real engagement, and why those three?
- Observability: can you reconstruct *why* Intake routed the way it did, from your traces alone? If not, you cannot debug this system at 2 a.m.
- Evaluation: write ten inputs with expected routing and expected redaction outcomes. Then worsen the Redactor prompt deliberately and confirm your eval set catches it.

---

## The decision framework

Ask these in order. Stop at the first one that answers.

1. **Does one agent with good tools already solve it?** → Do that. Multi-agent costs you
   latency, tokens, non-determinism and debuggability.
2. **Is the order known and fixed, each step depending on the last?** → **Sequential**
3. **Are the sub-tasks genuinely independent?** → **Concurrent** (+ an aggregator)
4. **Is it "classify, then send to the right specialist"?** → **Handoff** (+ a human target)
5. **Do agents need to critique and refine each other's work?** → **Group Chat**
   (+ an iteration cap)
6. **Is the solution path unknown up front?** → **Magentic** — a planning manager with a
   task ledger that replans as it learns
7. **Does the agent belong to another team, framework or cloud?** → **A2A**, on top of
   whichever of the above you picked

---

## Before any of this touches a real engagement

- [ ] Iteration caps and hop budgets on every loop
- [ ] Per-request token and cost budget, enforced in code
- [ ] OpenTelemetry span per agent turn, with the routing reason recorded
- [ ] Human-in-the-loop: tool approval on anything irreversible or customer-facing
- [ ] Checkpointing so a long workflow resumes instead of restarting
- [ ] Confidentiality gate on every outbound path, in-process and over A2A
- [ ] Agent outputs treated as untrusted input, never as instructions
- [ ] Agent cards verified, identities pinned, egress controlled
- [ ] An evaluation set — multi-agent regressions are otherwise invisible
- [ ] Real customer data only in an approved, access-controlled environment. Never in this repo.

---

## Reference material

- A2A protocol — <https://a2a-protocol.org/latest/>
- A2A source and SDKs — <https://github.com/a2aproject/A2A>
- Agent Framework orchestrations — <https://learn.microsoft.com/en-us/agent-framework/workflows/orchestrations/>
- Agent Framework Python samples — <https://github.com/microsoft/agent-framework/tree/main/python/samples/03-workflows/orchestrations>

---

> **The hard part of multi-agent systems is not making agents talk.
> It is deciding which agent should not exist.**
