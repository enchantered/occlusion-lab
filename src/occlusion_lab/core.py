"""Grid-world ray observations, occupancy maps, and A* navigation.

Coordinates are (row, column). Ground truth uses '#' for walls and '.' for free
space; observations use '?' unknown, '#' occupied, and '.' observed free.
"""
from __future__ import annotations

from dataclasses import dataclass
import heapq
from itertools import count
from typing import Iterable, Sequence

Point = tuple[int, int]


class MapError(ValueError):
    """Raised when a grid or coordinate is invalid."""


def validate_grid(grid: Sequence[str]) -> tuple[int, int]:
    if not grid or not grid[0]:
        raise MapError("grid must be non-empty")
    width = len(grid[0])
    if any(len(row) != width for row in grid):
        raise MapError("grid must be rectangular")
    if any(cell not in ".#" for row in grid for cell in row):
        raise MapError("grid cells must be '.' (free) or '#' (wall)")
    return len(grid), width


def in_bounds(point: Point, shape: tuple[int, int]) -> bool:
    r, c = point
    return 0 <= r < shape[0] and 0 <= c < shape[1]


def _check_point(point: Point, shape: tuple[int, int], name: str) -> None:
    if not isinstance(point, tuple) or len(point) != 2 or not all(isinstance(x, int) for x in point):
        raise MapError(f"{name} must be an (int, int) coordinate")
    if not in_bounds(point, shape):
        raise MapError(f"{name} {point} is out of bounds for {shape}")


def ray_cells(start: Point, end: Point) -> list[Point]:
    """Integer Bresenham line including both endpoints."""
    x0, y0 = start[1], start[0]
    x1, y1 = end[1], end[0]
    dx, dy = abs(x1 - x0), abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy
    result = []
    while True:
        result.append((y0, x0))
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x0 += sx
        if e2 < dx:
            err += dx
            y0 += sy
    return result


def observe(grid: Sequence[str], origin: Point, radius: int | None = None) -> tuple[str, ...]:
    """Cast one ray to each in-radius cell. Rays include and stop at first wall."""
    shape = validate_grid(grid)
    _check_point(origin, shape, "origin")
    if grid[origin[0]][origin[1]] == "#":
        raise MapError("origin must be free")
    if radius is not None and (not isinstance(radius, int) or radius < 0):
        raise MapError("radius must be a non-negative integer or None")
    h, w = shape
    visible = [["?" for _ in range(w)] for _ in range(h)]
    visible[origin[0]][origin[1]] = "."
    for r in range(h):
        for c in range(w):
            if radius is not None and abs(r-origin[0]) + abs(c-origin[1]) > radius:
                continue
            for rr, cc in ray_cells(origin, (r, c)):
                visible[rr][cc] = grid[rr][cc]
                if grid[rr][cc] == "#":
                    break
    return tuple("".join(row) for row in visible)


@dataclass(frozen=True)
class PathResult:
    path: tuple[Point, ...] | None
    expanded: int

    @property
    def reachable(self) -> bool:
        return self.path is not None

    @property
    def steps(self) -> int | None:
        return None if self.path is None else len(self.path) - 1


def astar(observed: Sequence[str], start: Point, goal: Point) -> PathResult:
    """Find a shortest four-neighbor path, treating unknown and walls as blocked."""
    shape = validate_observation(observed)
    _check_point(start, shape, "start")
    _check_point(goal, shape, "goal")
    if observed[start[0]][start[1]] != "." or observed[goal[0]][goal[1]] != ".":
        return PathResult(None, 0)
    if start == goal:
        return PathResult((start,), 0)
    tie = count()
    heuristic = lambda p: abs(p[0]-goal[0]) + abs(p[1]-goal[1])
    frontier = [(heuristic(start), 0, next(tie), start)]
    came_from: dict[Point, Point | None] = {start: None}
    costs = {start: 0}
    expanded = 0
    while frontier:
        _, g, _, current = heapq.heappop(frontier)
        if g != costs.get(current):
            continue
        expanded += 1
        if current == goal:
            path = []
            p: Point | None = goal
            while p is not None:
                path.append(p)
                p = came_from[p]
            return PathResult(tuple(reversed(path)), expanded)
        r, c = current
        for nxt in ((r-1,c),(r,c-1),(r,c+1),(r+1,c)):
            if in_bounds(nxt, shape) and observed[nxt[0]][nxt[1]] == ".":
                ng = g + 1
                if ng < costs.get(nxt, float("inf")):
                    costs[nxt] = ng
                    came_from[nxt] = current
                    heapq.heappush(frontier, (ng + heuristic(nxt), ng, next(tie), nxt))
    return PathResult(None, expanded)


def validate_observation(grid: Sequence[str]) -> tuple[int, int]:
    if not grid or not grid[0]:
        raise MapError("observation must be non-empty")
    width = len(grid[0])
    if any(len(row) != width for row in grid):
        raise MapError("observation must be rectangular")
    if any(cell not in ".#?" for row in grid for cell in row):
        raise MapError("observation cells must be '.', '#' or '?'")
    return len(grid), width


def render(grid: Sequence[str], start: Point | None = None, goal: Point | None = None,
           path: Iterable[Point] = ()) -> str:
    """Render a grid, overlaying route then endpoint markers."""
    rows = [list(row) for row in grid]
    for r, c in path:
        if rows[r][c] == ".":
            rows[r][c] = "*"
    if start is not None:
        rows[start[0]][start[1]] = "S"
    if goal is not None:
        rows[goal[0]][goal[1]] = "G"
    return "\n".join("".join(row) for row in rows)
