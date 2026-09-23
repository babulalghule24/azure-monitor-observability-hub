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
