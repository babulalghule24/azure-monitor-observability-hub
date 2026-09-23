# Course Outline & Thought Process
## Multi-Agent Orchestration — A2A, Handoffs, Group Chat & Workflows (Level 400)

**This is the document to read first — as the presenter, and as a learner.**
It sets the stage, shows the one architecture we build toward, and explains *why* each
step exists before any code appears.

Platform: **Microsoft Foundry (Azure AI Foundry) + Python + Microsoft Agent Framework + A2A**
Scenario: **SfMC Mission-Critical Operations Desk**, fully de-identified (`CUSTOMER-A`)

---

## 1. Setting the stage — the problem, in one paragraph

In Support for Mission Critical, every week the Technical Customer Lead and the CSA
prepare the **Open Case / Incident Review** and the service management meeting that
follows. To walk into that meeting you need a defensible picture of the week — and that
picture lives in four systems that do not talk to each other: Azure Monitor and Log
Analytics for what fired, the open support cases with their severity and age, the
unmitigated risks from the Consolidated Assessment sitting in a DevOps backlog, and a
reporting template that turns all of it into something a customer can read.

Today one engineer opens four tools and stitches it together by hand. It takes hours, it
varies by engineer, and risks surface late — which in mission critical is the expensive
kind of late.

**This week, for `CUSTOMER-A`:** intermittent 5xx errors on the public endpoint since
Tuesday, backend latency up, log ingestion cost rising, no deployment to blame.

Why this is a *legitimate* multi-agent problem — the three tests, all passed:
1. **Separation of expertise** — alert analysis, case management and architecture risk are
   genuinely different skills with different data.
2. **Separation of trust** — the monitoring baseline is owned by a different team (the
   Monitoring & Observability CoE), in a different Foundry project.
3. **Parallelism** — those three reads do not depend on each other.

If a problem fails all three tests, it wanted a better single agent, not a second agent.

---

## 2. What we are building — the one diagram

Everything in this session adds exactly one piece of this picture. Nobody has to hold the
whole thing in their head.

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│  SfMC OPERATIONS DESK — ORCHESTRATOR                                             │
│  Microsoft Agent Framework · Foundry project A                                   │
│                                                                                  │
│                            ╭──────────────╮                                      │
│                            │ INTAKE AGENT │   ← dynamic hand-off of tasks        │
│                            ╰──────┬───────╯      to specialist agents            │
│                ┌──────────────────┼──────────────────┐                           │
│           ┌────┴─────┐       ┌────┴─────┐       ┌────┴─────┐                     │
│           │A2A Client│       │A2A Client│       │A2A Client│                     │
│           └────┬─────┘       └────┬─────┘       └────┬─────┘                     │
│                │                  │                  │                           │
│   ┌────────────────────────────────────────────────────────────┐                 │
│   │ IN-PROCESS (no A2A, no HTTP hop):                          │                 │
│   │   Reporter  ⇄  Redactor      — Group Chat until APPROVED   │                 │
│   └────────────────────────────────────────────────────────────┘                 │
│                │                  │                  │                           │
└────────────────┼──────────────────┼──────────────────┼───────────────────────────┘
                 │                  │                  │
        ┌────────┴────────┐ ┌───────┴────────┐ ┌───────┴─────────────────────────┐
        │  A2A SERVER     │ │  A2A SERVER    │ │  A2A SERVER                     │
        │  ╭───────────╮  │ │ ╭────────────╮ │ │ ╭─────────────────────────────╮ │
        │  │  SIGNAL   │  │ │ │ CASEREVIEW │ │ │ │  CoE BASELINE ADVISOR       │ │
        │  ╰─────┬─────╯  │ │ ╰──────┬─────╯ │ │ ╰──────────────┬──────────────╯ │
        │        │ MCP    │ │        │ MCP   │ │   Monitoring & Observability CoE│
        │        ▼        │ │        ▼       │ │   Foundry project B             │
        │  Azure Monitor /│ │  Support case  │ │   DIFFERENT TEAM                │
        │  Log Analytics  │ │  data          │ │                                 │
        └─────────────────┘ └────────────────┘ └─────────────────────────────────┘

        MCP = agent → tools.      A2A = agent → agent.      Both, in one system.
