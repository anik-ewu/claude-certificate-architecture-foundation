"""Small helpers around the Claude API. Nothing to do here.

run_tool_loop() is the agentic loop you built in 1.1, packaged up so that
subagents can reuse it.
"""

import json
import logging

import anthropic

MODEL = "claude-haiku-4-5"

log = logging.getLogger("agent")
_client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from the environment


def _text(response) -> str:
    return "".join(b.text for b in response.content if b.type == "text")


def ask(system: str, prompt: str, max_tokens: int = 4000) -> str:
    """One call and one text answer. No tools."""
    response = _client.messages.create(
        model=MODEL, max_tokens=max_tokens, system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    if response.stop_reason != "end_turn":
        raise RuntimeError(f"Unexpected stop_reason: {response.stop_reason}")
    return _text(response)


def ask_json(system: str, prompt: str, schema: dict, max_tokens: int = 4000) -> dict:
    """One call whose answer is guaranteed to match `schema` (structured outputs)."""
    response = _client.messages.create(
        model=MODEL, max_tokens=max_tokens, system=system,
        messages=[{"role": "user", "content": prompt}],
        output_config={"format": {"type": "json_schema", "schema": schema}},
    )
    if response.stop_reason != "end_turn":
        raise RuntimeError(f"Unexpected stop_reason: {response.stop_reason}")
    return json.loads(_text(response))


def run_tool_loop(system: str, prompt: str, tools: list, tool_functions: dict,
                  max_iterations: int = 8) -> str:
    """The 1.1 agentic loop: branch on stop_reason, with a safety cap."""
    messages = [{"role": "user", "content": prompt}]
    for _ in range(max_iterations):
        response = _client.messages.create(
            model=MODEL, max_tokens=4000, system=system, tools=tools, messages=messages,
        )
        if response.stop_reason == "end_turn":
            return _text(response)
        if response.stop_reason != "tool_use":
            raise RuntimeError(f"Unexpected stop_reason: {response.stop_reason}")

        messages.append({"role": "assistant", "content": response.content})
        results = []
        for block in response.content:
            if block.type == "tool_use":
                log.info("      %s(%s)", block.name, json.dumps(block.input))
                try:
                    out, err = tool_functions[block.name](**block.input), False
                except Exception as e:
                    out, err = f"{type(e).__name__}: {e}", True
                results.append({"type": "tool_result", "tool_use_id": block.id,
                                "content": out, "is_error": err})
        messages.append({"role": "user", "content": results})

    log.warning("Subagent hit max_iterations=%d without end_turn", max_iterations)
    return "(subagent stopped early: iteration cap reached)"
