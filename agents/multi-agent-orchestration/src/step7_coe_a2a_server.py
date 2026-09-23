"""STEP 7 - The third A2A server: another team's agent, in another Foundry project.

WHAT THIS ADDS: the reason A2A exists at all.

Steps 2 and 4 served agents you own. This one is different in kind. The SfMC Monitoring &
Observability CoE owns the alert baseline for each Azure service. Your desk needs to ask
it a question. You must not need a copy of their prompts; they must not need access to
your engagement's data. Different team, different Foundry project, different data boundary.

Run in its own terminal and LEAVE IT RUNNING:
    python src/step7_coe_a2a_server.py

Then ask it something, from step 3's client pattern or directly:
    python -c "import asyncio,sys; sys.path.insert(0,'src'); from common import URL_COE, ask_a2a; \
asyncio.run(ask_a2a(URL_COE, 'Baseline for a public API tier behind Front Door with AKS compute?'))"
"""

from common import (
    COE_BASELINE, HOST, PORT_COE, URL_COE,
    agent_card, get_client, make, serve,
)

card = agent_card(
    name="sfmc-coe-baseline-advisor",
    description="SfMC Monitoring & Observability CoE alert-baseline guidance for Azure services.",
    skill_id="alert_baseline",
    skill_name="Recommend an alert baseline",
    skill_description="Returns the CoE-recommended alert baseline for an Azure service tier.",
    base_url=URL_COE,
    tags=["monitoring", "azure-monitor", "sfmc", "baseline", "coe"],
    examples=[
        "What is the recommended alert baseline for a public API tier behind Front Door?",
        "Should node CPU use a static threshold or a dynamic baseline?",
    ],
)


def main():
    agent = make(get_client(), "CoEBaselineAdvisor", COE_BASELINE)
    serve(agent, card, HOST, PORT_COE)


if __name__ == "__main__":
    main()

# CHECK YOUR UNDERSTANDING
# * Look at the question you send this agent in step 10. It contains no customer name, no
#   subscription ID, no case URL. Crossing a team boundary is exactly where
#   de-identification stops being a lab rule and becomes a control.
# * In production this agent would be in a different tenant boundary with its own identity.
#   What do you need on the wire before you would call it with real context? (Bearer token
#   enforced, card signature verified, identity pinned, egress policy, Redactor outbound.)
