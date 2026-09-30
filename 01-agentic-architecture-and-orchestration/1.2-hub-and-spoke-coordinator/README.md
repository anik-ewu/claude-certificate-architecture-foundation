# Topic 1.2 · Hub-and-Spoke Research Coordinator

Build a **coordinator** (the hub) that takes a broad research topic, splits it into subtopics, sends each subtopic to two **subagents** (the spokes: web search and document analysis), checks whether the combined results cover everything, and re-delegates the gaps until coverage is complete.

```
                        ┌──────────────────────────────┐
     topic ───────────► │   COORDINATOR (hub)          │ ──► report
                        │ 1 decompose (+ validate)     │
                        │ 3 write full briefs          │
                        │ 4 assess coverage            │
                        │ 5 re-delegate the gaps ◄──┐  │
                        └──┬─────────────────────▲──┘  │
           brief (all the  │                     │ results
           context, stated │                     │
           explicitly)     ▼                     │
             ┌──────────────────┐   web results   ┌─────────────────────┐
             │ web search agent │ ──(through the ─►│ document analysis   │
             │ (tool loop, 1.1) │    hub, never    │ agent               │
             └──────────────────┘    directly)     └─────────────────────┘
                 spokes: no memory, no shared context, never talk to each other
```

## Run

```bash
# from the repo root
source .venv/bin/activate
cd 01-agentic-architecture-and-orchestration/1.2-hub-and-spoke-coordinator

python starter.py                     # your version
python starter.py --narrow            # your version, failure demo
python solution/solution.py           # reference (about 2 min, about 40 Haiku calls)
python solution/solution.py --narrow  # reference, failure demo
```
Reports are written to `output/`.

## Files

| File | What it is |
|------|-----------|
| `starter.py` | Your file. `TODO 1` to `TODO 6` match the tasks. |
| `agent_utils.py` | Given: `ask()`, `ask_json()` (structured output), `run_tool_loop()` (your 1.1 loop). |
| `mock_data.py` | Given: fake search index and internal documents. They have **deliberate gaps** (see below). |
| `solution/solution.py` | Reference implementation. |

**The mock data has built-in gaps.** Broad searches for tidal, wave, OTEC and fusion return only a one-line stub. Targeted queries (for example "tidal barrage projects" or "fusion ignition milestone") return the real detail. Those four also have no internal documents. This gives the refinement loop something real to fix.

---

## Tasks

### ☐ Task 1: The coordinator
Create a coordinator that takes a broad research topic and returns a structured research report.

- **Why:** In hub-and-spoke, the **coordinator** owns decomposition, choosing subagents, and aggregating their results. The subagents don't.
- **You should see:** A `run_coordinator(topic)` function that returns a report, and a `COORDINATOR_SYSTEM` prompt that defines the hub's role.

### ☐ Task 2: Broad decomposition (5 or more subtopics)
Split the topic into at least 5 distinct subtopics that cover its full breadth.

- **Why:** Narrow decomposition is a specific failure pattern on the exam. A coordinator that assigns only solar and wind for "renewable energy" misses whole categories. Incomplete output traces back to the **decomposition**.
- **You should see:** At least 5 subtopics for any broad topic. For renewable energy: solar, wind, geothermal, tidal, biomass and fusion at minimum.

### ☐ Task 3: Two subagents with explicit context passing
Start a web search subagent and a document analysis subagent. Put everything they need in each prompt.

- **Why:** Subagents are **isolated**: they have no shared memory and inherit no context. If a subagent does badly, first check whether the coordinator gave it enough context. Don't assume the subagent itself is flawed.
- **You should see:** Each subagent receives the subtopic, the research goal, and relevant context from earlier agents. The doc agent gets the web agent's findings, **relayed by the coordinator**.

### ☐ Task 4: Aggregate and evaluate coverage
Combine both subagents' results and assess coverage for each subtopic.

- **Why:** The coordinator has to judge whether the combined results cover the whole topic. Gaps found here trigger re-delegation.
- **You should see:** Each subtopic marked well covered, partially covered or missing, and a coverage %.

### ☐ Task 5: Iterative refinement loop
When there are gaps, re-delegate **only those subtopics** with targeted queries, then check coverage again. Repeat until coverage is 100% or you reach `MAX_ROUNDS`.

- **Why:** Delegating once isn't enough. Evaluating and re-delegating is what separates a **coordinator** from a simple **dispatcher**.
- **You should see:** Round 1 covers everything. Round 2 or later covers only the gaps, and the loop stops at 100% or the cap.

### ☐ Task 6: Test with "renewable energy technologies"
Check that the final report has sections on solar, wind, geothermal, tidal, biomass and fusion.

