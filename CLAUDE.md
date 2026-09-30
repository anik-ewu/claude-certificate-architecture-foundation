# Claude Certified Architect – Foundations: study repo

A hands-on repo for preparing for the Claude Architect certificate. The user gives the tasks for each topic; Claude turns them into a folder the user can work through and complete.

## Preferences

- **Model: always `claude-haiku-4-5`** (the cheapest). This is practice and testing, so keep cost low. Use a bigger model only if the user asks for one.
  - Haiku 4.5 doesn't take `thinking: {type: "adaptive"}`. Leave `thinking` out.
- **Language:** Python, using the official `anthropic` SDK (`client.messages.create()`).
- **API key:** `ANTHROPIC_API_KEY` is exported in `~/.zshrc`. Use `anthropic.Anthropic()` with no key in the code. Never hardcode or commit a key.
- **Teaching style:** explain step by step and link each step to the task it covers. Always give the exact command to run. At the end, show a table of task status (done / verified).
- **Verify:** run the reference solution against the real API before saying a topic is done.
- **Git:** as soon as a topic's solution is created (and verified), commit it and push to `origin main` right away — no need to ask. One commit per topic. Otherwise, don't commit unless the user asks.

## Folder structure

```
NN-<exam-domain-slug>/                  one folder per exam section (e.g. 01-agentic-architecture-and-orchestration)
├── README.md                           list of topics in that section + status column (⬜ / ✅)
└── <S>.<T>-<topic-slug>/               one subfolder per topic, numbered by section.topic (e.g. 1.1-agentic-loop, 1.2-…)
    ├── README.md                       diagram, setup + run commands, tasks as a ☐ checklist
    │                                   (each task: what to build / **Why** / **You should see**),
    │                                   collapsible <details> hints, "Exam takeaways"
    ├── starter.py                      the user's practice file: TODO N blocks, one per task number
    ├── <helpers>.py                    mock data / support code the user doesn't need to write
    ├── output/                         generated reports (gitignored)
    └── solution/solution.py            finished reference, with "Task N" comments
```

- Section folders: `01-`, `02-`…; topic folders: `1.1-`, `1.2-`… (section.topic, as the user numbers them); kebab-case slugs.
- Give the user support code that isn't the point of the exercise (safe calculator, mock data), so they can focus on the concept being tested.
- Use made-up data in mocks (e.g. the fictional "Nimbus Robotics") so the model has to call the tools.
- Put the exam angle in each task: which pattern is right and which is the anti-pattern.
- Where a topic can fail in an exam-relevant way, add a demo flag (e.g. `--narrow`) that reproduces the failure.
- Haiku is less reliable than larger models. When it misbehaves, fix it with **code-side validation** (check the output and send specific feedback), not longer prompts, and write the lesson into the topic README ("Lessons from building this").
- Starter files: give the boilerplate (schemas, printing, report writing), and leave TODOs only for the concept being tested.

## Setup / run

```bash
# repo root
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cd NN-<section>/<S>.<T>-<topic>
python starter.py            # the user's version
python solution/solution.py  # reference
```

`.venv/`, `__pycache__/`, `.env` are gitignored.

## Progress

| Section | Topic | Status |
|---|---|---|
| 01 Agentic Architecture & Orchestration | 1.1 Agentic loop (tools + `stop_reason`, cap 20) | Solution done and verified; the user is working on `starter.py` |
| 01 Agentic Architecture & Orchestration | 1.2 Hub-and-spoke research coordinator | Solution verified (PASS; `--narrow` demo FAILs as intended); starter ready |
