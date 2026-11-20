"""Opt-in OpenAI Responses integration. Never invokes the API in offline mode."""
from __future__ import annotations

import os
import json
from typing import Any


def ask_json(instructions: str, input_value: Any, schema: dict, name: str) -> dict:
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("--llm requires OPENAI_API_KEY. Offline demo needs no key.")
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("Install requirements-optional.txt to use --llm.") from exc
    client = OpenAI(timeout=90, max_retries=1)
    response = client.responses.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        instructions=instructions,
        input=input_value,
        text={"format": {"type": "json_schema", "name": name,
                         "schema": schema, "strict": True}},
        store=False,
    )
    if not response.output_text:
        raise RuntimeError("OpenAI returned no structured text; request may be refused.")
    return json.loads(response.output_text)
