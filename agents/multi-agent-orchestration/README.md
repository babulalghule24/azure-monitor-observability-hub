# Multi-Agent Orchestration — A2A, Handoffs, Group Chat & Workflows (Level 400)

Build a real multi-agent system, one piece at a time, on **Microsoft Foundry (Azure AI
Foundry) with Python** — using the **Microsoft Agent Framework** orchestration patterns and
the **Agent2Agent (A2A)** protocol.

**11 steps. Each adds exactly one thing. You build all of them.**

The scenario is real work: preparing the weekly **Support for Mission Critical (SfMC)**
service review for a mission-critical Azure workload — fully de-identified.

> Delivered in the **AInstein APJMEA AI Agent Training Series** by Babulal Ghule,
> Cloud Solution Architect · WW Lead, SfMC Monitoring & Observability CoE.

---

## ⚠️ De-identification rule — read this first

Everything in SfMC is Microsoft Confidential and customer-identifying. **This repo contains
no customer data.** Every fixture under `data/` is synthetic: the customer is always
`CUSTOMER-A`, subscription GUIDs are fabricated, case IDs invented, and there are no names,
email addresses or IP addresses anywhere.

That is a design lesson, not repo hygiene. In this architecture the **Redactor is a
first-class agent with a veto**, running on the *outbound* path — not a clean-up step
bolted on at the end. Secure by design, secure by default, secure operations.

**Never commit real alert exports, case exports, assessment outputs or `.env` files.**

---

## Set the stage

You are the CSA on an SfMC engagement. It is Monday. The weekly **Open Case / Incident
Review** is Thursday, and you need a defensible picture of the week for `CUSTOMER-A`:

> Since Tuesday the public endpoint has returned intermittent 5xx errors and backend
> latency is up. There was no deployment. Log ingestion cost has risen. What happened,
> what do we think the cause is, and what are we asking the customer to do?

That answer lives in four systems that do not talk to each other — Azure Monitor signals,
open support cases, unmitigated Consolidated Assessment risks, and a reporting template.
One engineer stitches it together by hand in a few hours, differently every time.

**This repo builds the desk that does it.**

## What you are building

```
   ORCHESTRATOR — Foundry project A  (Microsoft Agent Framework)
     Intake agent ──dynamic hand-off of tasks──▶  3 × A2A Client
     in-process:  Reporter ⇄ Redactor   (Group Chat until APPROVED, no HTTP hop)
                    │              │              │
              ┌─────┴────┐   ┌─────┴────┐   ┌─────┴──────────────────┐
              │A2A SERVER│   │A2A SERVER│   │A2A SERVER              │
              │ Signal   │   │CaseReview│   │ CoE Baseline Advisor   │
              │  ↓ MCP   │   │  ↓ MCP   │   │ Foundry project B      │
              │ Azure    │   │ Support  │   │ DIFFERENT TEAM         │
              │ Monitor  │   │ cases    │   │                        │
              └──────────┘   └──────────┘   └────────────────────────┘
                 step 2         step 4              step 7

              MCP = agent → tools.    A2A = agent → agent.    Both, in one system.
```

**The architecture is not the code — it is the decision about which agents got A2A and
which stayed in-process.**

## The build path

| # | Step | Adds | File |
|---|---|---|---|
| 1 | Plain Signal agent on Foundry | One specialist, no protocol | `step1_signal_agent.py` |
| 2 | Wrap it into an A2A server | An agent card — it becomes callable | `step2_signal_a2a_server.py` |
| 3 | Call it from an A2A client | Discover → delegate → observe | `step3_a2a_client.py` |
| 4 | Second A2A server: CaseReview | A multi-agent system | `step4_case_a2a_server.py` |
| 5 | Sequential: Reporter → Redactor | First pattern + the gate | `step5_sequential_report.py` |
| 6 | Concurrent: three at once | Fan-out / fan-in | `step6_concurrent_gather.py` |
| 7 | CoE Baseline Advisor | Another team, another project | `step7_coe_a2a_server.py` |
| 8 | Handoff orchestrator | Dynamic routing + human escalation | `step8_handoff_orchestrator.py` |
| 9 | Group Chat | Refinement + iteration cap | `step9_group_chat.py` |
| 10 | Assemble the full desk | The whole diagram, running | `step10_full_desk.py` |
| 11 | Harden it | Identity, egress, budgets, tracing | `step11_hardening.py` |

