"""STEP 1 - A plain agent on Foundry. No protocol. No orchestration."""

import asyncio

import narrate
from common import SIGNAL, get_client, get_monitor_signals, make, sdk_flavour

QUESTION = (
    "For FY27-W12 on CUSTOMER-A: which alerts are real signal and which are noise, "
    "and what monitoring coverage is missing?"
)


async def main():
    narrate.step_header(
        1, "One agent, one tool",
        adds="The first box on our architecture diagram - a single working specialist. "
             "No protocol, no orchestration, nothing clever. This is deliberately the "
             "smallest thing that works: if this does not run, nothing later will.",
        watch_for="The agent reads a week of synthetic Azure Monitor data and separates "
                  "SIGNAL from NOISE. Watch whether it JUSTIFIES each call - an agent "
                  "that cannot say why is not usable in mission-critical support.",
    )

    narrate.event("SDK in use", sdk_flavour())
    narrate.event("the week", "CUSTOMER-A, FY27-W12 - 5xx errors since Tuesday, "
                              "latency up, no deployment")

    signal = make(get_client(), "Signal", SIGNAL, [get_monitor_signals])
    result = await signal.run(QUESTION)

    narrate.turn("Signal", str(result), "one agent, one tool, no orchestration")

    narrate.takeaway(
        "You authenticated to a Foundry project with Entra ID. There is no API key "
        "anywhere in this repo.",
        "The model chose to call get_monitor_signals because its DESCRIPTION said it "
        "could. Tool selection is a writing problem before it is a coding problem.",
        "Nothing here is multi-agent yet - and for this one question, it did not need "
        "to be. That is the discipline: add an agent only when you can name the "
        "expertise, the trust boundary, or the parallelism it buys you.",
    )

    narrate.ask(
        "AKS-NodePool-CPU-High fired 228 times. Did the agent call it noise, and did "
        "it say WHY?",
        "Would a second agent have made this particular answer better? Be honest.",
    )


if __name__ == "__main__":
    asyncio.run(main())
