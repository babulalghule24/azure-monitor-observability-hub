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
