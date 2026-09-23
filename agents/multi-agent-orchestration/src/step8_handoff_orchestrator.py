"""STEP 8 - Handoff: Intake routes a live incident, dynamically."""

import asyncio

import narrate
from common import LIVE_INCIDENT, build_desk, build_handoff, get_client, run_workflow

MAX_HOPS = 4


async def main():
    narrate.step_header(
        8, "Handoff — the model does the routing",
        adds="The top box on the diagram: the orchestrator, and the 'dynamic hand-off' "
             "arrow. There is NO orchestrator object in this code. Intake is a "
             "participant that happens to hold the conversation, and when it decides a "
             "specialist should own the work it CALLS A TOOL - handoff_to_<target>. "
             "The routing decision is made by the model, inside the agent.",
        watch_for="The handoff_to_<target> tool call, and Intake's stated REASON. Also "
                  "note the TCL escalation queue in the graph: some decisions are not "
                  "the agent's to make, and you express that as an edge to a human.",
    )

    narrate.event("the incident", "public endpoint failing ~1 request in 10; on-call "
                                  "wants to know within the hour where this belongs")

    desk = build_desk(get_client())
    workflow = build_handoff(
        coordinator=desk["intake"],
        specialists=[desk["signal"], desk["resilience"], desk["cases"]],
        human_target=desk["tcl_queue"],
    )

    transcript = await run_workflow(workflow, LIVE_INCIDENT)
    hops = transcript.count("handoff_to")

    narrate.event("handoffs observed", f"{hops}  (budget {MAX_HOPS})")
    if hops > MAX_HOPS:
        narrate.event("HOP BUDGET EXCEEDED",
                      "in production this is where you escalate to a human, not retry")

    narrate.takeaway(
        "DECENTRALISED. You defined what routing is POSSIBLE; the model decided what "
        "actually happened. Compare group chat, where a central orchestrator picks.",
        "This builder made three demands, and each is a design lesson: every agent "
        "needs history persistence (a handoff is a tool call that short-circuits the "
        "turn), you must name a START agent, and you must declare the GRAPH.",
        "Handoff is the only built-in pattern INTERACTIVE BY DEFAULT - it pauses for "
        "the user between turns. Right for a support conversation. At 2 a.m., maybe a "
        "latency bug.",
        "Ping-pong is the number-one handoff failure in production. That is what the "
        "hop budget is for.",
    )

    narrate.ask(
        "Does Intake's stated reason hold up, or did it route on a keyword?",
        "Which of these agents should never trigger a customer-facing action without a "
        "human in between - and how would you ENFORCE that rather than instruct it?",
    )


if __name__ == "__main__":
    asyncio.run(main())
