# Topic 1.1 · The Agentic Loop

Build a small agent with two tools (a calculator and a stubbed web search). You drive the loop yourself with `client.messages.create()` and use `stop_reason` to decide what happens next.

```
             ┌──────────────────────────────────────────────┐
             ▼                                              │
  messages ──► client.messages.create() ──► response        │
                                              │             │
                             response.stop_reason?          │
                     ┌────────────┼─────────────────┐       │
                "tool_use"    "end_turn"         anything   │
                     │            │               else      │
          run the tool(s),   return the text   log it and   │
          append assistant   (done ✅)         stop safely  │
          + tool_result ─────────────────────────────────────┘
```

## Setup

```bash
# from the repo root
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# ANTHROPIC_API_KEY is already exported in ~/.zshrc, so the client finds it.
echo ${ANTHROPIC_API_KEY:+key is set}

cd 01-agentic-architecture-and-orchestration/1.1-agentic-loop
python starter.py          # your work
python solution/solution.py  # reference, to compare
```

## Files

| File | What it is |
|------|-----------|
| `starter.py` | Your file. The `TODO 1` to `TODO 6` blocks match the tasks below. |
| `mock_data.py` | Fake search results for the web search stub. Nothing to do here. |
| `solution/solution.py` | Reference implementation. Try the tasks first. |

---

## Tasks

### ☐ Task 1: Register two tools
Set up a Claude API client with two tools: a **calculator** (takes `expression`, returns the result) and a **web search stub** (takes `query`, returns mock results).

- **Why:** With more than one tool, Claude has to pick the right one from context. That model-driven choice is central to agentic architecture.
- **You should see:** Two tool definitions, each with `name`, `description`, and an `input_schema` written as JSON Schema.

### ☐ Task 2: The loop and `stop_reason`
Implement the agentic loop: send a request to Claude and check `stop_reason` after every response.

- **Why:** The exam tests whether you branch on `stop_reason`, which is deterministic, or on content-type checks or parsing the text, which are unreliable.
- **You should see:** A `while` loop that calls `client.messages.create()` and checks `response.stop_reason` on each pass.

### ☐ Task 3: Handle `tool_use`
When `stop_reason == "tool_use"`: run the requested tool, build a `tool_result`, and append it to the conversation history.

- **Why:** This is the key handoff in the loop. The exam checks that you pull out the tool calls, run them, and send results back in the right message format.
- **You should see:** Two new messages per tool round: the assistant's full `response.content`, then a `user` message containing the `tool_result` block(s).

### ☐ Task 4: Handle `end_turn`
When `stop_reason == "end_turn"`: take the final text and return it.

- **Why:** `end_turn` is Claude's signal that the task is finished. Extracting the final text correctly closes the loop.
- **You should see:** The loop exits and returns the text content of the final response.

### ☐ Task 5: Test sequential tool calls
Use a prompt that needs several tool calls in order, for example "search for a value, then calculate with it". Check that the loop keeps going through every iteration.

- **Why:** Sequential calls test the whole loop lifecycle. The agent has to get one tool result, reason about it, decide to call another tool, and only then answer.
- **You should see:** At least two tool-call iterations before `end_turn`. The agent searches first, uses that result in a calculation, then gives the combined answer.

### ☐ Task 6: Safety iteration cap
Add a cap of **20** iterations as an upper bound. It is a fallback, not the main way the loop stops. Log a warning if it triggers.

- **Why:** The exam separates safety caps (fine as a fallback) from caps used as the main stopping mechanism (an anti-pattern). Your cap should never fire in normal use.
- **You should see:** A `MAX_ITERATIONS` constant, a counter that goes up each pass, and a warning log if the cap is hit. Normal queries finish through `stop_reason` long before 20.

---

## Hints (open only when stuck)

<details><summary>Task 1: tool definition shape</summary>

```python
{
    "name": "calculator",
    "description": "Evaluate an arithmetic expression. Use this for ANY math ...",
    "input_schema": {
        "type": "object",
        "properties": {
            "expression": {"type": "string", "description": "e.g. '(3 + 4) * 2'"}
        },
        "required": ["expression"],
    },
}
```
The `description` is what Claude reads to choose a tool, so say **when** to use it, not only what it does.
</details>

<details><summary>Task 2: the loop skeleton</summary>

```python
while True:
    response = client.messages.create(model=MODEL, max_tokens=..., tools=TOOLS, messages=messages)
    if response.stop_reason == "tool_use":
        ...
    elif response.stop_reason == "end_turn":
        ...
```
Don't use `if any(b.type == "text" ...)` or `if "final answer" in text` to decide whether to stop. That's the anti-pattern the exam looks for.
</details>

<details><summary>Task 3: message format for tool results</summary>

1. Append the **whole** `response.content` as the assistant turn. Don't keep only the tool_use blocks. Thinking and text blocks must go back too.
2. Put **all** tool results from that turn in **one** user message:
```python
{"role": "user", "content": [
    {"type": "tool_result", "tool_use_id": block.id, "content": "42"},
]}
```
3. `tool_use_id` must match `block.id`. If a tool fails, still return a result, with `"is_error": True`.
</details>

<details><summary>Task 4: getting the text</summary>

`response.content` is a list of blocks. Join the `.text` of the blocks where `block.type == "text"`.
</details>

<details><summary>Task 6: where the counter goes</summary>

`for iteration in range(1, MAX_ITERATIONS + 1): ...` and put the warning after the loop (Python's `for … else:` works well here). The loop body still leaves through `stop_reason`, and the cap only catches runaways.
</details>

---

## Exam takeaways

- The loop is driven by **`stop_reason`**. `tool_use` means continue, `end_turn` means done. Other values (`max_tokens`, `refusal`, `pause_turn`) need their own handling. Never silently treat them as done.
- The assistant turn goes back into history **unchanged** (`response.content`), followed by a user turn of `tool_result` blocks with matching `tool_use_id`s.
- Parallel tool calls: several `tool_use` blocks in one response lead to **one** user message with all the results.
- An iteration cap is a **safety net**, not the design. If it triggers, something is wrong and you should log it.
- Tool **descriptions** drive tool selection. Vague descriptions lead to wrong tool choices.
