# Multi-Agent Orchestration — A2A, Handoffs, Group Chat & Workflows

**Build a multi-agent system one piece at a time. Eleven steps. Thirty seconds to start.**

```bash
git clone https://github.com/babulalghule24/azure-monitor-observability-hub.git
cd azure-monitor-observability-hub/agents/multi-agent-orchestration
pip install -r requirements.txt

# No Azure account needed. No credentials. No setup.
LAB_OFFLINE=1 python src/step1_signal_agent.py       # PowerShell: $env:LAB_OFFLINE=1
```

That's it. You're running.

---

## Start here: a Monday you already know

It's Monday morning. You have a status meeting on Thursday, and to walk in prepared you
need to answer one question:

> *"Something went wrong last week. What happened, why, and what are we asking them to do
> about it?"*

The answer exists. It's just scattered across four systems that don't talk to each other:
the monitoring alerts, the open support tickets, a risk register everyone forgot about,
and a reporting template nobody enjoys filling in.

So you open four tabs and stitch it together by hand. It takes hours. It comes out
slightly different every time. And the thing you most needed to notice — that two of the
risks on that register *predicted this exact failure* — gets missed, because you ran out
of patience before you got to the register.

**This lab builds the thing that does it for you.** Not one clever agent — a small team of
them, each good at one source, coordinated properly, with a gate that stops anything
leaving unchecked.

Our version uses a Microsoft **Support for Mission Critical** weekly service review. Yours
might be a sprint report, an incident review, a client update. The pattern is the same,
and so are the mistakes.

## The catch nobody tells you

**Most multi-agent systems should have been a single agent.** More agents means more
latency, more tokens, more randomness, and far harder debugging.

You earn a second agent by naming one of three things:

1. **Different expertise** — different prompts, tools, and data
2. **A trust boundary** — someone else owns it and you shouldn't see inside
3. **Real parallelism** — work that genuinely doesn't wait on other work

Our Monday problem passes all three. Most problems pass none. Learning to tell the
difference is the actual skill, and it's what this lab is really teaching.

---

## What you'll build

```
   ORCHESTRATOR — your process
     Intake agent ──decides who handles what──▶  3 × A2A Client
     in-process:  Reporter ⇄ Redactor   (they talk directly — no network between them)
                    │              │              │
              ┌─────┴────┐   ┌─────┴────┐   ┌─────┴──────────────────┐
              │A2A SERVER│   │A2A SERVER│   │A2A SERVER              │
              │ Signal   │   │CaseReview│   │ CoE Baseline Advisor   │
              │  ↓ MCP   │   │  ↓ MCP   │   │ ANOTHER TEAM'S SYSTEM  │
              │ alerts   │   │ tickets  │   │                        │
              └──────────┘   └──────────┘   └────────────────────────┘
                 step 2         step 4              step 7

              MCP = agent → tools.    A2A = agent → agent.
```

**The one sentence to take away:** the architecture isn't the code — it's the decision
about which agents needed a network between them and which didn't.

Reporter and Redactor share a process because putting HTTP between them would cost
latency and buy nothing. The CoE advisor is remote because it belongs to a different team
who shouldn't see your data, and whose prompts you shouldn't need.

## The eleven steps

| # | Step | What it adds |
|---|---|---|
| 1 | One agent, one tool | A working specialist. No protocol, nothing clever. |
| 2 | Wrap it into an A2A server | An **agent card** — now anyone can call it |
| 3 | Call it from an A2A client | Discover → delegate → observe |
| 4 | A second A2A server | Now it's a *system* |
| 5 | Sequential | Write it, then gate it. Order matters. |
| 6 | Concurrent | Three sources at once. When "parallel" is honest. |
| 7 | The CoE advisor | Another team, another project. **Why A2A exists.** |
| 8 | Handoff | The *model* does the routing — plus a human escape hatch |
| 9 | Group Chat | Draft, critique, revise — with a budget |
| 10 | The whole desk | The diagram above, running |
| 11 | Harden it | Identity, egress, caps, tracing, evaluation |

