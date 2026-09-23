"""STEP 11 - Hardening: what stands between step 10 and a real engagement.

This file is runnable, but it is mostly a CHECKLIST IN CODE. Work down it and implement
each item against your own build. Nothing here is optional for mission-critical work.

Run:  python src/step11_hardening.py
"""

CHECKLIST = [
    ("Identity",
     "Every agent gets its own Entra ID workload identity with scoped tokens. An agent is "
     "a new identity in your tenant - give it the same scrutiny as a service principal."),
    ("A2A trust",
     "Verify agent card signatures (v1.0 supports JSON Web Signature). Pin identities. "
     "Never resolve an arbitrary URL at runtime. Enforce a bearer token or mTLS - the "
     "protocol ADVERTISES auth schemes, it does not ENFORCE them."),
    ("Egress",
     "Know which agents yours may call, and what may leave with the request. Run the "
     "Redactor on the OUTBOUND path, before anything crosses a boundary."),
    ("Untrusted input",
     "Treat every remote agent's response as data, never as instructions. A returned "
     "artifact that says 'ignore your previous rules' is an attack, not a message."),
    ("Budgets",
     "Iteration caps on group chat. Hop budgets on handoff. Per-request token budget. "
     "Enforced in code, not hoped for in a prompt."),
    ("Model tiering",
     "Use a cheap model for routing agents (Intake) and an expensive one for reasoning "
     "agents. Routing is classification, not analysis."),
    ("Observability",
     "One OpenTelemetry span per agent turn, with the routing reason as an attribute, "
     "exported to Application Insights. Without this a multi-agent bug is unfixable - you "
     "cannot reconstruct a conversation from logs."),
    ("Checkpointing",
     "Long workflows must resume, not restart. Checkpoint after each expensive stage."),
    ("Human in the loop",
     "Tool approval on anything irreversible or customer-facing. The agent proposes, the "
     "human commits. Keep the human handoff target in the graph."),
    ("Evaluation",
     "An eval set of at least 10 inputs with expected routing and expected redaction "
     "outcomes. Multi-agent regressions are otherwise invisible: a prompt change in the "
     "Redactor can quietly break the Reporter."),
    ("Data handling",
     "Real engagement data only in an approved, access-controlled environment. Synthetic "
     "fixtures everywhere else. Never in this repo."),
]


def main():
    print("\nSTEP 11 - PRODUCTION HARDENING CHECKLIST\n" + "=" * 60)
    for i, (area, detail) in enumerate(CHECKLIST, 1):
        print(f"\n[ ] {i:2}. {area}\n       {detail}")
    print("\n" + "=" * 60)
    print("Score yourself honestly. Anything unticked is a finding you would raise")
    print("against a customer's architecture - so raise it against your own first.\n")


if __name__ == "__main__":
    main()
