"""2D occupancy grid from world bounds and obstacle positions."""

from dataclasses import dataclass
from typing import List, Tuple

# Free = 0, blocked = 1.
OCCUPIED = 1
FREE = 0

DEFAULT_RESOLUTION = 0.25
DEFAULT_INFLATION_RADIUS = 1


@dataclass
class OccupancyGrid:
    """
    Row-major grid: grid[row][col]. Row 0 = min_y, col 0 = min_x.
    World bounds (min_x, max_x, min_y, max_y).
    """

    grid: List[List[int]]
    min_x: float
    max_x: float
    min_y: float
    max_y: float
    resolution: float

    @property
    def num_rows(self) -> int:
        return len(self.grid)

    @property
    def num_cols(self) -> int:
        return len(self.grid[0]) if self.grid else 0

    def world_to_grid(self, x: float, y: float) -> Tuple[int, int]:
        """World (x, y) to grid (row, col). Clamped to valid indices."""
        col = int((x - self.min_x) / self.resolution)
        row = int((y - self.min_y) / self.resolution)
        col = max(0, min(col, self.num_cols - 1))
        row = max(0, min(row, self.num_rows - 1))
        return (row, col)

    def grid_to_world(self, row: int, col: int) -> Tuple[float, float]:
        """Grid (row, col) to world (x, y) at cell center."""
        x = self.min_x + (col + 0.5) * self.resolution
        y = self.min_y + (row + 0.5) * self.resolution
        return (x, y)

    def is_blocked(self, row: int, col: int) -> bool:
        if row < 0 or row >= self.num_rows or col < 0 or col >= self.num_cols:
            return True
        return self.grid[row][col] == OCCUPIED

    def neighbors(self, row: int, col: int) -> List[Tuple[int, int]]:
        """4-connected neighbors that are in bounds and not blocked."""
        out: List[Tuple[int, int]] = []
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            r, c = row + dr, col + dc
            if not self.is_blocked(r, c):
                out.append((r, c))
        return out


def build_occupancy_grid(
    world_bounds: Tuple[float, float, float, float],
    obstacle_positions: List[Tuple[float, float]],
    resolution: float = DEFAULT_RESOLUTION,
    inflation_radius: int = DEFAULT_INFLATION_RADIUS,
) -> OccupancyGrid:
    """
    Build grid from bounds and obstacle list. Each obstacle (x,y) marks
    its cell and cells within inflation_radius (Manhattan, in grid cells)
    as occupied. Deterministic.
    """
    min_x, max_x, min_y, max_y = world_bounds
    ncols = int((max_x - min_x) / resolution)
    nrows = int((max_y - min_y) / resolution)
    ncols = max(1, ncols)
    nrows = max(1, nrows)

    grid: List[List[int]] = [[FREE] * ncols for _ in range(nrows)]
    radius = max(0, inflation_radius)

    for (ox, oy) in obstacle_positions:
        col = int((ox - min_x) / resolution)
        row = int((oy - min_y) / resolution)
        if not (0 <= row < nrows and 0 <= col < ncols):
            continue
        for dr in range(-radius, radius + 1):
            for dc in range(-radius, radius + 1):
                if abs(dr) + abs(dc) > radius:
                    continue
                r, c = row + dr, col + dc
                if 0 <= r < nrows and 0 <= c < ncols:
                    grid[r][c] = OCCUPIED

    return OccupancyGrid(
        grid=grid,
        min_x=min_x,
        max_x=max_x,
        min_y=min_y,
        max_y=max_y,
        resolution=resolution,
    )
