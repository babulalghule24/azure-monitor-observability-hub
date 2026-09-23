"""STEP 7 - The third A2A server: another team's agent, another Foundry project."""

import narrate
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
    narrate.step_header(
        7, "The CoE Baseline Advisor — another team's agent",
        adds="The reason A2A exists at all. Steps 2 and 4 served agents YOU own. This "
             "one is different in kind: the Monitoring & Observability CoE owns the "
             "alert baseline for each Azure service. Your desk needs to ask it a "
             "question. You must not need a copy of their prompts; they must not need "
             "access to your engagement's data.",
        watch_for="Different team, different Foundry project, different data boundary. "
                  "THAT - not convenience, not modularity - is what justifies an HTTP "
                  "hop between two agents.",
    )

    narrate.event("defence in depth",
                  "this agent REFUSES customer-identifying data even if a caller sends "
                  "it - the caller redacts outbound, the callee refuses inbound")
    narrate.event("leave this running", "step 10 calls this agent")

    agent = make(get_client(), "CoEBaselineAdvisor", COE_BASELINE)
    serve(agent, card, HOST, PORT_COE)


if __name__ == "__main__":
    main()

# CHECK YOUR UNDERSTANDING
# * Look at the question step 10 sends here: no customer name, no subscription ID, no
#   case URL. Crossing a team boundary is where de-identification stops being a lab
#   rule and becomes a control.
# * What would you need on the wire before calling this with real context? Bearer token
#   enforced, card signature verified, identity pinned, egress policy, Redactor outbound.
