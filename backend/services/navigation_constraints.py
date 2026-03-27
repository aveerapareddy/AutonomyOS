"""Map high-level mission constraints to navigation/grid parameters."""

from backend.simulator.grid_map import DEFAULT_INFLATION_RADIUS

GRID_INFLATION_AVOID_OBSTACLES = 2


def grid_inflation_cells(constraints: list[str]) -> int:
    if "avoid_obstacles" in constraints:
        return GRID_INFLATION_AVOID_OBSTACLES
    return DEFAULT_INFLATION_RADIUS
