"""Topic 1.1 · The Agentic Loop (starter)

Fill in TODO 1 to TODO 6 in order. See README.md for the why and the hints.
Run:  python starter.py
"""

import ast
import json
import logging
import operator

import anthropic

from mock_data import search

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("agent")

MODEL = "claude-haiku-4-5"

# TODO 6: add a MAX_ITERATIONS constant (20).


# ---------------------------------------------------------------------------
# Tool implementations (given, so you can focus on the loop)
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
# TODO 1: Tool definitions
#   Write two tool definitions, "calculator" and "web_search". Each needs
#   name, description and input_schema (JSON Schema). Say in the description
#   WHEN Claude should use the tool.
# ---------------------------------------------------------------------------

TOOLS = [
    # {"name": "calculator", "description": "...", "input_schema": {...}},
    # {"name": "web_search", "description": "...", "input_schema": {...}},
]

# Maps tool name -> Python function. Used when Claude asks for a tool.
TOOL_FUNCTIONS = {
    "calculator": calculator,
    "web_search": web_search,
}


def execute_tool(name: str, tool_input: dict) -> tuple[str, bool]:
    """Run a tool. Returns (result_text, is_error)."""
    # TODO 3a: look up the function in TOOL_FUNCTIONS, call it with **tool_input,
    #   and return (result, False). On an unknown tool or an exception, return
    #   (error message, True). Don't crash the loop.
    raise NotImplementedError


def run_agent(user_prompt: str) -> str:
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from the environment
    messages = [{"role": "user", "content": user_prompt}]

    # TODO 2: the agentic loop
    #   Call client.messages.create(model=MODEL, max_tokens=16000,
    #   tools=TOOLS, messages=messages) and branch on response.stop_reason.
    #
    # TODO 6: make the loop bounded by MAX_ITERATIONS. Keep a counter and
    #   log.warning(...) if the cap is hit. stop_reason must still be the
    #   normal way out.

    while True:
        response = ...  # TODO 2

        log.info("stop_reason=%s", response.stop_reason)

        if response.stop_reason == "tool_use":
            # TODO 3b:
            #   1. Append the assistant turn: {"role": "assistant", "content": response.content}
            #   2. For each block where block.type == "tool_use": log it, run
            #      execute_tool(block.name, block.input), and build a
            #      {"type": "tool_result", "tool_use_id": block.id, "content": ..., "is_error": ...}
            #   3. Append ONE user message containing all the tool_result blocks.
            ...

        elif response.stop_reason == "end_turn":
            # TODO 4: join the text of every block with block.type == "text" and return it.
            ...

        else:
            # max_tokens, refusal, pause_turn... Don't treat these as success.
            raise RuntimeError(f"Unexpected stop_reason: {response.stop_reason}")


if __name__ == "__main__":
    # TODO 5: this prompt needs search, then calculation. Watch the logs: you
    #   should see >= 2 tool_use iterations before end_turn.
    prompt = (
        "Look up Nimbus Robotics' revenue and its number of employees, "
        "then calculate revenue per employee in dollars."
    )
    print("\nFINAL ANSWER:\n" + run_agent(prompt))
