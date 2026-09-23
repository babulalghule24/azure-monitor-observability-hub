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
