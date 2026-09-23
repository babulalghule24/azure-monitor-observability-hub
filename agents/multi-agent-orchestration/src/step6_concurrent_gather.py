"""STEP 6 - Concurrent: three specialists read the same week at once."""

import asyncio

import narrate
from common import THIS_WEEK, build_concurrent, build_desk, get_client, run_workflow


async def main():
    narrate.step_header(
        6, "Concurrent — three specialists, one week, at once",
        adds="Fan-out / fan-in, and the test for when 'parallel' is honest. Signal "
             "reads the alerts, Resilience reads the assessment risks, CaseReview reads "
             "the open cases. Three different sources, and none of them needs another's "
             "output - so running them one at a time is pure wasted latency.",
        watch_for="Three independent answers, with NO ordering and NO shared "
                  "refinement. Nobody merges them. That is the design decision this "
                  "pattern hands back to you.",
    )

    desk = build_desk(get_client())
    workflow = build_concurrent([desk["signal"], desk["resilience"], desk["cases"]])
    await run_workflow(workflow, THIS_WEEK)

    narrate.takeaway(
        "THE TEST, in one sentence: if agent B should read agent A's answer, this is "
        "the wrong pattern. Concurrent is the one people reach for and then regret, "
        "because 'parallel' sounds efficient.",
        "The default aggregator returns one message per participant. Somebody still has "
        "to merge them - a custom aggregator, or a summarising agent. That is a "
        "decision you make, not a default you inherit.",
        "Here it IS honest: three sources, three skills, no dependency between them.",
    )

    narrate.ask(
        "Signal and Resilience may disagree about the cause. Who reconciles them, and "
        "when do you decide that - now, or in production?",
        "Add the Reporter as a fourth concurrent participant and watch it write a "
        "service review based on nothing. That failure IS the lesson.",
    )


if __name__ == "__main__":
    asyncio.run(main())
