"""Portable contracts for the pixel-art agents; no service dependencies required."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class AssetPlan:
    prompt: str
    name: str = "Sunset City Walk"
    style: str = "sunset"
    width: int = 320
    height: int = 180
    fps: int = 12
    duration_seconds: float = 5.0
    frame_count: int = 60
    palette: dict[str, str] = field(default_factory=dict)
    layers: list[str] = field(default_factory=lambda: [
        "01 Sky", "02 Distant skyline", "03 Storefronts", "04 Pavement",
        "05 Contact shadow", "06 Walker", "07 Atmosphere"
    ])
    animations: list[str] = field(default_factory=lambda: ["walk", "city_ambient"])
    source: str = "deterministic"
    notes: list[str] = field(default_factory=list)

    @property
    def frame_durations_ms(self) -> list[int]:
        """Distribute rounding error, so 60 frames add up to exactly 5000 ms."""
        total = round(self.duration_seconds * 1000)
        return [round((i + 1) * total / self.frame_count) -
                round(i * total / self.frame_count) for i in range(self.frame_count)]

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["frame_durations_ms"] = self.frame_durations_ms
        return result


@dataclass
class DesignSpec:
    plan: AssetPlan
    palette: dict[str, str]
    layers: list[str]
    character_anchor: tuple[int, int] = (160, 164)
    walk_cycle_frames: int = 12
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ReviewIssue:
    code: str
    severity: str
    description: str
    frame_index: int | None = None
    repair: str | None = None


@dataclass
class ReviewReport:
    passed: bool
    issues: list[ReviewIssue] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    source: str = "deterministic"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
