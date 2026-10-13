# Topic 1.3 · Subagent Invocation & Context Passing

Build a coordinator whose **only tool is `Task`** (it spawns subagents). Each subagent is defined by a description, a system prompt and a list of **allowed tools**. The coordinator answers: *"Should Nimbus Robotics launch its Stratus robot in Germany in 2027?"* by spawning two researchers **in parallel**, then a tool-less synthesizer that only knows what the coordinator **passes it as context**.

```
                    ┌────────────────────────────────────────┐
  question ───────► │ COORDINATOR   allowed tools: [Task]     │ ──► report
                    └──┬──────────────────┬──────────────▲───┘
     turn 1: two Task calls in ONE response│              │ turn 2: Task(synthesizer,
     (run in parallel)                     │              │   context=[findings...])
          ▼                                ▼              │
 ┌───────────────────┐        ┌────────────────────┐   ┌──┴────────────────────┐
 │ news_researcher   │        │ doc_analyst        │   │ synthesizer           │
 │ tools: search_news│        │ tools: list_docs,  │   │ tools: NONE           │
 │                   │        │        read_doc    │   │ knows ONLY its prompt │
 └───────┬───────────┘        └─────────┬──────────┘   │ + context             │
         └── findings: {claim, source_id, title, date, page} ──► coordinator ──┘
             (content kept separate from metadata)
```

## Run

```bash
# from the repo root
source .venv/bin/activate
cd 01-agentic-architecture-and-orchestration/1.3-subagent-invocation-and-context

python starter.py                         # your version
python starter.py --no-context            # your version, failure demo
python solution/solution.py               # reference (about 30 s, about 20 Haiku calls)
python solution/solution.py --no-context  # reference, failure demo
```
Reports are written to `output/`.

## Files

| File | What it is |
|------|-----------|
| `starter.py` | Your file. `TODO 1` to `TODO 6` match the tasks. Tool definitions, schemas, the `Task` tool and the checks are given. |
| `agent_utils.py` | Given: `ask()`, `ask_json()`, `run_tool_loop()` (your 1.1 loop, with an optional JSON `output_schema` for the final answer). |
| `mock_data.py` | Given: 5 made-up news articles (`N1`–`N5`) and 4 Nimbus internal documents (`D1`–`D4`), each with source metadata. |
| `solution/solution.py` | Reference implementation. |

---

## Tasks

### ☐ Task 1: Agent definitions with restricted tools
Define three agents (`news_researcher`, `doc_analyst`, `synthesizer`), each with a `description`, a `system` prompt and `allowed_tools`.

