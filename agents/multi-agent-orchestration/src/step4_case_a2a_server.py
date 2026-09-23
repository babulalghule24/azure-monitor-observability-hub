"""STEP 4 - A second A2A server: the CaseReview agent."""

import narrate
from common import (
    CASE_REVIEW, HOST, PORT_CASES, URL_CASES,
    agent_card, get_client, get_open_cases, make, serve,
)

card = agent_card(
    name="sfmc-case-review-agent",
    description="Open Microsoft support case review for a mission-critical workload.",
    skill_id="review_open_cases",
    skill_name="Review open support cases",
    skill_description="Summarises open cases by severity and age and flags stalled ones.",
    base_url=URL_CASES,
    tags=["support-cases", "sfmc", "service-review"],
    examples=["Which cases are stalled?", "What is open at Sev A and how old is it?"],
)


def main():
    narrate.step_header(
        4, "A second A2A server",
        adds="The second bottom box on the diagram. Two independent specialists, each "
             "reachable over the protocol, NEITHER knowing the other exists. This is "
             "where a multi-agent SYSTEM starts.",
        watch_for="How little ceremony that took: a new agent, a new card, a new port. "
                  "That cheapness is a trap as much as a feature - it makes it easy to "
                  "add agents you did not need.",
    )

    narrate.event("rule of thumb", "agents-as-tools inside a crew, A2A between crews")
    narrate.event("leave this running", "step 10 needs all three servers up")

    agent = make(get_client(), "CaseReview", CASE_REVIEW, [get_open_cases])
    serve(agent, card, HOST, PORT_CASES)


if __name__ == "__main__":
    main()

# CHECK YOUR UNDERSTANDING
# * In production, who owns each server? If the SAME team owns both, should they have
#   been A2A at all? Do not add an HTTP hop where a function call will do.
