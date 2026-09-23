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
