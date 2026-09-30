"""Topic 1.2 · Hub-and-Spoke Research Coordinator (starter)

Fill in TODO 1 to TODO 6 in order. See README.md for the why and the hints.
Run:
    python starter.py            # normal run
    python starter.py --narrow   # narrow-decomposition failure demo
"""

import argparse
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from agent_utils import ask, ask_json, run_tool_loop
from mock_data import get_documents, search

logging.basicConfig(level=logging.WARNING, format="%(message)s")
log = logging.getLogger("agent")
log.setLevel(logging.INFO)

HERE = Path(__file__).resolve().parent
MIN_SUBTOPICS = 5
MAX_ROUNDS = 3            # refinement safety cap (like MAX_ITERATIONS in 1.1)
WELL_COVERED_FACTS = 3    # coverage threshold, enforced in code
EXPECTED = ["solar", "wind", "geothermal", "tidal", "biomass", "fusion"]


def parallel(fn, items: dict) -> dict:
    """Given. Run fn(*args) for each {key: args} at the same time; return {key: result}."""
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {k: pool.submit(fn, *args) for k, args in items.items()}
    return {k: f.result() for k, f in futures.items()}


# ===========================================================================
# TODO 1: the coordinator's system prompt
#   Define the hub's role: it owns decomposition, delegation (writing complete
#   briefs for subagents that have NO memory) and aggregation/gap-filling.
#   Subagents never talk to each other.
# ===========================================================================

COORDINATOR_SYSTEM = """TODO"""


# ===========================================================================
# TODO 2: broad task decomposition
# ===========================================================================

