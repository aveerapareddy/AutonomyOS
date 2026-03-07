"""A* path planning on an occupancy grid."""

import heapq
from typing import List, Tuple

from backend.schemas.navigation import NavigationResult, Waypoint
from backend.simulator.grid_map import OccupancyGrid


def _heuristic(row: int, col: int, goal_row: int, goal_col: int) -> float:
    """Manhattan distance. Admissible for 4-connected grid."""
    return float(abs(row - goal_row) + abs(col - goal_col))


def _astar(
    grid: OccupancyGrid,
    start: Tuple[int, int],
    goal: Tuple[int, int],
) -> List[Tuple[int, int]]:
    """
    A* search. Returns path from start to goal (inclusive) as list of (row, col),
    or empty list if no path.
    """
    s_row, s_col = start
    g_row, g_col = goal
    if grid.is_blocked(s_row, s_col):
        return []
    if grid.is_blocked(g_row, g_col):
        return []
    if start == goal:
        return [start]

    # (f, counter, node, path)
    counter = 0
    open_heap: List[Tuple[float, int, Tuple[int, int], List[Tuple[int, int]]]] = []
    g_val = 0.0
    h_val = _heuristic(s_row, s_col, g_row, g_col)
    heapq.heappush(open_heap, (g_val + h_val, counter, start, [start]))
    counter += 1
    closed: set[Tuple[int, int]] = set()

    while open_heap:
        _f, _c, (r, c), path = heapq.heappop(open_heap)
        if (r, c) in closed:
            continue
        closed.add((r, c))
        if (r, c) == goal:
            return path
        for nr, nc in grid.neighbors(r, c):
            if (nr, nc) in closed:
                continue
            new_path = path + [(nr, nc)]
            ng = len(new_path) - 1
            nh = _heuristic(nr, nc, g_row, g_col)
            heapq.heappush(open_heap, (ng + nh, counter, (nr, nc), new_path))
            counter += 1
    return []


def plan_path(
    grid: OccupancyGrid,
    start_x: float,
    start_y: float,
    goal_x: float,
    goal_y: float,
) -> NavigationResult:
    """
    Plan path from (start_x, start_y) to (goal_x, goal_y) on the given grid.
    Returns world-space waypoints (including start and goal).
    """
    start_rc = grid.world_to_grid(start_x, start_y)
    goal_rc = grid.world_to_grid(goal_x, goal_y)
    if start_rc == goal_rc:
        x, y = grid.grid_to_world(start_rc[0], start_rc[1])
        return NavigationResult(
            path_found=True,
            waypoints=[Waypoint(x=x, y=y)],
            path_length=1,
        )
    path_rc = _astar(grid, start_rc, goal_rc)
    if not path_rc:
        return NavigationResult(
            path_found=False,
            waypoints=[],
            path_length=0,
            message="No path found",
        )
    waypoints = [
        Waypoint(x=grid.grid_to_world(r, c)[0], y=grid.grid_to_world(r, c)[1])
        for r, c in path_rc
    ]
    return NavigationResult(
        path_found=True,
        waypoints=waypoints,
        path_length=len(waypoints),
    )