Steps **1–3 are the A2A core**. Steps **5, 6, 8, 9** are the orchestration patterns.
Step **11** is the difference between a demo and something you'd put near a customer.

Every step prints **what it adds**, **what to watch for**, each agent's turn clearly
labelled, and **what just happened** — so the story tells itself as you run it.

---

## Two ways to run

### Offline — 30 seconds, no account

```bash
LAB_OFFLINE=1 python src/step1_signal_agent.py      # PowerShell: $env:LAB_OFFLINE=1
```

Scripted answers, no network, works on any laptop. **Every pattern behaves identically** —
who speaks, in what order, who decides, where the boundaries are. That's what you're here
to learn, and it doesn't need a live model.

Use this to learn the patterns, and in a workshop so nobody is blocked on setup.

### Live — against your own Microsoft Foundry project

```bash
cp .env.example .env          # add your project endpoint + model deployment
az login --tenant <TENANT_ID>  # the tenant that OWNS the resource — see below
python src/_preflight.py       # checks everything, explains failures in plain English
python src/step1_signal_agent.py
```

> **If setup fights you, it's one of four things** — a renamed SDK class, the wrong Entra
> tenant, a missing data-plane role, or a stale token. All four are documented with fixes
> in **[docs/SETUP-TROUBLESHOOTING.md](docs/SETUP-TROUBLESHOOTING.md)**, and
> `src/_preflight.py` diagnoses each one in a sentence.
>
> Or just use `LAB_OFFLINE=1` and learn the patterns now, setup later.

## Where to go next

| I want to... | Read |
|---|---|
| **Do the lab** — full walkthrough, code inline, expected output | **[docs/HANDS-ON-LAB.md](docs/HANDS-ON-LAB.md)** |
| Follow along quickly while running commands | [LAB-GUIDE.md](LAB-GUIDE.md) |
| Understand *why* the steps come in this order | [docs/COURSE-OUTLINE.md](docs/COURSE-OUTLINE.md) |
| Fix a setup problem | [docs/SETUP-TROUBLESHOOTING.md](docs/SETUP-TROUBLESHOOTING.md) |

## A note on the data

Everything here is **synthetic**. The customer is always `CUSTOMER-A`, the subscription
GUIDs are invented, and there are no names, emails or IP addresses anywhere.

That's not just repo hygiene — it's in the architecture. The **Redactor** is a
first-class agent with a veto, running on the *outbound* path, and it blocks the report
until it's clean. Try to sneak a name past it in step 5; if it lets you, you've just
learned that a prompt alone is not a control.

## Repo layout

```
multi-agent-orchestration/
├─ README.md                     ← you are here
├─ LAB-GUIDE.md                  ← the 11 steps, condensed
├─ docs/
│  ├─ HANDS-ON-LAB.md            ← full walkthrough, all code inline
│  ├─ COURSE-OUTLINE.md          ← the architecture and the reasoning
│  └─ SETUP-TROUBLESHOOTING.md   ← the four traps and their fixes
├─ data/                         ← synthetic fixtures only
└─ src/
   ├─ common.py                  ← client, tools, agents, A2A + builder helpers
   ├─ narrate.py                 ← the presentation layer
   ├─ offline.py                 ← LAB_OFFLINE=1 — no Azure needed
   ├─ _doctor.py                 ← what SDK do I have?
   ├─ _preflight.py              ← can I reach my project?
   └─ step1..step11              ← the build path, one file per step
```

## Reference

- A2A protocol — https://a2a-protocol.org/latest/
- A2A SDKs — https://github.com/a2aproject/A2A
- Agent Framework orchestrations — https://learn.microsoft.com/en-us/agent-framework/workflows/orchestrations/
- Agent Framework Python samples — https://github.com/microsoft/agent-framework/tree/main/python/samples/03-workflows/orchestrations

---

> **The hard part of multi-agent systems isn't making agents talk.
> It's deciding which agent shouldn't exist.**

MIT licensed. Teaching code — harden before production use.
