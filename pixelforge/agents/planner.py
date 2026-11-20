"""Turn a prompt into a bounded city-walk plan, with optional LLM interpretation."""
from __future__ import annotations

from ..models import AssetPlan
from .llm import ask_json


DEMO_PROMPT = "5秒像素城市黄昏街景，画面中央一个人物循环行走，霓虹灯和城市环境有动态。"


def plan_request(prompt: str, use_llm: bool = False) -> AssetPlan:
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("Prompt must contain a city-scene description.")
    prompt = prompt.strip()
    lowered = prompt.lower()
    style = "day" if any(word in lowered for word in (
        "白天", "日间", "晴天", "阳光", "daytime", "daylight", "sunny"
    )) else "night" if any(word in lowered for word in (
        "夜", "night", "midnight", "黑暗"
    )) else "sunset"
    name = {"day": "Daylight City Walk", "night": "Neon City Walk",
            "sunset": "Sunset City Walk"}[style]
    source = "deterministic"
    notes = ["This renderer supports the pixel-city / central walking-person template.",
             "Timing is fixed at 320×180, 60 frames, 12 fps, exactly 5 seconds."]
    if use_llm:
        result = ask_json(
            "Interpret the user request for the PixelForge city-walk template. "
            "Choose day, sunset, or night and a short scene name. Explain any requested object "
            "or action that the fixed city-and-walker renderer cannot support. "
            "Do not claim to generate arbitrary characters or execute code.",
            prompt,
            {"type": "object", "properties": {
                "name": {"type": "string"},
                "style": {"type": "string", "enum": ["day", "sunset", "night"]},
                "notes": {"type": "array", "items": {"type": "string"}},
            }, "required": ["name", "style", "notes"], "additionalProperties": False},
            "city_plan",
        )
        name, style = result["name"], result["style"]
        notes.extend(result["notes"])
        source = "openai"
    return AssetPlan(prompt=prompt, name=name, style=style, source=source, notes=notes)
