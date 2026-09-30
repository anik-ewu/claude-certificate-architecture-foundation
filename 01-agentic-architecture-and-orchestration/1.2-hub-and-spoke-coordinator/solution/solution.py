"""Topic 1.2 · Hub-and-Spoke Research Coordinator (reference solution)

Run (from the 1.2-hub-and-spoke-coordinator folder):
    python solution/solution.py            # normal run
    python solution/solution.py --narrow   # demo of the narrow-decomposition failure
"""

import argparse
import json
import logging
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
from agent_utils import ask, ask_json, run_tool_loop  # noqa: E402
from mock_data import get_documents, search  # noqa: E402

logging.basicConfig(level=logging.WARNING, format="%(message)s")
log = logging.getLogger("agent")
log.setLevel(logging.INFO)

MIN_SUBTOPICS = 5
MAX_ROUNDS = 3            # refinement safety cap (like MAX_ITERATIONS in 1.1)
WELL_COVERED_FACTS = 3    # coverage threshold, enforced in code
EXPECTED = ["solar", "wind", "geothermal", "tidal", "biomass", "fusion"]  # Task 6 test


def parallel(fn, items: dict) -> dict:
    """Run fn(*args) for each {key: args} at the same time; return {key: result}."""
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {k: pool.submit(fn, *args) for k, args in items.items()}
    return {k: f.result() for k, f in futures.items()}


# ===========================================================================
# Task 1: the coordinator (the hub)
# ===========================================================================

COORDINATOR_SYSTEM = """You are the research coordinator in a hub-and-spoke system.
You are the only component that sees the whole task. You own:
- decomposition: splitting the topic into subtopics that cover its FULL breadth
- delegation: writing complete, self-contained briefs for subagents
  (they have no memory and see nothing except the brief you write)
- aggregation: judging whether the combined findings cover every subtopic,
  and sending targeted follow-ups for any gaps.
Subagents never talk to each other; everything flows through you."""


# ===========================================================================
# Task 2: broad task decomposition
# ===========================================================================

