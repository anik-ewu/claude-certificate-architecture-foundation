"""Topic 1.1 · The Agentic Loop (reference solution)

Run:  python solution/solution.py   (from the 01-agentic-loop folder)
"""

import ast
import json
import logging
import operator
import sys
from pathlib import Path

import anthropic

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from mock_data import search  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("agent")

MODEL = "claude-haiku-4-5"

# Task 6: safety net only. Normal runs end on stop_reason long before this.
MAX_ITERATIONS = 20


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.Pow: operator.pow, ast.Mod: operator.mod,
    ast.USub: operator.neg, ast.UAdd: operator.pos,
}


def calculator(expression: str) -> str:
    """Safely evaluate an arithmetic expression (no eval())."""
    def _eval(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
            return _OPS[type(node.op)](_eval(node.left), _eval(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
            return _OPS[type(node.op)](_eval(node.operand))
        raise ValueError(f"Unsupported expression: {ast.dump(node)}")

    return str(_eval(ast.parse(expression, mode="eval").body))


def web_search(query: str) -> str:
    """Stubbed web search: returns mock results as JSON text."""
    return json.dumps(search(query))


# ---------------------------------------------------------------------------
# Task 1: tool definitions
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "name": "calculator",
        "description": (
            "Evaluate an arithmetic expression and return the numeric result. "
            "Use this for ANY math instead of computing it yourself. "
            "Supports + - * / ** % and parentheses. Numbers only, no units or commas."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Arithmetic expression, e.g. '(48600000 / 312)'.",
                }
            },
            "required": ["expression"],
        },
    },
    {
        "name": "web_search",
        "description": (
            "Search the web for facts you don't already know, such as company figures, "
            "dates or statistics. Returns a list of results with title and snippet. "
            "Use this to look up values before doing calculations with them."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The search query."}
            },
            "required": ["query"],
        },
    },
]

TOOL_FUNCTIONS = {
    "calculator": calculator,
    "web_search": web_search,
}


def execute_tool(name: str, tool_input: dict) -> tuple[str, bool]:
    """Run a tool. Returns (result_text, is_error). Never raises."""
    func = TOOL_FUNCTIONS.get(name)
    if func is None:
        return f"Unknown tool: {name}", True
    try:
        return func(**tool_input), False
    except Exception as e:  # report the failure to Claude so it can recover
        return f"{type(e).__name__}: {e}", True


# ---------------------------------------------------------------------------
# Tasks 2 to 6: the agentic loop
# ---------------------------------------------------------------------------

def run_agent(user_prompt: str) -> str:
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from the environment
    messages = [{"role": "user", "content": user_prompt}]

    for iteration in range(1, MAX_ITERATIONS + 1):
        # Task 2: call the model and branch on stop_reason
        response = client.messages.create(
            model=MODEL,
            max_tokens=16000,
            tools=TOOLS,
            messages=messages,
        )
        log.info("iteration=%d stop_reason=%s", iteration, response.stop_reason)

        if response.stop_reason == "tool_use":
            # Task 3: append the full assistant turn unchanged (text, thinking, tool_use)
            messages.append({"role": "assistant", "content": response.content})

            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue
                result, is_error = execute_tool(block.name, block.input)
                log.info("  -> %s(%s) = %s%s", block.name, json.dumps(block.input),
                         result, "  [ERROR]" if is_error else "")
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                    "is_error": is_error,
                })

            # All results from this turn go in ONE user message
            messages.append({"role": "user", "content": tool_results})

        elif response.stop_reason == "end_turn":
            # Task 4: done, so return the final text
            return "".join(b.text for b in response.content if b.type == "text")

        else:
            # max_tokens / refusal / pause_turn: never silently treat these as success
            raise RuntimeError(f"Unexpected stop_reason: {response.stop_reason}")

    # Task 6: only reached if the loop never hit end_turn
    log.warning("MAX_ITERATIONS (%d) reached without end_turn; aborting.", MAX_ITERATIONS)
    raise RuntimeError("Agent exceeded iteration cap")


if __name__ == "__main__":
    # Task 5: needs search first, then a calculation based on the results
    prompt = (
        "Look up Nimbus Robotics' revenue and its number of employees, "
        "then calculate revenue per employee in dollars."
    )
    print("\nFINAL ANSWER:\n" + run_agent(prompt))
