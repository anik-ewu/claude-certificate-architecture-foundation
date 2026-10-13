"""Topic 1.3 · Subagent Invocation & Context Passing (reference solution)

Run (from the 1.3-subagent-invocation-and-context folder):
    python solution/solution.py               # normal run
    python solution/solution.py --no-context  # demo: subagent spawned without context
"""

import argparse
import json
import logging
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
from agent_utils import MODEL, client, run_tool_loop, text_of  # noqa: E402
from mock_data import (DOC_IDS, NEWS_IDS, ALL_SOURCE_IDS, list_internal_docs,  # noqa: E402
                       read_internal_doc, search_news)

logging.basicConfig(level=logging.WARNING, format="%(message)s")
log = logging.getLogger("agent")
log.setLevel(logging.INFO)

QUESTION = ("Should Nimbus Robotics launch its Stratus warehouse robot in Germany in 2027? "
            "Give a recommendation with the main opportunities, risks and blockers.")
MAX_COORDINATOR_TURNS = 8   # safety cap, as in 1.1
KEY_FACTS = ["kestrel", "2023/1230", "hamburg"]   # Task 6 check: one per source area

# Tools that subagents may be allowed to use (definitions only; the agent
# definitions below decide who gets which).
TOOL_DEFS = {
    "search_news": {
        "name": "search_news",
        "description": "Search recent news articles. Returns up to 3 articles as JSON with "
                       "source_id, title, outlet, date and text. Use specific keywords.",
        "input_schema": {"type": "object",
                         "properties": {"query": {"type": "string"}},
                         "required": ["query"]},
    },
    "list_internal_docs": {
        "name": "list_internal_docs",
        "description": "List Nimbus Robotics internal documents (doc_id, title, date, pages). "
                       "Call this first to see what exists.",
        "input_schema": {"type": "object", "properties": {}},
    },
    "read_internal_doc": {
        "name": "read_internal_doc",
        "description": "Read one page of an internal document by doc_id (e.g. 'D1').",
        "input_schema": {"type": "object",
                         "properties": {"doc_id": {"type": "string"},
                                        "page": {"type": "integer", "default": 1}},
                         "required": ["doc_id"]},
    },
}
TOOL_FUNCS = {"search_news": search_news, "list_internal_docs": list_internal_docs,
              "read_internal_doc": read_internal_doc}

# Structured findings: the content (claim) kept separate from its metadata.
FINDINGS_SCHEMA = {
    "type": "object",
    "properties": {
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "claim": {"type": "string"},
                    "source_id": {"type": "string"},
                    "source_title": {"type": "string"},
                    "date": {"type": "string"},
                    "page": {"type": "integer"},
                },
                "required": ["claim", "source_id", "source_title", "date", "page"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["findings"],
    "additionalProperties": False,
}


# ===========================================================================
# Task 1: agent definitions (description, system prompt, allowed tools)
# ===========================================================================

AGENTS = {
    "news_researcher": {
        "description": "Searches recent news (competitors, market size, regulation, labour market). "
                       "Returns findings with source metadata.",
        "system": "You are a news research subagent. You know only what is in your prompt and "
                  "what search_news returns. Make 3-5 focused searches. Every finding must be a "
                  "concrete fact from an article, with its source_id, title, date and page 0.",
        "allowed_tools": ["search_news"],
    },
    "doc_analyst": {
        "description": "Reads Nimbus Robotics internal documents (pilot results, sales, compliance, "
                       "unit economics). Returns findings with source metadata.",
        "system": "You are an internal-document analysis subagent. You know only what is in your "
                  "prompt and what the document tools return. List the documents, read every page "
                  "relevant to the question, and return concrete facts with source_id, title, "
                  "date and page.",
        "allowed_tools": ["list_internal_docs", "read_internal_doc"],
    },
    "synthesizer": {
        "description": "Writes the final recommendation report. Has NO tools: it can only use the "
                       "findings you pass in `context`.",
        "system": "You are a synthesis subagent. You have no tools and no memory: use ONLY the "
                  "findings given in your prompt. Write a Markdown report with sections "
                  "'## Recommendation', '## Opportunities', '## Risks and blockers'. Cite every "
                  "factual sentence with its source id in square brackets, e.g. [N2] or [D1 p.2]. "
                  "Never state a fact that is not in the findings.",
        "allowed_tools": [],
    },
}


# ===========================================================================
# Task 2: spawn a subagent with ONLY its allowed tools
# ===========================================================================

def run_subagent(agent_type: str, prompt: str, context: list[dict]) -> str:
    agent = AGENTS[agent_type]
    allowed = agent["allowed_tools"]

    def guarded(name):
        # Enforced in code, not just by hiding the tool: a subagent can never
        # run a tool outside its definition.
        def call(**kwargs):
            if name not in allowed:
                raise PermissionError(f"{agent_type} is not allowed to use {name}")
            return TOOL_FUNCS[name](**kwargs)
        return call

    # Task 4: context is passed explicitly, as structured data, inside the prompt.
    # The subagent inherits nothing from the coordinator's conversation.
    full_prompt = prompt
    if context:
        full_prompt += ("\n\nCONTEXT: findings from other agents (JSON; cite by source_id):\n"
                        + json.dumps(context, indent=1))

    schema = FINDINGS_SCHEMA if allowed else None   # researchers return structured findings
    return run_tool_loop(
        agent["system"], full_prompt,
        [TOOL_DEFS[t] for t in allowed], {t: guarded(t) for t in allowed},
        max_iterations=10, output_schema=schema,
    )


# ===========================================================================
# Task 3: the Task tool + a coordinator that spawns subagents in parallel
# ===========================================================================

TASK_TOOL = {
    "name": "Task",
    "description": (
        "Spawn a subagent. It starts with NO memory of this conversation: it sees only "
        "`prompt` and `context`. Call this several times in ONE response to run independent "
        "subagents in parallel.\nAgent types:\n"
        + "\n".join(f"- {k}: {v['description']}" for k, v in AGENTS.items())
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "agent_type": {"type": "string", "enum": list(AGENTS)},
            "prompt": {"type": "string",
                       "description": "Complete, self-contained instructions: goal, scope, what to return."},
            "context": {
                "type": "array",
                "description": "Findings this subagent needs, copied exactly from earlier subagent "
                               "results (claim + source metadata). Required for the synthesizer.",
                "items": FINDINGS_SCHEMA["properties"]["findings"]["items"],
            },
        },
        "required": ["agent_type", "prompt", "context"],
    },
}