- **Why:** In the Agent SDK this is an `AgentDefinition`. The coordinator picks an agent from its **description**, so the description must say what the agent does and what it can't do. `allowed_tools` follows least privilege: the synthesizer gets none.
- **You should see:** The `Task` tool description (printed into the coordinator's tool list) lists the three agents with useful one-liners.

### ☐ Task 2: Spawn a subagent with only its allowed tools
Write `run_subagent(agent_type, prompt, context)`: give the subagent only its own tools and enforce that in code.

- **Why:** A subagent is a fresh agentic loop (1.1) with its own system prompt and tool set. Restricting tools is configuration **plus** a code check; hiding a tool is not the same as forbidding it.
- **You should see:** The news researcher only calls `search_news`; the doc analyst only calls the document tools.

### ☐ Task 3: Parallel spawning
In the coordinator loop, run **all** `Task` calls from one response at the same time, and return all results in one user message.

- **Why:** On the exam, "spawn subagents in parallel" means the coordinator emits **several `Task` tool calls in a single response**. Your code runs them concurrently. Spawning them across separate turns makes the work sequential for no reason.
- **You should see:** `Coordinator turn 1: spawning 2 subagent(s) in parallel`.

### ☐ Task 4: Explicit, structured context passing
(a) In `run_subagent`, append the `context` findings to the prompt as JSON. (b) In the coordinator, reject a synthesizer spawn that has no context.

- **Why:** **Subagents do not inherit the coordinator's conversation.** Whatever they need must be in the prompt. Passing findings as structured data (claim **separate from** source id, title, date, page) keeps attribution intact through synthesis.
- **You should see:** `Task(synthesizer) with 17 context findings` (the number varies), and every claim in the report cited like `[N2]` or `[D1 p.2]`.

### ☐ Task 5: Coordinator prompt = goals + quality criteria
Write `COORDINATOR_SYSTEM`: the goal, what a good report contains, and the facts of the system (subagents have no memory; independent work can run in parallel).

- **Why:** The exam prefers coordinator prompts that state **research goals and quality criteria** over step-by-step procedures. Goals let the coordinator adapt; a rigid script breaks when something unexpected comes back.
- **You should see:** The coordinator decides on its own to run both researchers first, then the synthesizer.

### ☐ Task 6: Test, then break it with `--no-context`
Run normally, then with `--no-context` (the coordinator spawns the synthesizer with an empty context and a bare prompt).

- **Why:** This is the exam's **"subagent output is poor → check what was passed to it"** case. The synthesizer is fine; the coordinator didn't give it anything to work with.
- **You should see:** `RESULT: PASS` normally. With `--no-context`: the synthesizer replies that it has no findings, the key facts and citations are missing, and `RESULT: FAIL`.

---

## What the reference run showed (Haiku 4.5)

```
### Coordinator turn 1: spawning 2 subagent(s) in parallel
  -> Task(news_researcher) with 0 context findings
  -> Task(doc_analyst) with 0 context findings
        search_news(...) x5        list_internal_docs() + read_internal_doc(...) x5
### Coordinator turn 2: spawning 1 subagent(s)
  -> Task(synthesizer) with 17 context findings
    ✅ independent subagents ran in parallel   ✅ >= 2 news / >= 2 internal docs cited
    ✅ no made-up source ids                   ✅ key facts present
RESULT: PASS
```

With `--no-context`:
```
  -> Task(synthesizer) with 0 context findings      (coordinator retries 3 more times)
synthesizer: "...no findings, sources, or research data have been provided in your prompt."
    ❌ >= 2 news sources cited  ❌ >= 2 internal docs cited  ❌ key facts present
RESULT: FAIL
```

### Lessons from building this

1. **The tool-less synthesizer can't fix a bad brief.** With no context it either asks for data or writes something generic. The research was fine; the hand-off wasn't. That's the exam's diagnosis order: **check the prompt/context the subagent got before blaming the subagent**.
2. **Guardrails go in code.** Rather than telling the coordinator "always pass context" in a longer prompt, `handle()` rejects a synthesizer spawn with empty context and returns an `is_error` result that says exactly what's missing (the 1.1 / 1.2 pattern).
3. **Structured output for researchers.** Forcing researchers to return `{claim, source_id, source_title, date, page}` JSON (structured outputs on the final turn) means the coordinator can copy findings into `context` without losing where they came from.

---

## Hints (open only when stuck)

<details><summary>Task 2: enforcing allowed tools</summary>

```python
def guarded(name):
    def call(**kwargs):
        if name not in allowed:
            raise PermissionError(f"{agent_type} is not allowed to use {name}")
        return TOOL_FUNCS[name](**kwargs)
    return call

tools = [TOOL_DEFS[t] for t in allowed]
funcs = {t: guarded(t) for t in allowed}
```
</details>

<details><summary>Task 3: running Task calls in parallel</summary>

```python
calls = [b for b in response.content if b.type == "tool_use"]
with ThreadPoolExecutor(max_workers=4) as pool:
    results = list(pool.map(handle, calls))   # map keeps the order
messages.append({"role": "user", "content": results})
```
</details>

<details><summary>Task 4: the context block and the guardrail</summary>

```python
if context:
    full_prompt += ("\n\nCONTEXT: findings from other agents (JSON; cite by source_id):\n"
                    + json.dumps(context, indent=1))
```
```python
if agent_type == "synthesizer" and not context and not no_context:
    return {"type": "tool_result", "tool_use_id": block.id, "is_error": True,
            "content": "Rejected: the synthesizer has no tools and no memory. "
                       "Pass every finding it needs in `context`."}
```
</details>

---

## Exam takeaways

- **`Task` is how a coordinator spawns subagents.** The coordinator's allowed tools must include `Task`; each subagent gets its own system prompt and **restricted** tool list (`AgentDefinition`).
- **No inherited context.** A subagent sees only its prompt. Pass prior findings **explicitly**, ideally as structured data with source metadata separate from content.
- **Parallel = several `Task` calls in one coordinator response**, not one per turn.
- **Coordinator prompts state goals and quality criteria**, not step-by-step procedures.
- **Poor subagent output → check the brief and context first.** In the `--no-context` demo, the synthesizer worked correctly with what it got; the coordinator failed to pass the findings.
