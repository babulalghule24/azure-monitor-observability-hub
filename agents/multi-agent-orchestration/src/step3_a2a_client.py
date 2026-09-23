"""STEP 3 - Call the Signal agent over A2A. Discover, delegate, observe."""

import asyncio

import narrate
from common import URL_SIGNAL, ask_a2a

QUESTION = (
    "For the current review week: which alert rules are noise rather than signal, which "
    "correlate with an incident window, and what monitoring coverage is missing?"
)


async def main():
    narrate.step_header(
        3, "Call it from an A2A client",
        adds="The first arrow on the diagram. You are now a CLIENT of a remote agent - "
             "one you did not build, running in a process you do not control.",
        watch_for="Three moves, and they are the entire protocol. DISCOVER the agent "
                  "card and decide whether to trust it. DELEGATE by sending a message. "
                  "OBSERVE what comes back. Also notice what you CANNOT see.",
    )

    narrate.event("step 1", "DISCOVER - fetch the agent card")
    text = await ask_a2a(URL_SIGNAL, QUESTION, message_id="step-3-001", verbose=False)

    narrate.event("step 2", "DELEGATE - send a Message; the remote agent does the work")
    narrate.event("step 3", "OBSERVE - read what comes back")

    narrate.turn("Signal (remote, over A2A)", text,
                 "same agent as step 1 - but you reached it over HTTP")

    narrate.takeaway(
        "You never saw the remote agent's instructions, its tool, its model deployment "
        "or its data. That OPACITY is not a limitation - it is the feature that makes "
        "A2A safe across an organisational boundary.",
        "For short synchronous work the agent replies with a Message. For long-running "
        "work it opens a TASK with a lifecycle - submitted, working, input_required, "
        "completed / failed / canceled - and streams status or calls you back on a "
        "webhook. Same protocol, two shapes.",
        "Note input_required in that lifecycle. The protocol has a built-in notion of "
        "'I need to ask a human something'. That is not an afterthought.",
    )

    narrate.ask(
        "Kill the server and re-run this. What comes back, and did your code handle it? "
        "failed and canceled are states you must code for, not just completed.",
        "What would you have to strip from a real engagement's context before sending "
        "it across this boundary?",
    )


if __name__ == "__main__":
    asyncio.run(main())
