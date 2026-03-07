"""Navigation and occupancy grid tests."""

import pytest

from backend.agents.navigation_agent import plan_path
from backend.schemas.navigation import NavigationResult
from backend.simulator.grid_map import build_occupancy_grid


def test_start_equals_goal() -> None:
    grid = build_occupancy_grid(
        world_bounds=(0.0, 10.0, 0.0, 10.0),
        obstacle_positions=[],
        resolution=1.0,
    )
    result = plan_path(grid, 0.5, 0.5, 0.5, 0.5)
    assert result.path_found is True
    assert result.path_length == 1
    assert len(result.waypoints) == 1
    assert result.waypoints[0].x == pytest.approx(0.5)
    assert result.waypoints[0].y == pytest.approx(0.5)


def test_blocked_unreachable() -> None:
    # 3x1 strip: cells (0,0) and (2,0) free, (1,0) blocked. No path from 0 to 2.
    grid = build_occupancy_grid(
        world_bounds=(0.0, 3.0, 0.0, 1.0),
        obstacle_positions=[(1.5, 0.5)],
        resolution=1.0,
        inflation_radius=0,
    )
    result = plan_path(grid, 0.5, 0.5, 2.5, 0.5)
    assert result.path_found is False
    assert result.path_length == 0
    assert len(result.waypoints) == 0
    assert result.message == "No path found"


def test_reachable_path_deterministic_world() -> None:
    # Same layout as world_builder: bounds (-10,10,-10,10), walls at (-3,0),(3,0), block at (1,1)
    bounds = (-10.0, 10.0, -10.0, 10.0)
    obstacles = [(-3.0, 0.0), (3.0, 0.0), (1.0, 1.0)]
    grid = build_occupancy_grid(bounds, obstacles, resolution=0.5)
    result = plan_path(grid, 0.0, 0.0, 5.0, 3.0)
    assert result.path_found is True
    assert result.path_length >= 2
    assert result.waypoints[0].x == pytest.approx(0.25, abs=0.3)
    assert result.waypoints[0].y == pytest.approx(0.25, abs=0.3)
    last = result.waypoints[-1]
    assert last.x == pytest.approx(5.0, abs=0.5)
    assert last.y == pytest.approx(3.0, abs=0.5)
