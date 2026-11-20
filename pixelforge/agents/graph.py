"""Optional LangGraph implementation of the same bounded agent workflow."""
from __future__ import annotations

from typing import Any, Callable, TypedDict
from PIL import Image
from ..models import AssetPlan, DesignSpec, ReviewReport
from .planner import plan_request
from .designer import design_asset
from .critic import inspect_frames, review_with_vision
from .fixer import repair_plan


class AgentState(TypedDict, total=False):
    prompt: str
    plan: AssetPlan
    design: DesignSpec
    frames: list[Image.Image]
    review: ReviewReport
    repair_attempted: bool


def compile_asset_graph(render: Callable[[DesignSpec], list[Image.Image]],
                        use_llm: bool = False) -> Any:
    """Compile planner→designer→render→critic→optional fixer→one re-render.

    The callable renderer keeps service-independent art generation reusable.
    The graph does not execute generated Python, Lua, or arbitrary model code.
    """
    try:
        from langgraph.graph import StateGraph, START, END
    except ImportError as exc:
        raise RuntimeError("Install requirements-optional.txt for LangGraph.") from exc

    graph = StateGraph(AgentState)
    graph.add_node("planner", lambda s: {"plan": plan_request(s["prompt"], use_llm)})
    graph.add_node("designer", lambda s: {"design": design_asset(s["plan"], use_llm)})
    graph.add_node("render", lambda s: {"frames": render(s["design"])})
    graph.add_node("critic", lambda s: {"review": (
        review_with_vision(s["frames"], s["plan"]) if use_llm
        else inspect_frames(s["frames"], s["plan"])
    )})

    def fix(state: AgentState) -> dict:
        plan = repair_plan(state["plan"], state["review"])
        old = state["design"]
        design = DesignSpec(plan=plan, palette=plan.palette.copy(), layers=old.layers,
                            character_anchor=old.character_anchor,
                            walk_cycle_frames=old.walk_cycle_frames,
                            notes=old.notes + ["One bounded automatic repair attempted."])
        return {"plan": plan, "design": design, "repair_attempted": True}

    graph.add_node("fixer", fix)
    graph.add_edge(START, "planner")
    graph.add_edge("planner", "designer")
    graph.add_edge("designer", "render")
    graph.add_edge("render", "critic")

    def route(state: AgentState) -> str:
        repairable = any(i.code in {"palette", "timing"} for i in state["review"].issues)
        return "fixer" if repairable and not state.get("repair_attempted") else "end"

    graph.add_conditional_edges("critic", route, {"fixer": "fixer", "end": END})
    graph.add_edge("fixer", "render")
    return graph.compile()
