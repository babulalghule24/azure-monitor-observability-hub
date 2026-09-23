"""STEP 1 - A plain agent on Foundry. No protocol, no orchestration, nothing clever.

WHAT THIS ADDS: the first box on our architecture diagram - one working specialist.
WHAT IT DOES NOT HAVE YET: any way for another agent to call it.

This is deliberately the smallest thing that works. If you cannot get this to run, none
of the later steps will, so fix it here.

Run:  python src/step1_signal_agent.py
"""

import asyncio

from common import SIGNAL, get_client, get_monitor_signals, make

QUESTION = (
    "For FY27-W12 on CUSTOMER-A: which alerts are real signal and which are noise, "
    "and what monitoring coverage is missing?"
)


async def main():
    client = get_client()

    # One agent. One tool. That is the entire Foundry surface area you need today.
    signal = make(client, "Signal", SIGNAL, [get_monitor_signals])

    result = await signal.run(QUESTION)
    print(result)


if __name__ == "__main__":
    asyncio.run(main())

# WHAT JUST HAPPENED
# 1. You authenticated to a Foundry project with Entra ID - no key anywhere.
# 2. The model called your get_monitor_signals tool because its description said it could.
# 3. It read synthetic alert data and separated signal from noise.
#
# CHECK YOUR UNDERSTANDING
# * The agent found AKS-NodePool-CPU-High firing 228 times. Did it call that signal or
#   noise, and did it say WHY? An agent that cannot justify a conclusion is not usable
#   in mission-critical support.
# * Nothing here is multi-agent yet. Ask yourself honestly: for this one question, would
#   a second agent have made the answer better?
