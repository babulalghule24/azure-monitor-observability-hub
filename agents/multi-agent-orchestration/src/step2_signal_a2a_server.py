"""STEP 2 - Wrap the Signal agent into an A2A server. It gets an agent card."""

import narrate
from common import (
    HOST, PORT_SIGNAL, SIGNAL, URL_SIGNAL,
    agent_card, get_client, get_monitor_signals, make, serve,
)

card = agent_card(
    name="sfmc-signal-agent",
    description="Azure Monitor alert analysis for a mission-critical workload review week.",
    skill_id="analyse_alert_week",
    skill_name="Analyse a review week's alerts",
    skill_description="Separates real signal from alert noise and reports coverage gaps.",
    base_url=URL_SIGNAL,
    tags=["monitoring", "azure-monitor", "sfmc"],
    examples=["Which alerts in FY27-W12 are noise?", "What monitoring coverage is missing?"],
)


def main():
    narrate.step_header(
        2, "Wrap it into an A2A server",
        adds="An AGENT CARD. The agent becomes callable by anyone who speaks A2A - a "
             "different framework, a different team, a different cloud. Compare this "
             "file with step 1: the agent is IDENTICAL. Same instructions, same tool, "
             "same Foundry project. All we added is a card and a server.",
        watch_for="This is the single most important idea in the protocol: A2A does "
                  "not change how you BUILD an agent. It changes who can REACH it.",
    )

    narrate.event("next", f"fetch the card:  curl {URL_SIGNAL}/.well-known/agent-card.json")
    narrate.event("then", "in another terminal:  python src/step3_a2a_client.py")
    narrate.event("leave this running", "the server must stay up for steps 3 and 10")

    agent = make(get_client(), "Signal", SIGNAL, [get_monitor_signals])
    serve(agent, card, HOST, PORT_SIGNAL)


if __name__ == "__main__":
    main()

# READ THE AGENT CARD BEFORE YOU MOVE ON
# It advertises: name, version, the skills you offer, whether you stream, what input
# and output types you take, and which auth schemes you accept. This is how a caller
# decides whether to delegate to you AT ALL. It is a CONTRACT, not documentation.
#
# And notice what is NOT in it: your instructions, your tool, your Foundry project.
# That omission is the point.
