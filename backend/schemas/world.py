"""World object descriptor for replay, telemetry, and benchmarking."""

from dataclasses import dataclass


@dataclass
class WorldObject:
    """Single typed world object (obstacle or target). One record, no parallel lists."""

    object_id: str
    object_type: str
    x: float
    y: float

    half_extents: tuple[float, float, float] = (0.5, 0.5, 0.5)
