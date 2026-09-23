# Lab Guide — Build the SfMC Mission-Critical Operations Desk

**11 steps. Each one adds exactly one thing. You build all of them.**

Platform: **Microsoft Foundry + Python + Microsoft Agent Framework + A2A**

> New to multi-agent systems? Start with `../Course-Outline-and-Thought-Process.md` — it
> sets the stage and explains why the steps come in this order. Then come back here.

---

## Set the stage

You are the CSA on an SfMC engagement. It is Monday. The weekly **Open Case / Incident
Review** is on Thursday, and you have to walk in with a defensible picture of the week for
`CUSTOMER-A`:

> Since Tuesday the public endpoint has returned intermittent 5xx errors and backend
> latency is up. There was no deployment. Log ingestion cost has risen. What happened,
> what do we think the cause is, and what are we asking the customer to do?

The answer lives in four systems that do not talk to each other. One engineer does this by
hand in a few hours. **By the end of this lab, a desk of agents does it — and you will have
built every piece.**

## What you are building

```
   ORCHESTRATOR (Foundry project A)                     ← steps 8, 9, 10
     Intake agent  ──dynamic hand-off──▶  3 × A2A Client
     in-process: Reporter ⇄ Redactor (Group Chat, no HTTP hop)
                    │              │              │
              ┌─────┴────┐   ┌─────┴────┐   ┌─────┴──────────────────┐
              │A2A SERVER│   │A2A SERVER│   │A2A SERVER              │
              │ Signal   │   │CaseReview│   │ CoE Baseline Advisor   │
              │  ↓ MCP   │   │  ↓ MCP   │   │ (Foundry project B,    │
              │ Azure    │   │ Support  │   │  DIFFERENT TEAM)       │
              │ Monitor  │   │ cases    │   │                        │
              └──────────┘   └──────────┘   └────────────────────────┘
                 step 2         step 4              step 7

              MCP = agent → tools.   A2A = agent → agent.
```

## ⚠️ The de-identification rule

All data is synthetic: `CUSTOMER-A`, fabricated GUIDs, invented case IDs, no names, no IPs.
The **Redactor is a first-class agent with a veto**, not a filter at the end. Keep it that
way, and never commit real data to this repo.

## The build path

| # | Step | Adds | Time |
|---|---|---|---|
| 1 | Plain Signal agent on Foundry | One specialist, no protocol | 3 min |
| 2 | Wrap it into an A2A server | An agent card — it becomes callable | 3 min |
| 3 | Call it from an A2A client | Discover → delegate → observe | 3 min |
| 4 | Second A2A server: CaseReview | A multi-agent system | 2 min |
| 5 | Sequential: Reporter → Redactor | First pattern + the gate | 3 min |
| 6 | Concurrent: three at once | Fan-out / fan-in | 3 min |
| 7 | CoE Baseline Advisor | Another team, another project | 3 min |
| 8 | Handoff orchestrator | Dynamic routing + human escalation | 3 min |
| 9 | Group Chat | Refinement + iteration cap | 3 min |
| 10 | Assemble the full desk | The whole diagram, running | 3 min |
| 11 | Harden it | Identity, egress, budgets, tracing | homework |

**In the live session** we do steps 1–3, then 6 and 5, then 8–9, then 7 and 10. Steps 4 and
11 are yours afterwards. If you fall behind, jump to step 3 — it is the one you cannot
easily reconstruct alone.

---

## Step 0 — Setup (do this *before* the session)

```bash
git clone https://github.com/<your-github-handle>/multi-agent-orchestration-l400.git
cd multi-agent-orchestration-l400

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env               # Windows: copy .env.example .env
```

In `.env`, set your **Foundry project endpoint** and model deployment:

```
AZURE_AI_PROJECT_ENDPOINT=https://<your-foundry-resource>.services.ai.azure.com/api/projects/<your-project>
AZURE_AI_MODEL_DEPLOYMENT_NAME=gpt-4o-mini
```

Sign in — there are no keys in this repo:

```bash
az login
```

**Verify:**

```bash
python -c "import agent_framework, agent_framework_orchestrations; print('ready')"
```

> **If an import or builder name has drifted:** the framework ships fast. Match your
> installed version against the official Python samples at
> https://github.com/microsoft/agent-framework/tree/main/python/samples/03-workflows/orchestrations
> and adjust one line. Reading the samples instead of the blog posts is a Level 400 habit.

Open `src/common.py` once and skim it. Every step file afterwards is short because the
Foundry client, the data tools, the agent instructions and two small A2A helpers all live
there.