DECOMPOSE_SCHEMA = {  # given
    "type": "object",
    "properties": {
        "subtopics": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "key_questions": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["name", "description", "key_questions"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["subtopics"],
    "additionalProperties": False,
}

# TODO 2a: write rules that push for FULL breadth. Think about: maturity stages
#   (deployed -> experimental), no catch-all buckets, no cross-cutting themes,
#   6-10 subtopics, 2-3 broad key questions each.
DECOMPOSE_RULES = """TODO"""


def decompose(topic: str, must_cover: list[str] = ()) -> list[dict]:
    prompt = f'Break this research topic into subtopics: "{topic}"\n\n{DECOMPOSE_RULES}'
    subtopics = ask_json(COORDINATOR_SYSTEM, prompt, DECOMPOSE_SCHEMA)["subtopics"]

    # TODO 2b: validate IN CODE (at most 2 retries):
    #   - at least MIN_SUBTOPICS subtopics
    #   - every word in must_cover appears in some subtopic name (lowercase)
    #   If either fails: log it, append feedback naming what's missing to the
    #   prompt, and call ask_json again. Raise if it still fails.
    return subtopics


# ===========================================================================
# TODO 3: two subagents with explicit context passing
# ===========================================================================

WEB_SEARCH_SYSTEM = """You are a web research subagent. You only know what is in the
brief below plus what the web_search tool returns. Make at most 2 searches.
Report only facts found in search results, as concise bullets that name the
source title. If results are thin, say clearly what is missing."""

DOC_ANALYSIS_SYSTEM = """You are a document analysis subagent. You only know what is in
the brief below, including the documents pasted into it. Analyse the documents
for the assigned subtopic as concise bullets. If no documents were provided,
say so in one line and don't invent content."""

WEB_SEARCH_TOOL = {
    "name": "web_search",
    "description": "Search the web. Returns a JSON list of {title, snippet}. "
                   "Specific queries return more detailed results than broad ones.",
    "input_schema": {
        "type": "object",
        "properties": {"query": {"type": "string", "description": "Search query"}},
        "required": ["query"],
    },
}


def build_brief(topic: str, subtopic: dict, prior_findings: list[str],
                follow_up: dict | None = None) -> str:
    # TODO 3a: return ONE string with everything the subagent needs:
    #   - the overall research goal (the topic)
    #   - its assigned subtopic name + description
    #   - its key questions
    #   - prior findings (if any): "don't repeat, build on them"
    #   - the follow-up (if any): follow_up["gap"] and follow_up["follow_up_queries"]
    #   Ask yourself: if this string were the ONLY thing you knew, could you do the job?
    raise NotImplementedError


def web_search_subagent(brief: str) -> str:
    return run_tool_loop(
        WEB_SEARCH_SYSTEM, brief, [WEB_SEARCH_TOOL],
        {"web_search": lambda query: json.dumps(search(query))},
        max_iterations=4,
    )


def document_analysis_subagent(brief: str, documents: list[str]) -> str:
    docs = "\n\n".join(documents) if documents else "(no documents available)"
    return ask(DOC_ANALYSIS_SYSTEM, f"{brief}\n\nDOCUMENTS:\n{docs}", max_tokens=1500)


def research_subtopic(topic: str, subtopic: dict, prior: list[str],
                      follow_up: dict | None) -> str:
    # TODO 3b:
    #   1. call web_search_subagent with a brief for this subtopic
    #   2. call document_analysis_subagent with a brief whose prior findings ALSO
    #      include the web agent's output (the coordinator relays it, because
    #      subagents can't see each other), plus get_documents(subtopic["name"])
    #   3. return both results in one string, labelled by agent
    raise NotImplementedError


# ===========================================================================
# TODO 4: aggregation and coverage evaluation
# ===========================================================================

SCORE = {"well_covered": 1.0, "partially_covered": 0.5, "missing": 0.0}

ASSESS_SCHEMA = {  # given
    "type": "object",
    "properties": {
        "specific_facts": {"type": "array", "items": {"type": "string"}},
        "gap": {"type": "string"},
        "follow_up_queries": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["specific_facts", "gap", "follow_up_queries"],
    "additionalProperties": False,
}


def assess_subtopic(topic: str, subtopic: dict, findings: list[str]) -> dict:
    # TODO 4a: ask_json(COORDINATOR_SYSTEM, prompt, ASSESS_SCHEMA) where the prompt
    #   gives the subtopic + its combined findings and asks for: specific_facts
    #   (concrete facts only), gap, follow_up_queries.
    #   Then set a["status"] IN CODE from len(specific_facts):
    #   >= WELL_COVERED_FACTS -> well_covered, >= 1 -> partially_covered, else missing.
    #   Set a["subtopic"] = subtopic["name"] and return a.
    raise NotImplementedError


def evaluate_coverage(topic: str, subtopics: list[dict],
                      findings: dict[str, list[str]]) -> tuple[list[dict], float]:
    # TODO 4b: run assess_subtopic for every subtopic (use parallel()), then
    #   compute coverage % = 100 * sum(SCORE[status]) / number of subtopics.
    #   Return (assessments in subtopic order, pct).
    raise NotImplementedError


def print_coverage(assessments: list[dict], pct: float) -> None:  # given
    icon = {"well_covered": "✅", "partially_covered": "🟡", "missing": "❌"}
    for a in assessments:
        gap = "" if a["status"] == "well_covered" else a["gap"][:60]
        log.info("    %s %-38s %d facts  %s", icon[a["status"]], a["subtopic"][:38],
                 len(a["specific_facts"]), gap)
    log.info("    coverage: %.0f%%", pct)


# ===========================================================================
# TODO 5: iterative refinement loop
# ===========================================================================

def run_coordinator(topic: str, must_cover: list[str] = (), narrow: bool = False) -> str:
    log.info("\n### Decomposing: %s", topic)
    if narrow:
        subtopics = [  # deliberately bad decomposition, for the failure demo
            {"name": "Solar", "description": "Solar power", "key_questions": ["Status and cost?"]},
            {"name": "Wind", "description": "Wind power", "key_questions": ["Status and cost?"]},
        ]
    else:
        subtopics = decompose(topic, must_cover)
    for s in subtopics:
        log.info("  - %s", s["name"])

    by_name = {s["name"]: s for s in subtopics}
    findings: dict[str, list[str]] = {n: [] for n in by_name}
    to_research: dict[str, dict | None] = {n: None for n in by_name}  # name -> follow-up

    # TODO 5: for rnd in 1..MAX_ROUNDS:
    #   1. research every subtopic in to_research (parallel + research_subtopic),
    #      passing a copy of its findings so far and its follow-up
    #   2. append each result to findings[name]
    #   3. evaluate_coverage + print_coverage
    #   4. if pct >= 100: stop
    #   5. else set to_research = {name: assessment} for subtopics NOT well_covered
    #      (re-delegate ONLY the gaps, with the targeted follow-up queries)
    #   If MAX_ROUNDS runs out, log.warning(...).

    return write_report(topic, subtopics, findings)


def write_report(topic: str, subtopics: list[dict], findings: dict[str, list[str]]) -> str:  # given
    material = "\n\n".join(f"=== {s['name']} ===\n" + "\n\n".join(findings[s["name"]])
                           for s in subtopics)
    return ask(
        "You write clear, factual research reports in Markdown.",
        f"Write a research report on '{topic}'. Use one '## <subtopic name>' section per "
        f"subtopic, in this order: {', '.join(s['name'] for s in subtopics)}. "
        f"Use only the findings below, and keep each section substantive but concise.\n\n{material}",
        max_tokens=8000,
    )


# ===========================================================================
# TODO 6: test. Run both modes and compare the results:
#   python starter.py           -> expect PASS, all 6 categories have a section
#   python starter.py --narrow  -> coverage says 100%, yet 4 categories are missing.
#   Why? Write your answer here: ...
# ===========================================================================

def check_expected(report: str) -> bool:  # given
    headings = [line.lower() for line in report.splitlines() if line.startswith("#")]
    body = report.lower()
    log.info("\n### Check against expected categories")
    ok = True
    for kw in EXPECTED:
        if any(kw in h for h in headings):
            status = "✅ own section"
        elif kw in body:
            status, ok = "🟡 mentioned only", False
        else:
            status, ok = "❌ missing", False
        log.info("    %-11s %s", kw, status)
    return ok


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", default="renewable energy technologies")
    parser.add_argument("--narrow", action="store_true")
    args = parser.parse_args()

    report = run_coordinator(args.topic, must_cover=EXPECTED, narrow=args.narrow)
    out = HERE / "output" / ("my_report_narrow.md" if args.narrow else "my_report.md")
    out.parent.mkdir(exist_ok=True)
    out.write_text(report)
    log.info("\nReport saved to %s", out.relative_to(HERE))
    log.info("\nRESULT: %s", "PASS" if check_expected(report) else "FAIL")