Steps **1–3 are the A2A core**. Steps **5, 6, 8, 9** are the orchestration patterns.
Step **11** is the difference between a demo and an engagement.

## The cast

| Agent | Owns | Where it lives |
|---|---|---|
| **Intake** | Routes the situation, or escalates to a human | Orchestrator, in-process |
| **Signal** | Azure Monitor alert analysis — signal vs noise, coverage gaps | A2A server, port 9001 |
| **CaseReview** | Open support cases by severity and age | A2A server, port 9002 |
| **Resilience** | Unmitigated Consolidated Assessment risks | In-process |
| **Reporter** | Writes the service review pack | In-process |
| **Redactor** | Confidentiality + accuracy gate, with a veto | In-process |
| **TCL escalation queue** | The human. Severity calls, customer commitments | Handoff target |
| **CoE Baseline Advisor** | Another team's alert-baseline guidance | A2A server, port 9003 |

## Where to start

| If you want to... | Read this |
|---|---|
| **Do the lab** — narrative, full code inline, expected output, checks | **[docs/HANDS-ON-LAB.md](docs/HANDS-ON-LAB.md)** — the complete self-contained walkthrough |
| Follow along quickly while running commands | [LAB-GUIDE.md](LAB-GUIDE.md) — the same 11 steps, condensed |
| Understand *why* the steps come in this order | [docs/COURSE-OUTLINE.md](docs/COURSE-OUTLINE.md) — outline and design reasoning |

## Repo layout

```
multi-agent-orchestration-l400/
├─ README.md                      ← you are here
├─ LAB-GUIDE.md                   ← the 11 steps, condensed
├─ docs/
│  ├─ HANDS-ON-LAB.md             ← full walkthrough with all code inline
│  └─ COURSE-OUTLINE.md           ← the architecture and the reasoning
├─ requirements.txt
├─ .env.example
├─ .gitignore                     ← blocks .env and any real data export
├─ LICENSE
├─ data/                          ← SYNTHETIC fixtures only
│  ├─ alerts.json                    Azure Monitor activity + coverage gaps
│  ├─ cases.json                     open support cases
│  └─ risks.json                     Consolidated Assessment risk backlog
└─ src/
   ├─ common.py                   ← Foundry client, tools, agents, A2A helpers
   └─ step1..step11               ← the build path, one file per step
```

Read `src/common.py` once. Every step file is short because the plumbing lives there.

## Quick start

```bash
git clone https://github.com/<your-github-handle>/multi-agent-orchestration-l400.git
cd multi-agent-orchestration-l400

python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env     # add your Foundry project endpoint + model deployment
az login                 # auth is Entra ID — there are no keys in this repo

python src/step1_signal_agent.py
```

Then work through **[docs/HANDS-ON-LAB.md](docs/HANDS-ON-LAB.md)** (full walkthrough) or
**[LAB-GUIDE.md](LAB-GUIDE.md)** (condensed).

## Reference material

- A2A protocol — https://a2a-protocol.org/latest/
- A2A source and SDKs — https://github.com/a2aproject/A2A
- Agent Framework orchestrations — https://learn.microsoft.com/en-us/agent-framework/workflows/orchestrations/
- Agent Framework Python samples — https://github.com/microsoft/agent-framework/tree/main/python/samples/03-workflows/orchestrations

## License

MIT — see `LICENSE`. Teaching code: harden before production use.
