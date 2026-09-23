"""STEP 4 - A second A2A server: the CaseReview agent.

WHAT THIS ADDS: the second bottom box on the diagram. Two independent specialists, each
reachable over the protocol, neither knowing the other exists.

This is where a multi-agent SYSTEM starts, and notice how little ceremony it took: a new
agent, a new card, a new port.

Run in its own terminal and LEAVE IT RUNNING:
    python src/step4_case_a2a_server.py

Sanity check from anywhere:
    curl http://127.0.0.1:9002/.well-known/agent-card.json
"""

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
    agent = make(get_client(), "CaseReview", CASE_REVIEW, [get_open_cases])
    serve(agent, card, HOST, PORT_CASES)


if __name__ == "__main__":
    main()

# CHECK YOUR UNDERSTANDING
# * Both servers now run on your laptop. In production, who owns each one - the same team?
#   Different teams? If the same team owns both, should they have been A2A at all?
# * Rule of thumb to hold onto: agents-as-tools inside a crew, A2A between crews.
