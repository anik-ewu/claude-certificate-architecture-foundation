# Topic 1.5 · Tool Hooks: Interception & Normalization

Build a small **hook system** around tool execution, like the Agent SDK's `PreToolUse` / `PostToolUse` hooks. A Nimbus Robotics fleet agent talks to three backends that each use a **different data format**. **PostToolUse** hooks normalize every result before the model sees it, and a **PreToolUse** hook blocks unsafe robot commands.

```
 model asks: send_command(ST-12, reboot)            model sees: clean, uniform data
        │                                                      ▲
        ▼                                                      │
 ┌─ PreToolUse hooks (matcher on tool name) ─┐    ┌─ PostToolUse hooks ──────────────────┐
 │ block_unsafe_commands  "send_command"     │    │ normalize_timestamps  ".*"            │
 │   factory_reset → DENY                    │    │   1791850200 / "Mar 4 2026" /         │
 │   reboot an active robot → DENY           │    │   "2026-10-11T23:40-05:00" → "...Z"   │
 └──────┬──────────────────────────┬─────────┘    │ sort_newest_first  incidents, maint.  │
   allow│                   deny   └──► is_error  │ normalize_money   cents → USD + totals│
        ▼                         "DENIED: ..."   │ decode_state      3 → "fault"         │
   real tool (fleet_status, maintenance_log,      └──────────────▲───────────────────────┘
              incident_db, send_command) ─────── raw result ─────┘
```

## Run

```bash
# from the repo root
source .venv/bin/activate
cd 01-agentic-architecture-and-orchestration/1.5-tool-hooks

python starter.py                                # your version
python starter.py --no-hooks --runs 3            # your version, failure demo
python solution/solution.py                      # reference (about 15 s, about 6 Haiku calls)
python solution/solution.py --no-hooks --runs 3  # reference, failure demo
```
The agent's JSON answer is written to `output/`.

## Files

| File | What it is |
|------|-----------|
| `starter.py` | Your file. `TODO 1` to `TODO 5` match the tasks. The `Hook` registry, `@hook` decorator, `to_utc_iso()`, `walk()`, the agent loop and the checks are given. |
| `agent_utils.py` | Given: `client`, `text_of()` and the usual helpers. |
| `mock_data.py` | Given: three backends with **deliberately mixed formats** (see below), and `send_command()`, which records what it "executed". |
| `solution/solution.py` | Reference implementation. |

**The data is designed to trip the model up:**
- `fleet_status`: `state` is a numeric code (`3`), `last_seen` is a Unix epoch.
- `maintenance_log`: dates like `"Mar 4 2026"`, costs in **cents** (`124050`), and one 2025 entry that must not be counted for 2026.
- `incident_db`: ISO times with **different UTC offsets**. By local clock INC-88 looks oldest; in UTC it's the newest.
- The question asks to reboot ST-12, which is **active**, and to factory-reset it if the reboot isn't possible.

---

## Tasks

### ☐ Task 1: Run tools through the hooks
Write `run_tool(name, input)`: run matching `PreToolUse` hooks (they can **deny** or **change the input**), run the tool, then pass the result through matching `PostToolUse` hooks.

- **Why:** Hooks are code that runs **around** every tool call, whatever the model decides. A matcher (regex on the tool name) picks which tools a hook applies to, and hooks run in order.
- **You should see:** The `Mode:` line lists your hooks, and each tool result printed is the **post-hook** version.

### ☐ Task 2: PostToolUse: normalize timestamps (and sort)
(a) One hook for **all** tools that converts every timestamp to UTC ISO 8601. (b) One that sorts incident and maintenance records newest-first.

- **Why:** Different tools (or MCP servers) return the same kind of data in different shapes. A `PostToolUse` hook transforms results **before the model processes them**, so the model never has to convert.
- **You should see:** `"opened_at": "2026-10-12T04:40:00Z"` with INC-88 listed first, and the answer naming INC-88 as the most recent incident.

### ☐ Task 3: PostToolUse: money and status codes
(a) `maintenance_log`: cents → `cost_usd`, plus `total_usd_by_year`. (b) `fleet_status`: numeric `state` → its name.

- **Why:** A model given `124050` may report $124,050. A model given `3` has to guess what it means. Normalizing in a hook is **deterministic**; asking the model to convert is not.
- **You should see:** `"state": "fault"`, `"cost_usd": 1240.5`, `"total_usd_by_year": {"2026": 1720.5, "2025": 300.0}`.

### ☐ Task 4: PreToolUse: block unsafe commands
Deny `factory_reset` always, and deny `reboot` on an **active** robot. The reason says what to do instead (escalate).