---

## Step 1 — A plain agent on Foundry (3 min)

**Adds:** one working specialist. No protocol, no orchestration, nothing clever.

```bash
python src/step1_signal_agent.py
```

What happened: you authenticated to a Foundry project with Entra ID, the model called your
`get_monitor_signals` tool because its description said it could, and it separated signal
from noise in the week's alerts.

**Check yourself**
- `AKS-NodePool-CPU-High` fired 228 times. Did the agent call that signal or noise — and
  did it say *why*? An agent that cannot justify a conclusion is not usable in
  mission-critical support.
- Nothing here is multi-agent yet. Honestly: would a second agent have made this answer
  better?

---

## Step 2 — Wrap it into an A2A server (3 min)

**Adds:** an **agent card**. The agent becomes callable by anyone who speaks A2A — a
different framework, a different team, a different cloud.

**This is the most important idea in the protocol: A2A does not change how you build an
agent. It changes who can reach it.** Nothing about the Signal agent changed between step 1
and step 2.

Terminal 1 — **leave this running**:

```bash
python src/step2_signal_a2a_server.py
```

Terminal 2 — look at what you just published:

```bash
curl http://127.0.0.1:9001/.well-known/agent-card.json
```

Read it properly. It advertises name, version, your skills, whether you stream, what input
and output types you take, and which authentication schemes you accept. **This is a
contract, not documentation** — it is how a caller decides whether to delegate to you at all.

**Check yourself**
- Your instructions, your tool and your Foundry project are *not* in that card. Why is
  that the point?
- The card lists auth schemes. Nothing in the protocol enforces them. Who does?

---

## Step 3 — Call it from an A2A client (3 min)

**Adds:** the first arrow on the diagram.

Terminal 2:

```bash
python src/step3_a2a_client.py
```

Trace the three moves in the output — they are the entire protocol:

1. **Discover** — fetch the agent card. Decide whether to trust it.
2. **Delegate** — send a `Message`. The remote agent opens a **Task**.
3. **Observe** — `submitted → working → input_required → completed` (or `failed` /
   `canceled`), ending in **Artifacts**.

And notice what you *cannot* see: the remote agent's instructions, tool, model or data.
That opacity is the feature that makes A2A safe across an organisational boundary.

**Check yourself**
- Which state would a long-running research task sit in for minutes — and how would you
  be told when it finished? (Streaming over SSE, or a webhook push notification.)
- Kill the server and re-run. What state comes back, and did your code handle it?

---

## Step 4 — A second A2A server (2 min)

**Adds:** a multi-agent *system*. Two independent specialists, neither knowing the other
exists.

Terminal 3 — **leave running**:

```bash
python src/step4_case_a2a_server.py
curl http://127.0.0.1:9002/.well-known/agent-card.json   # from anywhere
```

**Check yourself**
- In production, who owns each server? If the *same* team owns both, should they have been
  A2A at all? **Rule of thumb: agents-as-tools inside a crew, A2A between crews.**

---

## Step 5 — Sequential: Reporter → Redactor (3 min)

**Adds:** the first orchestration pattern, and the confidentiality gate. These two are
**in-process, not A2A** — same process, no HTTP hop, because they do not need one.

```bash
python src/step5_sequential_report.py
```

Order is the whole point: the Reporter cannot write before findings exist, and nothing
leaves the desk before the Redactor has seen it.

**Check yourself**
- Each agent sees the whole conversation by default — right here, since the Redactor must
  check the draft against the findings. `chain_only_agent_responses=True` restricts that
  for pure transform stages. When would you want it?
- **Try to break the gate:** add `contact is Jane Doe, jane@example.com` to `FINDINGS` and
  re-run. The Redactor *must* refuse. If it does not, your gate is decorative — and you
  have just learned first-hand that a prompt alone is not a control.

---

## Step 6 — Concurrent: three specialists at once (3 min)

**Adds:** fan-out / fan-in — and the test for when "parallel" is honest.

```bash
python src/step6_concurrent_gather.py
```

Signal, Resilience and CaseReview each read a different source. None needs another's
output, so running them serially is pure wasted latency. **The test: if agent B should read
agent A's answer, this is the wrong pattern.**

**Check yourself**
- Nobody merged the three answers — the default aggregator returns one message per
  participant. Who merges: a custom aggregator, or the Reporter?
- What do you do when Signal and Resilience contradict each other? Decide now, not in
  production.
- **Stretch:** add the Reporter as a fourth concurrent participant and watch it write a
  review based on nothing. That failure *is* the lesson.

---

