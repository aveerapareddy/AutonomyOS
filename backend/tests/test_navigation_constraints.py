"""Navigation constraint mapping."""

from backend.services.navigation_constraints import grid_inflation_cells
from backend.simulator.grid_map import DEFAULT_INFLATION_RADIUS


def test_default_inflation() -> None:
    assert grid_inflation_cells([]) == DEFAULT_INFLATION_RADIUS


def test_avoid_obstacles_raises_inflation() -> None:
    assert grid_inflation_cells(["avoid_obstacles"]) > DEFAULT_INFLATION_RADIUS
