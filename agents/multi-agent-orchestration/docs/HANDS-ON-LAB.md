# Hands-On Lab — Build the SfMC Mission-Critical Operations Desk

**A complete, self-contained walkthrough.** Every step below carries its narrative, the
full source code, what to run, what you should see, and questions to check your
understanding. If you only read one file in this repo, read this one.

Platform: **Microsoft Foundry (Azure AI Foundry) + Python + Microsoft Agent Framework + A2A**
Level: **400** · Time: **25 minutes live, ~90 minutes at your own pace**

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

```bash
git clone https://github.com/<your-github-handle>/multi-agent-orchestration-l400.git
cd multi-agent-orchestration-l400

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

API note: the framework ships fast. If an import or builder name has drifted, match your
installed version against the official Python samples:
https://github.com/microsoft/agent-framework/tree/main/python/samples/03-workflows/orchestrations
"""

import json
import os
from pathlib import Path
from typing import Annotated

from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
from pydantic import Field

from agent_framework.azure import AzureAIAgentClient

load_dotenv()

DATA = Path(__file__).resolve().parent.parent / "data"


# =====================================================================================
# 1. The Foundry client - where every agent in this repo actually runs
# =====================================================================================

def get_client() -> AzureAIAgentClient:
    """Agents run in a Microsoft Foundry project. Auth is Entra ID - no keys, ever."""
    return AzureAIAgentClient(
        project_endpoint=os.environ["AZURE_AI_PROJECT_ENDPOINT"],
        model_deployment_name=os.environ.get("AZURE_AI_MODEL_DEPLOYMENT_NAME", "gpt-4o-mini"),
        async_credential=DefaultAzureCredential(),
    )


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


def make(client, name: str, instructions: str, tools=None):
    """One-liner so every step file reads the same way."""
    return client.create_agent(name=name, instructions=instructions, tools=tools or [])


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


def serve(agent, card, host: str, port: int):
    """Wrap any agent in an A2A server and run it. This is the whole 'become callable' step."""
    import uvicorn
    from a2a.server.apps import A2AStarletteApplication

    app = A2AStarletteApplication(agent_card=card, agent=agent)
    print(f"\nServing '{card.name}' at http://{host}:{port}")
    print(f"Agent card: http://{host}:{port}/.well-known/agent-card.json\n")
    uvicorn.run(app.build(), host=host, port=port)


async def ask_a2a(base_url: str, question: str, message_id: str = "sfmc-001", verbose: bool = True):
    """Discover -> delegate -> observe. The three moves of every A2A call."""
    import httpx
    from a2a.client import A2ACardResolver, ClientFactory
    from a2a.types import Message, Part, Role, TextPart

    async with httpx.AsyncClient(timeout=90) as http:
        card = await A2ACardResolver(http, base_url).get_agent_card()      # 1. DISCOVER
        if verbose:
            print(f"Discovered : {card.name} v{card.version}")
            print(f"Skills     : {[s.id for s in card.skills]}")
            print(f"Streaming  : {card.capabilities.streaming}")

        client = ClientFactory(httpx_client=http).create(card)             # 2. DELEGATE
        message = Message(
            role=Role.user, message_id=message_id,
            parts=[Part(root=TextPart(text=question))],
        )

        out = []
        async for event in client.send_message(message):                   # 3. OBSERVE
            if verbose:
                print(event)
            out.append(str(event))
        return "\n".join(out)


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
"""STEP 1 - A plain agent on Foundry. No protocol, no orchestration, nothing clever.

WHAT THIS ADDS: the first box on our architecture diagram - one working specialist.
WHAT IT DOES NOT HAVE YET: any way for another agent to call it.

This is deliberately the smallest thing that works. If you cannot get this to run, none
of the later steps will, so fix it here.

Run:  python src/step1_signal_agent.py
"""

import asyncio

from common import SIGNAL, get_client, get_monitor_signals, make

QUESTION = (
    "For FY27-W12 on CUSTOMER-A: which alerts are real signal and which are noise, "
    "and what monitoring coverage is missing?"
)


async def main():
    client = get_client()

    # One agent. One tool. That is the entire Foundry surface area you need today.
    signal = make(client, "Signal", SIGNAL, [get_monitor_signals])

    result = await signal.run(QUESTION)
    print(result)


if __name__ == "__main__":
    asyncio.run(main())

# WHAT JUST HAPPENED
# 1. You authenticated to a Foundry project with Entra ID - no key anywhere.
# 2. The model called your get_monitor_signals tool because its description said it could.
# 3. It read synthetic alert data and separated signal from noise.
#
# CHECK YOUR UNDERSTANDING
# * The agent found AKS-NodePool-CPU-High firing 228 times. Did it call that signal or
#   noise, and did it say WHY? An agent that cannot justify a conclusion is not usable
#   in mission-critical support.
# * Nothing here is multi-agent yet. Ask yourself honestly: for this one question, would
#   a second agent have made the answer better?
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
"""STEP 2 - Wrap the Signal agent into an A2A server. It gets an agent card.

WHAT THIS ADDS: the agent becomes CALLABLE by anyone who speaks A2A - a different
framework, a different team, a different cloud. Nothing about the agent itself changed.

This is the single most important idea in the protocol: A2A does not change how you build
an agent. It changes who can reach it.

Run in its own terminal and LEAVE IT RUNNING:
    python src/step2_signal_a2a_server.py

Then, in another terminal, look at what you just published:
    curl http://127.0.0.1:9001/.well-known/agent-card.json
"""

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
    agent = make(get_client(), "Signal", SIGNAL, [get_monitor_signals])
    serve(agent, card, HOST, PORT_SIGNAL)


if __name__ == "__main__":
    main()

# READ THE AGENT CARD BEFORE YOU MOVE ON
# It advertises: name, version, the skills you offer, whether you stream, what input and
# output types you take, and which authentication schemes you accept. This is how a
# caller decides whether to delegate to you AT ALL. It is a contract, not documentation.
#
# CHECK YOUR UNDERSTANDING
# * Your agent's instructions, your tool, and your Foundry project are NOT in that card.
#   Why is that the point?
# * The card lists auth schemes. Nothing in the protocol enforces them. Who does?
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
"""STEP 3 - Call the Signal agent from an A2A client. Discover, delegate, observe.

WHAT THIS ADDS: the first arrow on the diagram. You are now a client of a remote agent.

Make sure step 2 is running first, then:
    python src/step3_a2a_client.py
"""

import asyncio

from common import URL_SIGNAL, ask_a2a

QUESTION = (
    "For the current review week: which alert rules are noise rather than signal, which "
    "correlate with an incident window, and what monitoring coverage is missing?"
)


async def main():
    await ask_a2a(URL_SIGNAL, QUESTION, message_id="step-3-001")


if __name__ == "__main__":
    asyncio.run(main())

# THE THREE MOVES, AND YOU WILL SEE ALL THREE IN THE OUTPUT
# 1. DISCOVER - fetch the agent card. Decide whether to trust it.
# 2. DELEGATE - send a Message. The remote agent opens a Task.
# 3. OBSERVE  - the Task moves through its lifecycle:
#               submitted -> working -> input_required -> completed / failed / canceled
#               and finally emits Artifacts.
#
# NOTICE WHAT YOU CANNOT SEE
# You never saw the remote agent's instructions, its tool, its model deployment or its
# data. That opacity is not a limitation - it is the feature that makes A2A safe across
# an organisational boundary.
#
# CHECK YOUR UNDERSTANDING
# * Find the task state transitions in the output. Which state would a long-running
#   research task sit in for minutes, and how would you get told when it finished?
# * Kill the server and re-run this. What state do you get, and did your code handle it?
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
"""STEP 4 - A second A2A server: the CaseReview agent.

WHAT THIS ADDS: the second bottom box on the diagram. Two independent specialists, each
reachable over the protocol, neither knowing the other exists.

This is where a multi-agent SYSTEM starts, and notice how little ceremony it took: a new
agent, a new card, a new port.

Run in its own terminal and LEAVE IT RUNNING:
    python src/step4_case_a2a_server.py

Sanity check from anywhere:
    curl http://127.0.0.1:9002/.well-known/agent-card.json
"""

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
    agent = make(get_client(), "CaseReview", CASE_REVIEW, [get_open_cases])
    serve(agent, card, HOST, PORT_CASES)


if __name__ == "__main__":
    main()

# CHECK YOUR UNDERSTANDING
# * Both servers now run on your laptop. In production, who owns each one - the same team?
#   Different teams? If the same team owns both, should they have been A2A at all?
# * Rule of thumb to hold onto: agents-as-tools inside a crew, A2A between crews.
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
"""STEP 5 - Sequential: findings -> Reporter -> Redactor.

WHAT THIS ADDS: the first ORCHESTRATION pattern, and the in-process side box on the
diagram. Note these two agents are NOT A2A - they are in the same process, so putting
HTTP between them would cost latency and buy nothing.

Sequential is a pipeline: fixed order, you wrote the order, each agent consumes what the
previous one produced. Here, order is the whole point. The Reporter cannot write before
the findings exist, and nothing leaves the desk before the Redactor has seen it.

Run:  python src/step5_sequential_report.py
"""

import asyncio

from agent_framework.orchestrations import SequentialBuilder

from common import build_desk, get_client

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
    desk = build_desk(get_client())

    workflow = (
        SequentialBuilder()
        .participants([desk["reporter"], desk["redactor"]])
        .build()
    )

    async for event in workflow.run_stream(FINDINGS):
        print(event)


if __name__ == "__main__":
    asyncio.run(main())

# CHECK YOUR UNDERSTANDING
# * By default each agent sees the WHOLE conversation, not just the last message. Good
#   here - the Redactor must check the draft against the original findings. For a pure
#   transform stage, SequentialBuilder offers chain_only_agent_responses=True. When would
#   you want that, and what does it save?
# * Try breaking the gate: add "contact is Jane Doe, jane@example.com" to FINDINGS and
#   re-run. The Redactor MUST refuse. If it does not, your gate is decorative - and you
#   have just learned that a prompt alone is not a control.
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
"""STEP 6 - Concurrent: three specialists read the same week at once.

WHAT THIS ADDS: fan-out / fan-in. Signal, Resilience and CaseReview each read a different
source. None needs another's output, so running them one at a time is wasted latency.

This is the honest case for "parallel". Most people reach for concurrent when they should
not - so learn the test: if agent B should read agent A's answer, this is the wrong pattern.

Run:  python src/step6_concurrent_gather.py
"""

import asyncio

from agent_framework.orchestrations import ConcurrentBuilder

from common import THIS_WEEK, build_desk, get_client


async def main():
    desk = build_desk(get_client())

    workflow = (
        ConcurrentBuilder()
        .participants([desk["signal"], desk["resilience"], desk["cases"]])
        .build()
    )

    async for event in workflow.run_stream(THIS_WEEK):
        print(event)


if __name__ == "__main__":
    asyncio.run(main())

# CHECK YOUR UNDERSTANDING
# * Nobody merged the three answers. The default aggregator returns one message per
#   participant. Who should merge - a custom aggregator, or the Reporter in step 5?
# * What do you do when Signal and Resilience contradict each other? Decide that now,
#   not in production.
# * Stretch: add the Reporter as a fourth concurrent participant and watch it write a
#   service review based on nothing. That failure IS the lesson.
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
"""STEP 7 - The third A2A server: another team's agent, in another Foundry project.

WHAT THIS ADDS: the reason A2A exists at all.

Steps 2 and 4 served agents you own. This one is different in kind. The SfMC Monitoring &
Observability CoE owns the alert baseline for each Azure service. Your desk needs to ask
it a question. You must not need a copy of their prompts; they must not need access to
your engagement's data. Different team, different Foundry project, different data boundary.

Run in its own terminal and LEAVE IT RUNNING:
    python src/step7_coe_a2a_server.py

Then ask it something, from step 3's client pattern or directly:
    python -c "import asyncio,sys; sys.path.insert(0,'src'); from common import URL_COE, ask_a2a; \
asyncio.run(ask_a2a(URL_COE, 'Baseline for a public API tier behind Front Door with AKS compute?'))"
"""

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
    agent = make(get_client(), "CoEBaselineAdvisor", COE_BASELINE)
    serve(agent, card, HOST, PORT_COE)


if __name__ == "__main__":
    main()

# CHECK YOUR UNDERSTANDING
# * Look at the question you send this agent in step 10. It contains no customer name, no
#   subscription ID, no case URL. Crossing a team boundary is exactly where
#   de-identification stops being a lab rule and becomes a control.
# * In production this agent would be in a different tenant boundary with its own identity.
#   What do you need on the wire before you would call it with real context? (Bearer token
#   enforced, card signature verified, identity pinned, egress policy, Redactor outbound.)
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
"""STEP 8 - Handoff: Intake routes a live incident, dynamically.

WHAT THIS ADDS: the top box on the diagram - the orchestrator - and the "dynamic hand-off
of tasks to specialist agents" arrow.

There is NO orchestrator object here. Read that again. Intake is a participant that
happens to hold the conversation, and when it decides a specialist should own the work it
calls a generated tool - handoff_to_<target>. The routing decision is made by the model,
inside the agent, not by code you wrote. That is what "decentralised" means.

The most important line in this file is tcl_queue. In mission-critical support, some
decisions are not the agent's to make: severity calls, customer commitments, anything
contractual. The way you express that in a handoff architecture is a handoff target that
is a human queue, not an agent. Design it in on day one.

Run:  python src/step8_handoff_orchestrator.py
"""

import asyncio

from agent_framework.orchestrations import HandoffBuilder

from common import LIVE_INCIDENT, build_desk, get_client

MAX_HOPS = 4   # hop budget. Without it, two agents can hand back and forth forever.


async def main():
    desk = build_desk(get_client())

    workflow = (
        HandoffBuilder(participants=[
            desk["intake"], desk["signal"], desk["resilience"],
            desk["cases"], desk["tcl_queue"],
        ])
        .set_coordinator(desk["intake"])
        .add_handoff(desk["intake"], [desk["signal"], desk["resilience"],
                                      desk["cases"], desk["tcl_queue"]])
        .add_handoff(desk["signal"], [desk["cases"], desk["tcl_queue"]])
        .add_handoff(desk["resilience"], [desk["intake"], desk["tcl_queue"]])
        .add_handoff(desk["cases"], [desk["signal"], desk["tcl_queue"]])
        .build()
    )

    hops = 0
    async for event in workflow.run_stream(LIVE_INCIDENT):
        print(event)
        if "handoff_to" in str(event):
            hops += 1
            if hops > MAX_HOPS:
                print(f"\n!! hop budget of {MAX_HOPS} exceeded - stopping. In production "
                      "this is where you escalate to a human, not retry.")
                break


if __name__ == "__main__":
    asyncio.run(main())

# CHECK YOUR UNDERSTANDING
# * Find the handoff_to_<target> tool call in the stream. Does Intake's stated reason hold
#   up, or did it route on a keyword?
# * Handoff is the only built-in pattern that is INTERACTIVE BY DEFAULT - it pauses for
#   the user between turns. For a support conversation that is right. For a 2 a.m.
#   incident, is it?
# * Stretch: make two specialists hand back unconditionally and watch the hop budget catch
#   the ping-pong. This is the number-one handoff failure in production.
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
"""STEP 9 - Group Chat: Reporter and Redactor refine until APPROVED.

WHAT THIS ADDS: iterative refinement, and the difference between centralised and
decentralised coordination.

Star topology. An orchestrator sits in the middle and decides who speaks next, and every
participant sees the full shared conversation - which is exactly what lets the Reporter
act on the Redactor's corrections.

One line to remember:
    GROUP CHAT is centralised - an orchestrator picks the speaker.
    HANDOFF    is decentralised - the current agent picks, by calling a tool.

Run:  python src/step9_group_chat.py
"""

import asyncio

from agent_framework.orchestrations import GroupChatBuilder

from common import build_desk, get_client
from step5_sequential_report import FINDINGS

TASK = (
    "Write the FY27-W12 service review summary for CUSTOMER-A from these findings, then "
    "revise it until the Redactor approves it.\n\n" + FINDINGS
)


async def main():
    desk = build_desk(get_client())

    workflow = (
        GroupChatBuilder()
        .participants([desk["reporter"], desk["redactor"]])
        .set_round_robin_manager(max_iterations=6)     # hard stop. This is a budget.
        .build()
    )

    async for event in workflow.run_stream(TASK):
        print(event)


if __name__ == "__main__":
    asyncio.run(main())

# CHECK YOUR UNDERSTANDING
# * Re-run with max_iterations=2. The loop stops mid-refinement. An uncapped group chat is
#   an uncapped bill - that number is a budget decision, not a tuning knob.
# * Round-robin wastes a turn after APPROVED. Write a selection function that terminates
#   on APPROVED and watch the token cost roughly halve.
# * The Redactor is a PARTICIPANT WITH A VETO, not a filter bolted on at the end. Why does
#   that placement matter for a mission-critical engagement?
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
"""STEP 10 - Assemble the whole thing and produce the weekly review pack.

WHAT THIS ADDS: nothing new. That is the point. This is the architecture diagram from the
first slide, running end to end:

    Orchestrator (this process, Foundry project A)
      |-- A2A client  ->  Signal Agent        (A2A server, step 2, port 9001)
      |-- A2A client  ->  CaseReview Agent    (A2A server, step 4, port 9002)
      |-- A2A client  ->  CoE Baseline Advisor(A2A server, step 7, port 9003, other team)
      `-- in-process  ->  Reporter + Redactor (Group Chat, step 9, no HTTP hop)