## Step 7 — The CoE Baseline Advisor (3 min)

**Adds:** the reason A2A exists at all.

Steps 2 and 4 served agents you own. This one is different in kind. The Monitoring &
Observability CoE owns the alert baseline for each Azure service. Your desk needs to ask
it a question. You must not need a copy of their prompts; they must not need access to your
engagement's data. **Different team, different Foundry project, different data boundary.**

Terminal 4 — **leave running**:

```bash
python src/step7_coe_a2a_server.py
```

**Check yourself**
- Look at the question step 10 sends this agent: no customer name, no subscription ID, no
  case URL. **Crossing a team boundary is where de-identification stops being a lab rule
  and becomes a control.**
- What would you need on the wire before calling this with real context? (Bearer token
  enforced, card signature verified, identity pinned, egress policy, Redactor outbound.)

---

## Step 8 — Handoff: dynamic routing (3 min)

**Adds:** the orchestrator, and the "dynamic hand-off" arrow on the diagram.

```bash
python src/step8_handoff_orchestrator.py
```

There is **no orchestrator object**. Intake is a participant that happens to hold the
conversation, and it transfers by **calling a generated tool** — `handoff_to_<target>`. The
routing decision is made by the model, inside the agent, not by code you wrote.

The most important line in the file is `tcl_queue`. Some decisions are not the agent's to
make — severity calls, customer commitments, anything contractual. In a handoff
architecture you express that as **a handoff target that is a human queue**. Design it in
on day one.

**Check yourself**
- Find the `handoff_to_<target>` call. Does Intake's stated reason hold up, or did it route
  on a keyword?
- Handoff is the only built-in pattern that is **interactive by default** — it pauses for
  the user between turns. Right for a support conversation; is it right at 2 a.m.?
- **Stretch:** make two specialists hand back unconditionally and watch `MAX_HOPS` catch
  the ping-pong. This is the number-one handoff failure in production.

---

## Step 9 — Group Chat: refine until APPROVED (3 min)

**Adds:** iterative refinement, and the centralised/decentralised distinction.

```bash
python src/step9_group_chat.py
```

Star topology: an orchestrator picks who speaks next, and every participant sees the full
shared conversation — which is what lets the Reporter act on the Redactor's corrections.

> **Group chat is centralised** — an orchestrator picks the speaker.
> **Handoff is decentralised** — the current agent picks, by calling a tool.

**Check yourself**
- Re-run with `max_iterations=2`. The loop stops mid-refinement. **An uncapped group chat
  is an uncapped bill** — that number is a budget, not a tuning knob.
- Round-robin wastes a turn after `APPROVED`. Write a selection function that terminates on
  it and watch the token cost roughly halve.
- The Redactor is a *participant with a veto*, not a filter at the end. Why does that
  placement matter for a mission-critical engagement?

---

## Step 10 — Assemble the full desk (3 min)

**Adds: nothing new. That is the point.** This is the first slide's diagram, running.

All three servers must be up — step 2, step 4 and step 7, each in its own terminal. Then:

```bash
python src/step10_full_desk.py
```

Three remote agents gathered concurrently over A2A — one owned by another team — then an
in-process group chat writes and gates the pack until the Redactor approves it.

**Check yourself**
- You just sent findings across a team boundary. Where should the Redactor have run —
  before the A2A calls, after, or both? (Outbound, before anything leaves.)
- **Which of these agents could you delete tomorrow without the pack getting worse?** That
  question is the entire discipline of multi-agent design.

---

## Step 11 — Harden it (homework)

```bash
python src/step11_hardening.py
```

Eleven areas: identity per agent, A2A trust, egress, untrusted input, budgets, model
tiering, observability, checkpointing, human-in-the-loop, evaluation, data handling.

Score yourself honestly. **Anything unticked is a finding you would raise against a
customer's architecture — so raise it against your own first.**

---

## The decision framework you leave with

Ask in order. Stop at the first that answers.

1. **Does one agent with good tools already solve it?** → Do that.
2. **Fixed order, each step depending on the last?** → **Sequential**
3. **Genuinely independent sub-tasks?** → **Concurrent** (+ an aggregator)
4. **Classify, then route to a specialist?** → **Handoff** (+ a human target)
5. **Agents critiquing and refining each other?** → **Group Chat** (+ an iteration cap)
6. **Solution path unknown up front?** → **Magentic** (planning manager, task ledger)
7. **Agent owned by another team, framework or cloud?** → **A2A**, on top of the above

> **The hard part of multi-agent systems is not making agents talk.
> It is deciding which agent should not exist.**