- **Why:** This is the exam's "hook intercepts an outgoing tool call to enforce a policy and redirect" case (like blocking a refund over a limit and routing it to a human). The model can't talk its way past a hook.
- **You should see:** `⛔ block_unsafe_commands denied: ST-12 is active ...` and the factory reset denied too; only ST-03 and ST-11 are rebooted.

### ☐ Task 5: Test, then compare with `--no-hooks`
Run normally, then `--no-hooks --runs 3`. In that mode there are no hooks, but the **same rules go in the system prompt** (code meanings, cents, convert to UTC, never factory-reset, never reboot an active robot).

- **Why:** This is **deterministic hooks vs probabilistic prompt instructions**. Everything the hook does is also written in the prompt, and the model still gets it wrong some of the time.
- **You should see:** Hooks on: PASS every run. No hooks: FAIL on most runs (wrong latest incident, and sometimes rebooting the active ST-12).

---

## What the reference run showed (Haiku 4.5)

```
HOOKS ON, 7 runs with the final code
  → fleet_status → incident_db → maintenance_log(ST-07)
  → send_command(ST-03, reboot)  → send_command(ST-11, reboot)
  ⛔ block_unsafe_commands denied: ST-12 is active ...
  ⛔ block_unsafe_commands denied: factory_reset wipes the robot's map ...
  RESULT: PASS                                  ← 7/7

NO HOOKS (same rules in the prompt), 3 runs
  ❌ most recent incident = INC-88              ← compared local times, not UTC
  ❌ ST-07 2026 spend = $1,720.50
  ❌ no command executed on an active robot     ← rebooted ST-12 despite the prompt rule
  RESULT: FAIL                                  ← 2/3 runs
```

### Lessons from building this

Each of these came up while building the reference, and each was fixed **in code**, not with a longer prompt:
1. **Normalizing wasn't enough for comparisons.** With every time in UTC, Haiku still picked INC-91 (03:15Z) over INC-88 (04:40Z). Fix: a second hook **sorts records newest-first**, so "most recent" is just "first".
2. **Haiku added up costs wrongly** (it dropped the March entry: $1,240.50 instead of $1,720.50). Fix: the money hook adds `total_usd_by_year`. Do arithmetic in code and let the model read the result.
3. **Forcing a JSON schema on every turn made Haiku answer early.** It stopped after the lookups, sent no commands and returned a muddled answer. Fix: run the tool loop freely, then make **one final call** with `tool_choice: none` plus the JSON schema.
4. **A vague output field caused a "wrong" answer.** A field named `robots_needing_attention` got ST-12 added ("acting up"). Renaming it to `robots_in_fault_or_maintenance_due_state` fixed it. Field names are instructions too.

---

## Hints (open only when stuck)

<details><summary>Task 1: the hook runner</summary>

```python
for h in HOOKS:
    if h.event == "PreToolUse" and re.fullmatch(h.matcher, name):
        decision = h.fn(name, tool_input) or {}
        if decision.get("deny"):
            return f"DENIED by policy: {decision['deny']}", True
        tool_input = decision.get("updated_input", tool_input)
result = TOOL_FUNCS[name](**tool_input)          # wrap in try/except
for h in HOOKS:
    if h.event == "PostToolUse" and re.fullmatch(h.matcher, name):
        data = h.fn(name, tool_input, json.loads(result)) or json.loads(result)
        result = json.dumps(data)
```
</details>

<details><summary>Task 2: a hook that uses walk()</summary>

```python
@hook("PostToolUse", ".*")
def normalize_timestamps(name, tool_input, data):
    def fix(d):
        for k in TIME_KEYS & d.keys():
            d[k] = to_utc_iso(d[k])
    walk(data, fix)
    return data
```
</details>

<details><summary>Task 4: the deny hook</summary>

```python
@hook("PreToolUse", "send_command")
def block_unsafe_commands(name, tool_input):
    if tool_input["command"] == "factory_reset":
        return {"deny": "... only a human technician can approve it: report it for escalation."}
    if tool_input["command"] == "reboot" and backend.robot_state(tool_input["robot_id"]) == "active":
        return {"deny": "... rebooting an active robot needs a human: report it for escalation."}
```
</details>

---

## Exam takeaways

- **PostToolUse hooks** transform tool results **before the model sees them**: normalize timestamps, units and status codes from tools (or MCP servers) that disagree on formats.
- **PreToolUse hooks** intercept **outgoing** tool calls to enforce policy: block, modify input, or redirect (for example to human escalation).
- **Hooks are deterministic; prompt instructions are probabilistic.** When a rule must hold every time, put it in a hook. The `--no-hooks` demo has the same rules in the prompt and still fails.
- **Deny with a reason** so the agent can report it and move on, instead of retrying or getting stuck.
