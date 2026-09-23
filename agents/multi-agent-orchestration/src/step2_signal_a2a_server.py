"""STEP 2 - Wrap the Signal agent into an A2A server. It gets an agent card.

WHAT THIS ADDS: the agent becomes CALLABLE by anyone who speaks A2A - a different
framework, a different team, a different cloud. Nothing about the agent itself changed.

This is the single most important idea in the protocol: A2A does not change how you build
an agent. It changes who can reach it.

Run in its own terminal and LEAVE IT RUNNING:
    python src/step2_signal_a2a_server.py

Then, in another terminal, look at what you just published:
    curl http://127.0.0.1:9001/.well-known/agent-card.json
"""

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
    agent = make(get_client(), "Signal", SIGNAL, [get_monitor_signals])
    serve(agent, card, HOST, PORT_SIGNAL)


if __name__ == "__main__":
    main()

# READ THE AGENT CARD BEFORE YOU MOVE ON
# It advertises: name, version, the skills you offer, whether you stream, what input and
# output types you take, and which authentication schemes you accept. This is how a
# caller decides whether to delegate to you AT ALL. It is a contract, not documentation.
#
# CHECK YOUR UNDERSTANDING
# * Your agent's instructions, your tool, and your Foundry project are NOT in that card.
#   Why is that the point?
# * The card lists auth schemes. Nothing in the protocol enforces them. Who does?