- **Why:** This is the exam's narrow-decomposition case. If only solar and wind appear, the root cause is the **coordinator's decomposition**.
- **You should see:** `RESULT: PASS` with all 6 categories marked `✅ own section`. Then run `--narrow` and see coverage reported as 100% even though 4 categories are missing.

---

## What the reference run showed (Haiku 4.5)

```
### Decomposing: renewable energy technologies
  (decomposition rejected: ... missing these required categories: biomass, fusion)
  - Solar Photovoltaic (PV) ... - Biomass ... - Tidal and Wave Energy ... - Fusion Energy ... (11 total)

### Round 1: coverage evaluation  →  10 ✅, 1 ❌ (0 facts)   coverage: 91%
### Round 2: delegating 1 subtopic(s)                        ← only the gap
### Round 2: coverage evaluation  →  11 ✅                   coverage: 100%
RESULT: PASS: all 6 categories covered
```

And with `--narrow`:
```
    ✅ Solar  ✅ Wind     coverage: 100%      ← the evaluator is "happy"...
    geothermal ❌  tidal ❌  biomass ❌  fusion ❌
RESULT: FAIL                                  ← ...but the report is incomplete
```
**This is the key exam point.** The evaluator can only score the subtopics the coordinator created. A "100% covered" report can still be incomplete, and the root cause is the **decomposition**, not the subagents or the evaluator.

### Lessons from building this

These came up while building the reference, and each maps to an exam idea:
1. **Haiku left fusion out of the decomposition in 3 out of 3 tries**, even with "cover experimental categories" in the prompt. The fix was not a longer prompt. It was the 1.1 principle again: **validate in code** (`must_cover` check) and send specific feedback ("missing: fusion") back to the model.
2. **The first evaluator made up its own verdicts.** It was asked to judge the whole topic in one call, and it returned some subtopics twice with conflicting statuses, and sometimes only 1 of 8. The fix: one assessment per subtopic (run in parallel). The model **lists the facts it found**, and **code** applies the threshold (at least 3 facts means well covered). Don't let the model grade itself on a vague scale.
3. **A catch-all subtopic ("Emerging Technologies") hides categories.** Fusion was buried inside one and never got its own section.

---

## Hints (open only when stuck)

<details><summary>Task 2: validating the decomposition</summary>

```python
for _ in range(2):
    names = [s["name"].lower() for s in subtopics]
    missing = [c for c in must_cover if not any(c in n for n in names)]
    if len(subtopics) >= MIN_SUBTOPICS and not missing:
        return subtopics
    prompt += f"\n\nPrevious answer: {...}. Missing: {missing}. Return the full revised list."
    subtopics = ask_json(...)
raise RuntimeError(...)
```
</details>

<details><summary>Task 3: what goes in a brief</summary>

Imagine the subagent is a contractor who has never heard of your project. It needs to know: the overall goal, its exact slice of the work, the questions to answer, what's already known (so it doesn't repeat it), and on later rounds, **what gap to fill and which queries to try**. Join the parts with blank lines and label each one (`OVERALL RESEARCH GOAL: ...`).
</details>

<details><summary>Task 3: relaying between spokes</summary>

```python
web = web_search_subagent(build_brief(topic, subtopic, prior, follow_up))
docs = document_analysis_subagent(
    build_brief(topic, subtopic, prior + [f"[web search agent]\n{web}"], follow_up),
    get_documents(subtopic["name"]),
)
```
The doc agent can't "see" the web agent. The coordinator puts the web output into the doc agent's brief.
</details>

<details><summary>Task 5: the loop shape</summary>

```python
for rnd in range(1, MAX_ROUNDS + 1):
    results = parallel(research_subtopic, {n: (topic, by_name[n], list(findings[n]), fu)
                                           for n, fu in to_research.items()})
    ...append to findings...
    assessments, pct = evaluate_coverage(topic, subtopics, findings)
    if pct >= 100: break
    to_research = {a["subtopic"]: a for a in assessments if a["status"] != "well_covered"}
else:
    log.warning(...)
```
</details>

---

## Exam takeaways

- **Hub-and-spoke:** all communication goes through the coordinator. Spokes never talk to each other, so the coordinator relays results between them.
- **Subagent isolation:** a subagent knows only what is in its prompt. If its output is poor, **check the brief first**.
- **Narrow decomposition:** if categories are missing from the output, trace it back to the **coordinator's decomposition**. The subagents and the evaluator can only work within the subtopics they were given.
- **Coordinator vs dispatcher:** a coordinator evaluates results and re-delegates gaps with targeted queries. A dispatcher sends tasks once and stops.
- **Deterministic guardrails:** validate the decomposition in code, apply coverage thresholds in code, and cap refinement rounds as a safety net (as in 1.1).
