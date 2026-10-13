"""Topic 1.3 · Subagent Invocation & Context Passing (starter)

Fill in TODO 1 to TODO 6 in order. See README.md for the why and the hints.
Run:
    python starter.py               # normal run
    python starter.py --no-context  # demo: synthesizer spawned without context
"""

import argparse
import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent

from agent_utils import MODEL, client, run_tool_loop, text_of
from mock_data import (DOC_IDS, NEWS_IDS, ALL_SOURCE_IDS, list_internal_docs,
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
# TODO 1: agent definitions (description, system prompt, allowed tools)
#   The system prompts are given. Fill in for each agent:
#   - "description": one line the COORDINATOR reads to pick the agent
#     (what it does, and for the synthesizer: that it has no tools and only
#     sees what you pass in `context`)
#   - "allowed_tools": the least it needs. news_researcher -> search_news;
#     doc_analyst -> the two document tools; synthesizer -> none.
# ===========================================================================

AGENTS = {
    "news_researcher": {
        "description": "TODO",
        "system": "You are a news research subagent. You know only what is in your prompt and "
                  "what search_news returns. Make 3-5 focused searches. Every finding must be a "
                  "concrete fact from an article, with its source_id, title, date and page 0.",
        "allowed_tools": [],  # TODO
    },
    "doc_analyst": {
        "description": "TODO",
        "system": "You are an internal-document analysis subagent. You know only what is in your "
                  "prompt and what the document tools return. List the documents, read every page "
                  "relevant to the question, and return concrete facts with source_id, title, "
                  "date and page.",
        "allowed_tools": [],  # TODO
    },
    "synthesizer": {
        "description": "TODO",
        "system": "You are a synthesis subagent. You have no tools and no memory: use ONLY the "
                  "findings given in your prompt. Write a Markdown report with sections "
                  "'## Recommendation', '## Opportunities', '## Risks and blockers'. Cite every "
                  "factual sentence with its source id in square brackets, e.g. [N2] or [D1 p.2]. "
                  "Never state a fact that is not in the findings.",
        "allowed_tools": [],
    },
}


# ===========================================================================
# TODO 2 + TODO 4a: spawn a subagent with ONLY its allowed tools and explicit context
# ===========================================================================

def run_subagent(agent_type: str, prompt: str, context: list[dict]) -> str:
    agent = AGENTS[agent_type]
    allowed = agent["allowed_tools"]

    # TODO 2: give the subagent ONLY its allowed tools, and enforce it in code.
    #   - tools = [TOOL_DEFS[t] for t in allowed]
    #   - tool_functions: wrap each TOOL_FUNCS[t] so it raises PermissionError if the
    #     tool isn't in `allowed` (defence in depth: hiding a tool is not enforcing it)

    # TODO 4a: pass the context EXPLICITLY. Append it to the prompt as structured JSON
    #   (claim + source_id/title/date/page), labelled e.g. "CONTEXT: findings from
    #   other agents (cite by source_id)". The subagent inherits nothing else.
    full_prompt = prompt

    # Researchers (with tools) return FINDINGS_SCHEMA JSON; the synthesizer returns Markdown.
    #   return run_tool_loop(agent["system"], full_prompt, tools, tool_functions,
    #                        max_iterations=10, output_schema=FINDINGS_SCHEMA if allowed else None)
    raise NotImplementedError


# ===========================================================================
# Task 3 (given): the Task tool. Read its description: that is what the coordinator sees.
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
# TODO 5: the coordinator prompt: GOALS and QUALITY CRITERIA, not step-by-step
#   Say what a good final report looks like (both source types, which areas,
#   every claim keeps its source id) and the facts of the system (subagents have
#   no memory; independent work can run in parallel; reply DONE when the
#   synthesizer has returned the report). Don't script "first call X, then Y".
# ===========================================================================

COORDINATOR_SYSTEM = """TODO"""


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

        # TODO 4b: guardrail in code. If agent_type is "synthesizer", context is empty
        #   and we're not in the no_context demo, DON'T run it. Return an is_error
        #   tool_result telling the coordinator to pass the findings in `context`.

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
        # TODO 3: run ALL the Task calls from this response at the same time
        #   (ThreadPoolExecutor + handle), keeping their order. All results go back
        #   in ONE user message (the 1.1 rule).
        results = []

        messages.append({"role": "user", "content": results})

    log.warning("Coordinator hit MAX_COORDINATOR_TURNS=%d", MAX_COORDINATOR_TURNS)
    return state


# ===========================================================================
# TODO 6: run both modes and compare (check() is given):
#   python starter.py               -> PASS
#   python starter.py --no-context  -> FAIL. Why? Write your answer here: ...
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
    out = HERE / "output" / ("my_report_no_context.md" if args.no_context else "my_report.md")
    out.parent.mkdir(exist_ok=True)
    out.write_text(state["report"] or "(no report)")
    log.info("\nReport saved to %s", out.relative_to(HERE))
    log.info("\nRESULT: %s", "PASS" if check(state) else "FAIL")
