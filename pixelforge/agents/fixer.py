"""Conservative spec repairs. Pixel geometry defects are reported, never hidden."""
from __future__ import annotations

from dataclasses import replace
from ..models import AssetPlan, ReviewReport
from .designer import PALETTES


def repair_plan(plan: AssetPlan, review: ReviewReport) -> AssetPlan:
    repaired = replace(plan, palette=plan.palette.copy(), notes=list(plan.notes))
    repairs: list[str] = []
    for issue in review.issues:
        if issue.code == "palette":
            repaired.palette = PALETTES[plan.style].copy()
            repairs.append("Restore the bounded template palette, then re-render.")
        elif issue.code == "timing":
            repaired.duration_seconds = 5.0
            repaired.fps = 12
            repaired.frame_count = 60
            repairs.append("Restore 60 frames at 12 fps / 5 seconds, then re-render.")
        elif issue.severity == "error":
            repairs.append(f"Unresolved renderer issue ({issue.code}): {issue.description}")
    repaired.notes.extend(repairs)
    return repaired
