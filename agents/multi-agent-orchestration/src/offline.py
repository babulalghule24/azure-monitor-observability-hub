"""OFFLINE MODE - run the whole lab with no Azure, no Foundry, no credentials.

Set LAB_OFFLINE=1 and every agent is answered by a small scripted stand-in instead of
a model. Nothing is called over the network. It starts instantly and always works.

WHY THIS EXISTS
The point of this lab is the ORCHESTRATION - who speaks, in what order, who decides,
and where the boundaries are. None of that needs a live model to understand. So:

    LAB_OFFLINE=1   ->  learn the patterns in 30 seconds, on any laptop
    (unset)         ->  the same code against a real Foundry project

Same step files. Same builders. Same A2A servers and clients. Only the thing that
generates the words changes.
"""

import textwrap

# --- canned answers, keyed by agent name --------------------------------------------
# Written to be realistic enough that the ORCHESTRATION is what you notice.

_ANSWERS = {
    "Signal": """\
NOISE — AKS-NodePool-CPU-High. Fired 228 times this week on a static 70% threshold,
every 5 minutes. A rule that fires constantly is telling you about its threshold, not
about your workload. Fix: sustained duration, or a dynamic baseline.

SIGNAL — Frontdoor-5xx-RateSpike. Sev1, three firings, Tue 09:14–09:58 UTC. Tight,
bounded, and it stopped. That is an event.

SIGNAL — AppGateway-BackendLatency-P95. First fired Tue 09:12 UTC, two minutes BEFORE
the 5xx spike, and still active. Latency led the errors.

SIGNAL — SQL-DTU-Saturation. Tue 09:20–11:05 UTC. Overlaps both. The chain reads:
database saturates, gateway latency climbs, front door returns 5xx.

COVERAGE GAPS — no availability test on the public checkout endpoint; no alert on Key
Vault certificate expiry; backup failures are logged but never alerted.""",

    "Resilience": """\
RISK-03 (High, open 45 days) — no synthetic availability monitoring on the primary
customer-facing endpoint. This is why Tuesday was noticed late. The assessment
predicted this exact blind spot.

RISK-02 (Medium, open 60 days) — static-threshold alerting, no dynamic baselines.
Directly explains the 228 firings the Signal agent called noise.

RISK-01 (High, open 74 days) — single-region data tier, documented RTO never validated
by a failover test. Not implicated this week, but it is the one that ends badly.

RISK-04 (Medium, open 88 days) — certificate lifecycle unmonitored, manual renewal.

Two of this week's four findings were already on the risk register. The assessment was
right; the remediation is late.""",

    "CaseReview": """\
CASE-1001 — Sev A, 4 days, with the product group. The Tuesday 5xx errors. Active and
correctly escalated.

CASE-1003 — Sev B, 9 days, active. Log Analytics ingestion cost increase, cause
unclear. Matches LogIngestion-VolumeSpike.

CASE-1002 — Sev B, 12 days, awaiting customer data. Managed instance failover exceeded
documented RTO. Blocked on us, not on Microsoft.

CASE-0987 — Sev C, 31 days, STALLED. Diagnostic settings missing on two data services.
Low severity, but it is a monitoring gap that has sat for a month.""",

    "Reporter": """\
Health this week: DEGRADED — one Sev1 incident window, now resolved; two open risks
directly implicated.

What happened. On Tuesday between 09:12 and 11:05 UTC the platform saw a correlated
event: database saturation, then gateway latency, then 5xx errors on the public
endpoint. No deployment was involved.

What we believe the cause is. A load-driven database saturation propagating outward.
Two known, unmitigated risks made it worse: no synthetic availability test meant it was
detected late, and static-threshold alerting buried the signal in noise.

Recommended actions.
1. Add a synthetic availability test on the public endpoint — owner: CUSTOMER-A, this
   sprint. Closes RISK-03.
2. Move compute alerting to dynamic baselines — owner: joint, next 30 days. Closes
   RISK-02 and removes ~228 alerts/week of noise.
3. Complete the pending data for CASE-1002 so the failover investigation can proceed —
   owner: CUSTOMER-A, this week.

Needs a customer decision. RISK-01, the single-region data tier with an unvalidated
RTO, remains open at 74 days.""",

    "Redactor": "APPROVED",

    "Intake": """\
Routing to the Monitoring Signal agent.

Reason: the question asked is whether this is a monitoring gap, a known risk, or an
existing case — and the fastest discriminator is whether the alerts show a bounded
incident window or a coverage hole. Signal answers that first, and its answer
determines whether this needs Resilience or CaseReview next.

Not routing to the TCL escalation queue: no severity call or customer commitment is
being requested yet.

[tool call: handoff_to_Signal]""",

    "CoEBaselineAdvisor": """\
For a public API tier behind Front Door with an AKS compute tier, the CoE baseline is:

MUST ALERT — front-door 5xx rate, backend latency P95, origin health, certificate
expiry (30/14/7 day lead), and backup job failure.

DYNAMIC, NOT STATIC — node CPU and memory, request rate, and queue depth. Static
thresholds on elastic compute generate exactly the pattern you describe: ~228 firings
a week is a threshold problem, not a workload problem.

AVAILABILITY TESTING — a mission-critical public endpoint requires synthetic
availability tests from at least three regions at one-minute intervals, alerting on two
consecutive failures. Without it, detection depends on a customer complaining.

Note: any customer-identifying detail in your request was ignored.""",

    "TCL_Escalation": """\
FOR HUMAN TCL DECISION

Situation: public endpoint failing ~1 request in 10 for CUSTOMER-A. On-call needs a
determination within the hour.
Known: two unmitigated High risks (RISK-03 availability monitoring, RISK-01 single
region) and one active Sev A case (CASE-1001) with the product group.
Not yet determined: whether this is a recurrence of Tuesday's event.

Decision needed from you: severity call, and whether to invoke the customer
communication path. Neither is an agent's decision to make.""",
}

_DEFAULT = ("[offline mode] No scripted answer for this agent. The orchestration is "
            "what matters here - watch who speaks and in what order.")


class _OfflineResponse:
    def __init__(self, text: str):
        self.text = text
        self.messages = []

    def __str__(self) -> str:
        return self.text


class _OfflineAgent:
    """Stands in for a real agent. Same surface the workflows use: .name and .run()."""

    def __init__(self, name: str, instructions: str = "", tools=None):
        self.name = name
        self.instructions = instructions
        self.tools = tools or []
        self.display_name = name

    async def run(self, message, **kwargs):
        return _OfflineResponse(textwrap.dedent(_ANSWERS.get(self.name, _DEFAULT)).strip())

    # some builders probe for these
    async def run_stream(self, message, **kwargs):
        yield await self.run(message)

    def __repr__(self) -> str:
        return f"<OfflineAgent {self.name}>"


class OfflineClient:
    """Stands in for FoundryChatClient. No network, no credentials, no waiting."""

    def as_agent(self, name: str = "agent", instructions: str = "", tools=None, **kwargs):
        return _OfflineAgent(name, instructions, tools)

    # older SDK name
    create_agent = as_agent

    def __repr__(self) -> str:
        return "<OfflineClient — LAB_OFFLINE=1, no Azure calls>"
