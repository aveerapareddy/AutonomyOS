"""Navigation and occupancy grid tests."""

import pytest

from backend.agents.navigation_agent import plan_path
from backend.schemas.navigation import NavigationResult
from backend.simulator.grid_map import OCCUPIED, build_occupancy_grid


def _blocked_cell_count(grid) -> int:
    return sum(row.count(OCCUPIED) for row in grid.grid)


def test_obstacle_inflation_blocks_more_cells() -> None:
    """Larger inflation_radius marks more cells as blocked (deterministic)."""
    bounds = (0.0, 5.0, 0.0, 5.0)
    obstacles = [(2.5, 2.5)]
    g0 = build_occupancy_grid(bounds, obstacles, resolution=1.0, inflation_radius=0)
    g2 = build_occupancy_grid(bounds, obstacles, resolution=1.0, inflation_radius=2)
    n0 = _blocked_cell_count(g0)
    n2 = _blocked_cell_count(g2)
    assert n2 > n0
    assert n0 >= 1


def test_path_simplification_reduces_collinear_points() -> None:
    """Simplified path has no more points than raw; raw >= simplified when path has segments."""
    bounds = (0.0, 10.0, 0.0, 10.0)
    obstacles = [(5.0, 4.0), (5.0, 5.0), (5.0, 6.0)]
    grid = build_occupancy_grid(bounds, obstacles, resolution=1.0, inflation_radius=0)
    result = plan_path(grid, 2.0, 5.0, 8.0, 5.0)
    assert result.path_found
    assert result.path_length_raw >= result.path_length
    assert result.path_length >= 2
    if result.path_length_raw > 2:
        assert result.path_length < result.path_length_raw


def test_start_equals_goal() -> None:
    grid = build_occupancy_grid(
        world_bounds=(0.0, 10.0, 0.0, 10.0),
        obstacle_positions=[],
        resolution=1.0,
    )
    result = plan_path(grid, 0.5, 0.5, 0.5, 0.5)
    assert result.path_found is True
    assert result.path_length == 1
    assert result.path_length_raw == 1
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
