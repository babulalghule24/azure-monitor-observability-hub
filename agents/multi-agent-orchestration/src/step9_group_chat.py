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