DECOMPOSE_SCHEMA = {
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

DECOMPOSE_RULES = f"""Rules:
- Cover the FULL breadth: widely deployed, scaling up, pilot, and experimental /
  long-term research categories (include ones whose place in the topic is
  debated but that are commonly discussed alongside it).
- Each subtopic is ONE distinct category, named after that category. No
  catch-all buckets like "Emerging technologies" or "Other".
- No cross-cutting themes (policy, markets, storage, grid integration).
- Aim for 6-10 subtopics (never fewer than {MIN_SUBTOPICS}).
- Give each one a short name, a one-line description and 2-3 broad overview
  questions (how it works, current status, main challenges)."""


def decompose(topic: str, must_cover: list[str] = ()) -> list[dict]:
    prompt = f'Break this research topic into subtopics: "{topic}"\n\n{DECOMPOSE_RULES}'
    subtopics = ask_json(COORDINATOR_SYSTEM, prompt, DECOMPOSE_SCHEMA)["subtopics"]

    # Validate in code: minimum breadth, plus any categories the requester requires.
    # The model saying "I covered everything" is not proof.
    for _ in range(2):
        names = [s["name"].lower() for s in subtopics]
        missing = [c for c in must_cover if not any(c in n for n in names)]
        if len(subtopics) >= MIN_SUBTOPICS and not missing:
            return subtopics
        feedback = f"Your decomposition had {len(subtopics)} subtopics"
        if missing:
            feedback += f" and is missing these required categories: {', '.join(missing)}"
        log.info("  (decomposition rejected: %s)", feedback)
        prompt += (f"\n\nPrevious answer: {[s['name'] for s in subtopics]}\n{feedback}. "
                   "Return the complete revised list with each required category as its own "
                   "subtopic, using the category word in the subtopic name.")
        subtopics = ask_json(COORDINATOR_SYSTEM, prompt, DECOMPOSE_SCHEMA)["subtopics"]
    raise RuntimeError("Decomposition is still too narrow after feedback")


# ===========================================================================
# Task 3: two subagents with explicit context passing
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
    """Everything the subagent needs, stated explicitly. It inherits nothing."""
    parts = [
        f"OVERALL RESEARCH GOAL: produce a report on '{topic}' that covers its full breadth.",
        f"YOUR ASSIGNED SUBTOPIC: {subtopic['name']}: {subtopic['description']}",
        "KEY QUESTIONS TO ANSWER:\n" + "\n".join(f"- {q}" for q in subtopic["key_questions"]),
    ]
    if prior_findings:
        parts.append("FINDINGS ALREADY GATHERED (don't repeat them, build on them):\n"
                     + "\n\n".join(prior_findings))
    if follow_up:
        parts.append(f"GAP THE COORDINATOR FOUND: {follow_up['gap']}\n"
                     "TARGETED QUERIES TO TRY:\n"
                     + "\n".join(f"- {q}" for q in follow_up["follow_up_queries"]))
    return "\n\n".join(parts)


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
    """One spoke round-trip: web search agent, then doc agent (given the web results)."""
    name = subtopic["name"]
    log.info("  -> [%s] web search subagent", name)
    web = web_search_subagent(build_brief(topic, subtopic, prior, follow_up))

    # Subagents can't see each other, so the coordinator passes the web
    # agent's output to the doc agent itself.
    log.info("  -> [%s] document analysis subagent", name)
    docs = document_analysis_subagent(
        build_brief(topic, subtopic, prior + [f"[web search agent]\n{web}"], follow_up),
        get_documents(name),
    )
    return f"[web search agent]\n{web}\n\n[document analysis agent]\n{docs}"


# ===========================================================================
# Task 4: aggregation and coverage evaluation
# ===========================================================================

SCORE = {"well_covered": 1.0, "partially_covered": 0.5, "missing": 0.0}

ASSESS_SCHEMA = {
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
    prompt = f"""Research topic: {topic}
Subtopic: {subtopic['name']}: {subtopic['description']}
Combined findings from both subagents:

{chr(10).join(findings) or "(nothing yet)"}

- specific_facts: list each distinct, concrete fact about THIS subtopic
  (a figure, a named project, a date, a named technology). Skip generic
  statements such as "X is a form of energy" and "no data found".
- gap: what an overview section on this subtopic still lacks (empty if nothing)
- follow_up_queries: 2-3 specific search queries that would fill the gap"""
    a = ask_json(COORDINATOR_SYSTEM, prompt, ASSESS_SCHEMA)
    n = len(a["specific_facts"])
    # The model lists the evidence; code applies the threshold
    a["status"] = ("well_covered" if n >= WELL_COVERED_FACTS
                   else "partially_covered" if n else "missing")
    a["subtopic"] = subtopic["name"]
    return a


def evaluate_coverage(topic: str, subtopics: list[dict],
                      findings: dict[str, list[str]]) -> tuple[list[dict], float]:
    """Aggregate: assess every subtopic (in parallel) and score overall coverage."""
    results = parallel(assess_subtopic,
                       {s["name"]: (topic, s, findings[s["name"]]) for s in subtopics})
    assessments = [results[s["name"]] for s in subtopics]
    pct = 100 * sum(SCORE[a["status"]] for a in assessments) / len(assessments)
    return assessments, pct


def print_coverage(assessments: list[dict], pct: float) -> None:
    icon = {"well_covered": "✅", "partially_covered": "🟡", "missing": "❌"}
    for a in assessments:
        gap = "" if a["status"] == "well_covered" else a["gap"][:60]
        log.info("    %s %-38s %d facts  %s", icon[a["status"]], a["subtopic"][:38],
                 len(a["specific_facts"]), gap)
    log.info("    coverage: %.0f%%", pct)


# ===========================================================================
# Task 5: iterative refinement loop
# ===========================================================================

def run_coordinator(topic: str, must_cover: list[str] = (), narrow: bool = False) -> str:
    log.info("\n### Decomposing: %s", topic)
    if narrow:
        # Deliberately bad decomposition, to reproduce the failure the exam describes
        subtopics = [
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

    for rnd in range(1, MAX_ROUNDS + 1):
        log.info("\n### Round %d: delegating %d subtopic(s) to the subagents", rnd, len(to_research))
        results = parallel(research_subtopic, {
            n: (topic, by_name[n], list(findings[n]), fu) for n, fu in to_research.items()
        })
        for n, text in results.items():
            findings[n].append(f"(round {rnd})\n{text}")

        log.info("### Round %d: coverage evaluation", rnd)
        assessments, pct = evaluate_coverage(topic, subtopics, findings)
        print_coverage(assessments, pct)
        if pct >= 100:
            break
        # Re-delegate only the gaps, with the coordinator's targeted queries
        to_research = {a["subtopic"]: a for a in assessments if a["status"] != "well_covered"}
    else:
        log.warning("MAX_ROUNDS (%d) reached with coverage at %.0f%%", MAX_ROUNDS, pct)

    return write_report(topic, subtopics, findings)


def write_report(topic: str, subtopics: list[dict], findings: dict[str, list[str]]) -> str:
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
# Task 6: test against the expected categories
# ===========================================================================

def check_expected(report: str) -> bool:
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
    if not ok:
        log.info("\n  Diagnosis: the coverage evaluator only scores the subtopics the coordinator "
                 "created. Missing categories point to the DECOMPOSITION, not the subagents.")
    return ok


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", default="renewable energy technologies")
    parser.add_argument("--narrow", action="store_true", help="demo the narrow-decomposition failure")
    args = parser.parse_args()

    report = run_coordinator(args.topic, must_cover=EXPECTED, narrow=args.narrow)

    out = HERE / "output" / ("report_narrow.md" if args.narrow else "report.md")
    out.parent.mkdir(exist_ok=True)
    out.write_text(report)
    log.info("\nReport saved to %s", out.relative_to(HERE))

    passed = check_expected(report)
    log.info("\nRESULT: %s", "PASS: all 6 categories covered" if passed else "FAIL")
