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
