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
