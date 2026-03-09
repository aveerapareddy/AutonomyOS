"""Deterministic scenario generator for benchmark runs."""

import math
import random
import uuid
from typing import List

from backend.scenarios.scenario_config import ScenarioConfig


DEFAULT_BOUNDS = (-10.0, 10.0, -10.0, 10.0)
MIN_OBSTACLES = 1
MAX_OBSTACLES = 5
OBSTACLE_TYPES = ["wall", "block"]
START_TARGET_MARGIN = 2.0


def _clear_of_obstacles(x: float, y: float, obstacles: List[tuple], margin: float = 1.5) -> bool:
    for (ox, oy) in obstacles:
        if abs(x - ox) < margin and abs(y - oy) < margin:
            return False
    return True


def _pick_start(
    rng: random.Random,
    bounds: tuple,
    obstacle_positions: List[tuple],
    target_x: float,
    target_y: float,
) -> tuple:
    min_x, max_x, min_y, max_y = bounds
    for _ in range(50):
        x = rng.uniform(min_x + 1, max_x - 1)
        y = rng.uniform(min_y + 1, max_y - 1)
        if not _clear_of_obstacles(x, y, obstacle_positions):
            continue
        if abs(x - target_x) < START_TARGET_MARGIN and abs(y - target_y) < START_TARGET_MARGIN:
            continue
        theta = rng.uniform(0.0, 2.0 * math.pi)
        return (x, y, theta)
    return (0.0, 0.0, 0.0)


def generate_scenarios(
    count: int,
    seed: int | None = None,
    bounds: tuple = DEFAULT_BOUNDS,
) -> List[ScenarioConfig]:
    """Generate N warehouse-like scenarios. Deterministic for same seed."""
    rng = random.Random(seed)
    min_x, max_x, min_y, max_y = bounds
    scenarios: List[ScenarioConfig] = []

    for i in range(count):
        n_obstacles = rng.randint(MIN_OBSTACLES, MAX_OBSTACLES)
        obstacle_positions: List[tuple] = []
        obstacle_types: List[str] = []

        for j in range(n_obstacles):
            x = rng.uniform(min_x + 1, max_x - 1)
            y = rng.uniform(min_y + 1, max_y - 1)
            obstacle_positions.append((x, y))
            obstacle_types.append(rng.choice(OBSTACLE_TYPES))

        target_x = rng.uniform(min_x + 1, max_x - 1)
        target_y = rng.uniform(min_y + 1, max_y - 1)
        while not _clear_of_obstacles(target_x, target_y, obstacle_positions):
            target_x = rng.uniform(min_x + 1, max_x - 1)
            target_y = rng.uniform(min_y + 1, max_y - 1)

        start_x, start_y, start_theta = _pick_start(
            rng, bounds, obstacle_positions, target_x, target_y
        )

        scenario_id = uuid.uuid4().hex if seed is None else _deterministic_id(seed, i)
        scenarios.append(
            ScenarioConfig(
                scenario_id=scenario_id,
                scenario_name=f"scenario_{i}",
                world_bounds=bounds,
                obstacle_positions=obstacle_positions,
                obstacle_types=obstacle_types,
                target_position=(target_x, target_y),
                robot_start_position=(start_x, start_y, start_theta),
            )
        )
    return scenarios


def _deterministic_id(seed: int, index: int) -> str:
    combined = seed * 31 + index
    rng = random.Random(combined)
    return "".join(rng.choices("0123456789abcdef", k=32))
