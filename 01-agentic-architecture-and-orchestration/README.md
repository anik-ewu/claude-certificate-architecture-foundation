# 01 · Agentic Architecture & Orchestration

This domain covers how an agent actually runs: the loop that drives it, how control passes between the model and your code, and how you keep it safe and predictable.

## Topics

| # | Topic | Folder | Status |
|---|-------|--------|--------|
| 1.1 | The agentic loop (tool use + `stop_reason`) | [`1.1-agentic-loop/`](1.1-agentic-loop/) | ⬜ To do |
| 1.2 | Hub-and-spoke research coordinator (subagents, decomposition, refinement) | [`1.2-hub-and-spoke-coordinator/`](1.2-hub-and-spoke-coordinator/) | ⬜ To do |
| 1.3 | Subagent invocation & context passing (`Task` tool, allowed tools, parallel spawns) | [`1.3-subagent-invocation-and-context/`](1.3-subagent-invocation-and-context/) | ⬜ To do |
| 1.4 | Multi-step workflows: enforcement & handoff (prerequisite gates, structured handoff) | [`1.4-workflow-enforcement-and-handoff/`](1.4-workflow-enforcement-and-handoff/) | ⬜ To do |

More topics from this domain get added here as new subfolders (`1.3-…`, `1.4-…`), each with its own `README.md` (tasks), `starter.py` (your work), and `solution/` (reference to check against).

## How to work through a topic

1. Read the topic's `README.md`. Each task says what to build, **why** the exam cares, and **what you should see** when it's done.
2. Open `starter.py` and fill in the `TODO` blocks in order. They follow the task numbers.
3. Run it: `python starter.py`
4. Stuck? Read the **Hints** in the README first. Look at `solution/solution.py` only after you've tried.
5. Tick the checklist in the README and update the Status column above.
