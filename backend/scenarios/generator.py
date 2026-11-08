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
    # Deterministic bounded fallback; never fabricate a blocked/out-of-bounds start.
    min_x,max_x,min_y,max_y=bounds
    for ix in range(17):
        for iy in range(17):
            x=min_x+1+ix*(max_x-min_x-2)/16
            y=min_y+1+iy*(max_y-min_y-2)/16
            if _clear_of_obstacles(x,y,obstacle_positions) and not (abs(x-target_x)<START_TARGET_MARGIN and abs(y-target_y)<START_TARGET_MARGIN):
                return (x,y,0.0)
    raise ValueError('No valid robot start found within the bounded sampling budget')


def generate_scenarios(
    count: int,
    seed: int | None = None,
    bounds: tuple = DEFAULT_BOUNDS,
) -> List[ScenarioConfig]:
    """Generate N warehouse-like scenarios. Deterministic for same seed."""
    if isinstance(count,bool) or not isinstance(count,int) or not 0<=count<=100:
        raise ValueError('Scenario count must be an integer in 0..100')
    if len(bounds)!=4 or not all(math.isfinite(v) for v in bounds):raise ValueError('Bounds must be finite')
    if not (4<=bounds[1]-bounds[0]<=40 and 4<=bounds[3]-bounds[2]<=40):raise ValueError('Generated-world dimensions must be 4..40 meters')
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
        for _ in range(512):
            if _clear_of_obstacles(target_x,target_y,obstacle_positions):break
            target_x = rng.uniform(min_x + 1, max_x - 1)
            target_y = rng.uniform(min_y + 1, max_y - 1)
        else:
            raise ValueError('No clear target found within the bounded sampling budget')

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
