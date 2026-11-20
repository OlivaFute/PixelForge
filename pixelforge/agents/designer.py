"""Limited palettes and layer design, constrained to the implemented renderer."""
from __future__ import annotations

import re
from ..models import AssetPlan, DesignSpec
from .llm import ask_json


PALETTES = {
    "sunset": {
        "sky": "#38334F", "sky_light": "#ECAE9C", "far_building": "#5D4C69",
        "building_shadow": "#433651", "building": "#53415C", "building_light": "#B17B80",
        "street": "#504C69", "street_light": "#76657F", "outline": "#181C35",
        "neon_cyan": "#79D5D1", "neon_pink": "#E79993", "warm_light": "#FFB66E",
        "skin": "#EFBD98", "hair": "#363149", "jacket": "#DC775E",
        "jacket_light": "#F3A16E", "pants": "#324967", "shoe": "#181C35",
        "cloud": "#986277", "leaf": "#719578", "white": "#FFE2B4",
    },
    "night": {
        "sky": "#131426", "sky_light": "#292443", "far_building": "#302D49",
        "building_shadow": "#242D42", "building": "#3A4561", "building_light": "#5A637A",
        "street": "#242536", "street_light": "#434153", "outline": "#151827",
        "neon_cyan": "#6EDBCD", "neon_pink": "#F17CA7", "warm_light": "#F4CA81",
        "skin": "#E5AD88", "hair": "#302B37", "jacket": "#D86664",
        "jacket_light": "#F18B79", "pants": "#39415C", "shoe": "#182233",
        "cloud": "#44425B", "leaf": "#426C68", "white": "#F4E4CC",
    },
    "day": {
        "sky": "#93C8D2", "sky_light": "#B6DDD5", "far_building": "#92A6B9",
        "building_shadow": "#6D819C", "building": "#9E9DB4", "building_light": "#D1BFAF",
        "street": "#6B6C7E", "street_light": "#9D8B8A", "outline": "#35435A",
        "neon_cyan": "#71DCC1", "neon_pink": "#D67D9A", "warm_light": "#FFE3A2",
        "skin": "#EDB692", "hair": "#403847", "jacket": "#BD5A69",
        "jacket_light": "#EB8690", "pants": "#49516A", "shoe": "#303C50",
        "cloud": "#E3EBDD", "leaf": "#527F71", "white": "#FFF3D6",
    },
}


def design_asset(plan: AssetPlan, use_llm: bool = False) -> DesignSpec:
    palette = PALETTES[plan.style].copy()
    notes = ["Integer-pixel drawing only; preview uses nearest-neighbor scaling."]
    if use_llm:
        properties = {name: {"type": "string"} for name in palette}
        result = ask_json(
            "Design a coherent small pixel-city palette for the supplied brief. "
            "Keep colors distinct enough for a red-jacket walking person to stand out. "
            "Every value must be exactly #RRGGBB, with no alpha or CSS names.",
            f"Prompt: {plan.prompt}\nTime: {plan.style}\nBase palette: {palette}",
            {"type": "object", "properties": properties,
             "required": list(properties), "additionalProperties": False},
            "city_palette",
        )
        if any(not re.fullmatch(r"#[0-9a-fA-F]{6}", color) for color in result.values()):
            raise ValueError("LLM palette contains invalid colors; no render was started.")
        palette = result
        notes.append("Palette chosen by OpenAI; geometry uses the bounded local renderer.")
    plan.palette = palette.copy()
    return DesignSpec(plan=plan, palette=palette, layers=list(plan.layers), notes=notes)
