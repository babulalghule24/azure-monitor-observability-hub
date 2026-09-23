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
