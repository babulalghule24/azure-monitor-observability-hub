"""STEP 3 - Call the Signal agent from an A2A client. Discover, delegate, observe.

WHAT THIS ADDS: the first arrow on the diagram. You are now a client of a remote agent.

Make sure step 2 is running first, then:
    python src/step3_a2a_client.py
"""

import asyncio

from common import URL_SIGNAL, ask_a2a

QUESTION = (
    "For the current review week: which alert rules are noise rather than signal, which "
    "correlate with an incident window, and what monitoring coverage is missing?"
)


async def main():
    await ask_a2a(URL_SIGNAL, QUESTION, message_id="step-3-001")


if __name__ == "__main__":
    asyncio.run(main())

# THE THREE MOVES, AND YOU WILL SEE ALL THREE IN THE OUTPUT
# 1. DISCOVER - fetch the agent card. Decide whether to trust it.
# 2. DELEGATE - send a Message. The remote agent opens a Task.
# 3. OBSERVE  - the Task moves through its lifecycle:
#               submitted -> working -> input_required -> completed / failed / canceled
#               and finally emits Artifacts.
#
# NOTICE WHAT YOU CANNOT SEE
# You never saw the remote agent's instructions, its tool, its model deployment or its
# data. That opacity is not a limitation - it is the feature that makes A2A safe across
# an organisational boundary.
#
# CHECK YOUR UNDERSTANDING
# * Find the task state transitions in the output. Which state would a long-running
#   research task sit in for minutes, and how would you get told when it finished?
# * Kill the server and re-run this. What state do you get, and did your code handle it?