```

**Read the diagram twice.** The architecture is not the code — it is the decision about
which agents got A2A and which stayed in-process. Reporter and Redactor live in the same
process because they do not need a network hop; putting HTTP between them would cost
latency and buy nothing. The CoE advisor is remote because it belongs to someone else.

---

## 3. The build path — 11 steps, each adding exactly one thing

| # | Step | What it ADDS | File |
|---|---|---|---|
| **1** | A plain Signal agent on Foundry | One working specialist. No protocol. | `step1_signal_agent.py` |
| **2** | Wrap it into an A2A server | An **agent card** — it becomes callable by anyone | `step2_signal_a2a_server.py` |
| **3** | Call it from an A2A client | **Discover → delegate → observe**, the task lifecycle | `step3_a2a_client.py` |
| **4** | A second A2A server: CaseReview | A multi-agent *system*, two independent specialists | `step4_case_a2a_server.py` |
| **5** | Sequential: findings → Reporter → Redactor | The first orchestration pattern; the confidentiality gate | `step5_sequential_report.py` |
| **6** | Concurrent: three specialists at once | Fan-out / fan-in, and when "parallel" is honest | `step6_concurrent_gather.py` |
| **7** | The CoE Baseline Advisor | Another team, another Foundry project — the real A2A case | `step7_coe_a2a_server.py` |
| **8** | Handoff: Intake routes dynamically | Decentralised routing + a **human TCL escalation target** | `step8_handoff_orchestrator.py` |
| **9** | Group Chat: refine until APPROVED | Centralised coordination + an iteration cap | `step9_group_chat.py` |
| **10** | Assemble the full desk | Nothing new — the whole diagram, running | `step10_full_desk.py` |
| **11** | Harden it | Identity, egress, budgets, tracing, evaluation | `step11_hardening.py` |

**Steps 1–3 are the A2A core.** Steps 5, 6, 8, 9 are the orchestration patterns. Step 11
is the difference between a demo and an engagement.

> Tell the room: *"You will have built all eleven by the end. Nothing here is a demo you
> only watch."*

---

## 4. Thought process — why this order, and not another

**Why start with a plain agent (step 1) instead of the protocol?**
Because the single most important idea in A2A is that *it does not change how you build an
agent*. If people meet the protocol first, they think it is a framework. Building the agent
first, then wrapping it, makes the boundary obvious: the agent did not change — only who
could reach it did.

**Why serve and call before adding any orchestration?**
Discover → delegate → observe is the entire protocol. Once that clicks, everything else is
a variation. Teaching orchestration first would bury the lifecycle under builder syntax.

**Why two A2A servers before the third?**
The second server (step 4) shows there is a *system*. The third (step 7) shows the
*reason* — a different team, a different project, a different data boundary. If we
introduced the CoE agent too early, learners would conclude A2A is "how you add agents",
which is wrong and expensive.

**Why is Sequential taught before Concurrent?**
Because the Redactor has to exist before people see anything leave the desk. Making
confidentiality the *second* pattern taught, not the last, is deliberate.

**Why is Handoff late?**
It is the most seductive pattern and the easiest to get wrong. By step 8 the room already
understands hop cost and context loss, so the guardrails land instead of sounding like
nagging.

**Why does step 10 add nothing new?**
Because the payoff is seeing the first slide's diagram run. The lesson of step 10 is that
the architecture was the set of *boundary decisions*, and the code was almost incidental.

**What we deliberately leave out of the 90 minutes:**
Magentic internals, custom aggregators, checkpoint internals, .NET, the AP2 payments
extension. They are named, not taught. A Level 400 that covers everything covers nothing.

---

## 5. How the 90 minutes maps to the build path

| Time | Section | Build steps |
|---|---|---|
| 0:00–0:08 | Open + the real problem | — |
| 0:08–0:15 | When NOT to go multi-agent | — |
| 0:15–0:20 | The four-layer mental model + the target diagram | — |
| 0:20–0:45 | The five orchestration patterns | 5, 6, 8, 9 (+ Magentic) |
| 0:45–1:05 | A2A internals | 2, 3, 7 |
| 1:05–1:28 | Hands-on lab | 1–3, then 6 and 5, then 8–9, then 7 |
| 1:28–1:38 | Hardening, takeaways, Q&A | 11 |

Return to the diagram at the start of each section and point at the piece being added.
That single habit is what makes a dense 400 feel navigable.

---

## 6. The de-identification rule — why it is architecture, not hygiene

Everything in SfMC is Microsoft Confidential and customer-identifying. So:

- All fixtures are synthetic. The customer is `CUSTOMER-A`. Subscription GUIDs are
  fabricated, case IDs invented, and there are no names, emails or IP addresses anywhere.
- The **Redactor is a first-class agent with a veto**, not a post-processing filter. It
  participates in the group chat and blocks the pack until it is clean.
- It runs on the **outbound** path — before anything crosses an A2A boundary, not after.
- Secure by design, secure by default, secure operations.

**Teaching note:** in the lab, have people *try to break it* — add a fake name and email to
the findings and re-run. If the Redactor lets it through, the room has just learned that a
prompt alone is not a control. That is a far better lesson than a slide saying so.

---

## 7. The decision framework learners leave with

Ask in order; stop at the first that answers.

1. **Does one agent with good tools already solve it?** → Do that.
2. **Fixed order, each step depending on the last?** → **Sequential**
3. **Genuinely independent sub-tasks?** → **Concurrent** (+ an aggregator)
4. **Classify, then send to the right specialist?** → **Handoff** (+ a human target)
5. **Agents critiquing and refining each other?** → **Group Chat** (+ an iteration cap)
6. **Solution path unknown up front?** → **Magentic** (planning manager, task ledger)
7. **Agent owned by another team, framework or cloud?** → **A2A**, on top of the above

And the one sentence to carry out of the room:

> **The hard part of multi-agent systems is not making agents talk.
> It is deciding which agent should not exist.**

---

## 8. Reference material (primary sources only)

- A2A protocol — https://a2a-protocol.org/latest/
- A2A repo and SDKs — https://github.com/a2aproject/A2A
- Agent Framework orchestrations — https://learn.microsoft.com/en-us/agent-framework/workflows/orchestrations/
- Agent Framework Python samples — https://github.com/microsoft/agent-framework/tree/main/python/samples/03-workflows/orchestrations
