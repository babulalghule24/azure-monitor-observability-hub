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
