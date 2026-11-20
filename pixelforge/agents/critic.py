"""Objective image checks plus an explicit opt-in OpenAI vision review."""
from __future__ import annotations

import base64
import hashlib
import io
from PIL import Image

from ..models import AssetPlan, ReviewIssue, ReviewReport
from .llm import ask_json


def inspect_frames(frames: list[Image.Image], plan: AssetPlan) -> ReviewReport:
    issues: list[ReviewIssue] = []
    if len(frames) != plan.frame_count:
        issues.append(ReviewIssue("frame_count", "error", "Frame count differs from plan."))
    if sum(plan.frame_durations_ms) != round(plan.duration_seconds * 1000):
        issues.append(ReviewIssue("timing", "error", "Frame timing does not match duration."))
    hashes = set()
    central_hashes = set()
    max_colors = 0
    for i, frame in enumerate(frames):
        if frame.size != (plan.width, plan.height):
            issues.append(ReviewIssue("canvas", "error", "Unexpected canvas size.", i))
            continue
        rgba = frame.convert("RGBA")
        if rgba.getextrema()[3][0] != 255:
            issues.append(ReviewIssue("alpha", "error", "Scene contains transparent pixels.", i))
        hashes.add(hashlib.sha256(rgba.tobytes()).hexdigest())
        center = rgba.crop((plan.width // 2 - 18, 124, plan.width // 2 + 18, 171))
        central_hashes.add(hashlib.sha256(center.tobytes()).hexdigest())
        colors = rgba.getcolors(maxcolors=4096)
        max_colors = max(max_colors, len(colors) if colors is not None else 4097)
    if frames and len(hashes) < 2:
        issues.append(ReviewIssue("motion", "error", "All frames are identical."))
    if frames and len(central_hashes) < 4:
        issues.append(ReviewIssue("central_motion", "error", "Central region has fewer than four poses."))
    if max_colors > 128:
        issues.append(ReviewIssue("palette", "warning", "Scene exceeds the 128-color review budget."))
    metrics = {"frame_count": len(frames), "unique_frames": len(hashes),
               "central_unique_frames": len(central_hashes), "max_colors": max_colors,
               "duration_ms": sum(plan.frame_durations_ms),
               "canvas": [plan.width, plan.height],
               "note": "Central-region motion is an objective proxy, not semantic gait analysis."}
    return ReviewReport(passed=not any(issue.severity == "error" for issue in issues),
                        issues=issues, metrics=metrics)


def review_with_vision(frames: list[Image.Image], plan: AssetPlan) -> ReviewReport:
    report = inspect_frames(frames, plan)
    samples = [frames[i] for i in sorted(set([0, len(frames) // 4, len(frames) // 2,
                                             3 * len(frames) // 4]))] if frames else []
    content = [{"type": "input_text", "text": (
        f"Review these samples of a 5-second pixel-city loop for this brief: {plan.prompt}. "
        "Assess central character visibility, pixel clarity, and walk poses. "
        "These sparse frames cannot establish continuous timing; say so if relevant."
    )}]
    for frame in samples:
        buf = io.BytesIO()
        frame.resize((960, 540), Image.Resampling.NEAREST).save(buf, format="PNG")
        content.append({"type": "input_image", "image_url":
                        "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")})
    result = ask_json(
        "You are a pixel-art reviewer. Report visible defects only. Return an empty "
        "issues array if no visible defect. Do not imply you have watched a whole video.",
        [{"role": "user", "content": content}],
        {"type": "object", "properties": {"issues": {"type": "array", "items": {
            "type": "object", "properties": {
                "code": {"type": "string"}, "severity": {"type": "string", "enum": ["error", "warning"]},
                "description": {"type": "string"}, "repair": {"type": "string"},
            }, "required": ["code", "severity", "description", "repair"], "additionalProperties": False,
        }}}, "required": ["issues"], "additionalProperties": False}, "vision_review",
    )
    report.issues.extend(ReviewIssue(**issue) for issue in result["issues"])
    report.passed = not any(issue.severity == "error" for issue in report.issues)
    report.source = "openai_vision"
    return report