BEFORE YOU RUN THIS, start all three servers, each in its own terminal:
    python src/step2_signal_a2a_server.py
    python src/step4_case_a2a_server.py
    python src/step7_coe_a2a_server.py

Then:
    python src/step10_full_desk.py
"""

import asyncio

from agent_framework.orchestrations import GroupChatBuilder

from common import (
    URL_CASES, URL_COE, URL_SIGNAL,
    ask_a2a, build_desk, get_client,
)

WEEK_Q = (
    "For the current review week on CUSTOMER-A: intermittent 5xx on the public endpoint "
    "since Tuesday, backend latency up, no deployment, log ingestion cost rising. "
    "Report what you see from your source."
)

# Deliberately de-identified: nothing here names a customer, a subscription or a person.
COE_Q = (
    "For a mission-critical public API tier behind Front Door with an AKS compute tier: "
    "what alert baseline should be in place, which signals should use dynamic thresholds "
    "instead of static ones, and what availability testing is expected? Context: static "
    "70% node CPU alerting produces ~228 firings a week and there is no synthetic "
    "availability test on the customer-facing endpoint."
)


async def main():
    # --- Gather: three remote agents over A2A, concurrently -------------------------
    print("=== GATHERING FROM THREE A2A AGENTS ===\n")
    signal, cases, baseline = await asyncio.gather(
        ask_a2a(URL_SIGNAL, WEEK_Q, "desk-signal", verbose=False),
        ask_a2a(URL_CASES, WEEK_Q, "desk-cases", verbose=False),
        ask_a2a(URL_COE, COE_Q, "desk-coe", verbose=False),
    )
    for label, text in (("SIGNAL", signal), ("CASES", cases), ("CoE BASELINE", baseline)):
        print(f"\n--- {label} ---\n{text[:1200]}")

    findings = (
        "FINDINGS for CUSTOMER-A (gathered over A2A):\n\n"
        f"[Monitoring signal]\n{signal}\n\n"
        f"[Open cases]\n{cases}\n\n"
        f"[CoE recommended baseline]\n{baseline}"
    )

    # --- Write and gate: in-process group chat, until APPROVED ----------------------
    print("\n\n=== WRITING AND GATING THE REVIEW PACK ===\n")
    desk = build_desk(get_client())
    workflow = (
        GroupChatBuilder()
        .participants([desk["reporter"], desk["redactor"]])
        .set_round_robin_manager(max_iterations=6)
        .build()
    )

    async for event in workflow.run_stream(
        "Write the weekly service review pack for CUSTOMER-A from these findings, then "
        "revise until the Redactor approves.\n\n" + findings
    ):
        print(event)


if __name__ == "__main__":
    asyncio.run(main())

# LOOK AT WHAT YOU BUILT
# * Three agents you reach over an open protocol - one of them owned by another team - and
#   two agents in your own process, because they did not need a network hop.
# * The decision about WHICH agents got A2A and which stayed in-process is the actual
#   architecture. The code is almost incidental.
#
# CHECK YOUR UNDERSTANDING
# * You just sent findings across a team boundary. Where should the Redactor have run -
#   before the A2A calls, after them, or both? (Answer: outbound, before anything leaves.)
# * Which of these five agents could you delete tomorrow without the pack getting worse?
#   That question is the whole discipline of multi-agent design.
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