# ===========================================================================
# Task 5: the coordinator prompt: goals and quality criteria, not step-by-step
# ===========================================================================

COORDINATOR_SYSTEM = """You coordinate subagents to answer a business question.
Your only tool is Task, which spawns a subagent.

Goal: a sourced recommendation that a manager can act on.
Quality criteria for the final report:
- uses evidence from BOTH external news and Nimbus internal documents
- covers market opportunity, competition, regulation/compliance and pilot results
- every factual claim keeps its source id; nothing is invented

Subagents have no memory and cannot see this conversation or each other.
Whatever a subagent needs must be in its prompt or its context.
Independent research can run in parallel (several Task calls in one response).
When the synthesizer has returned the report, reply with exactly: DONE"""


def run_coordinator(question: str, no_context: bool = False) -> dict:
    state = {"report": None, "max_parallel": 0, "spawns": []}
    messages = [{"role": "user", "content": question}]

    def handle(block) -> dict:
        args = block.input
        agent_type, context = args["agent_type"], args.get("context") or []
        if no_context and agent_type == "synthesizer":
            # Demo: the coordinator assumes the subagent "already knows" what it found
            context, args = [], {**args, "prompt": "Write the final report for the question."}
        log.info("  -> Task(%s) with %d context findings", agent_type, len(context))
        state["spawns"].append((agent_type, len(context)))

        # Task 4 guardrail: a tool-less subagent with no context can only invent things.
        if agent_type == "synthesizer" and not context and not no_context:
            return {"type": "tool_result", "tool_use_id": block.id, "is_error": True,
                    "content": "Rejected: the synthesizer has no tools and no memory. Pass every "
                               "finding it needs in `context` (copy them from the research results)."}
        try:
            out, err = run_subagent(agent_type, args["prompt"], context), False
        except Exception as e:
            out, err = f"{type(e).__name__}: {e}", True
        if agent_type == "synthesizer" and not err:
            state["report"] = out
        return {"type": "tool_result", "tool_use_id": block.id, "content": out, "is_error": err}

    for turn in range(1, MAX_COORDINATOR_TURNS + 1):
        response = client.messages.create(
            model=MODEL, max_tokens=8000, system=COORDINATOR_SYSTEM,
            tools=[TASK_TOOL], messages=messages,   # coordinator's allowed tools: Task only
        )
        if response.stop_reason == "end_turn":
            log.info("\nCoordinator: %s", text_of(response)[:200])
            return state
        if response.stop_reason != "tool_use":
            raise RuntimeError(f"Unexpected stop_reason: {response.stop_reason}")

        messages.append({"role": "assistant", "content": response.content})
        calls = [b for b in response.content if b.type == "tool_use"]
        log.info("\n### Coordinator turn %d: spawning %d subagent(s)%s", turn, len(calls),
                 " in parallel" if len(calls) > 1 else "")
        state["max_parallel"] = max(state["max_parallel"], len(calls))
        # All Task calls from one response run at the same time; results go back
        # together in ONE user message, in the same order (1.1 rule).
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(handle, calls))
        messages.append({"role": "user", "content": results})

    log.warning("Coordinator hit MAX_COORDINATOR_TURNS=%d", MAX_COORDINATOR_TURNS)
    return state


# ===========================================================================
# Task 6: check the report
# ===========================================================================

def check(state: dict) -> bool:
    report = state["report"] or ""
    cited = set(re.findall(r"\b([ND]\d)\b", report))
    fake = cited - ALL_SOURCE_IDS
    lower = report.lower()
    checks = {
        "synthesizer produced a report": bool(report),
        "independent subagents ran in parallel": state["max_parallel"] >= 2,
        ">= 2 news sources cited": len(cited & NEWS_IDS) >= 2,
        ">= 2 internal docs cited": len(cited & DOC_IDS) >= 2,
        "no made-up source ids": not fake,
        "key facts present (" + ", ".join(KEY_FACTS) + ")": all(k in lower for k in KEY_FACTS),
    }
    log.info("\n### Checks")
    for name, ok in checks.items():
        log.info("    %s %s", "✅" if ok else "❌", name)
    log.info("    cited: %s", ", ".join(sorted(cited)) or "(none)")
    if not all(checks.values()):
        log.info("\n  Diagnosis: a subagent only knows its prompt. If the report lacks facts the "
                 "research found, check what the coordinator PASSED to the synthesizer.")
    return all(checks.values())


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-context", action="store_true",
                        help="demo: spawn the synthesizer without passing findings")
    args = parser.parse_args()

    state = run_coordinator(QUESTION, no_context=args.no_context)
    out = HERE / "output" / ("report_no_context.md" if args.no_context else "report.md")
    out.parent.mkdir(exist_ok=True)
    out.write_text(state["report"] or "(no report)")
    log.info("\nReport saved to %s", out.relative_to(HERE))
    log.info("\nRESULT: %s", "PASS" if check(state) else "FAIL")
