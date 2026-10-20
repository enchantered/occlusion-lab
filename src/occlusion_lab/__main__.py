"""Run with python -m occlusion_lab demo [--json]."""
import argparse
import json
from typing import Any

from .core import astar, observe, render

# Fixed synthetic world: no external or image assets.
WORLD = (
    "###########",
    "#...#.....#",
    "#...#.....#",
    "#.........#",
    "#...#.....#",
    "#...#.....#",
    "###########",
)
START = (3, 1)
GOAL = (3, 9)
OBSERVATION_RADIUS = 8


def run_demo(radius: int = OBSERVATION_RADIUS) -> tuple[dict[str, Any], tuple[str, ...], tuple[tuple[int, int], ...] | None]:
    observed = observe(WORLD, START, radius)
    result = astar(observed, START, GOAL)
    return {
        "grid_size": {"rows": len(WORLD), "columns": len(WORLD[0])},
        "observation_radius_manhattan": radius,
        "start": list(START),
        "goal": list(GOAL),
        "reachable_on_observed_free_cells": result.reachable,
        "path_steps": result.steps,
        "path_cells": None if result.path is None else [list(p) for p in result.path],
        "expanded_nodes": result.expanded,
        "observed_free_cells": sum(row.count(".") for row in observed),
        "unknown_cells": sum(row.count("?") for row in observed),
    }, observed, result.path


def main() -> None:
    parser = argparse.ArgumentParser(description="Deterministic occupancy mapping and observed-map A* demo")
    sub = parser.add_subparsers(dest="command", required=True)
    demo = sub.add_parser("demo", help="show the fixed synthetic mapping/navigation example")
    demo.add_argument("--json", action="store_true", help="emit deterministic metrics as JSON only")
    demo.add_argument("--radius", type=int, default=OBSERVATION_RADIUS,
                      help=f"Manhattan observation radius (non-negative; default: {OBSERVATION_RADIUS})")
    args = parser.parse_args()
    if args.radius < 0:
        parser.error("--radius must be a non-negative integer")
    metrics, observed, path = run_demo(args.radius)
    if args.json:
        print(json.dumps(metrics, sort_keys=True, indent=2))
        return
    print("GROUND TRUTH")
    print(render(WORLD, START, GOAL))
    print("\nOBSERVED MAP (unknown = blocked; * = planned route)")
    print(render(observed, START, GOAL, path or ()))
    if path is None:
        print("No route is known using observed free cells; unknown cells are blocked for planning. This does not prove the goal is unreachable in the hidden world.")
    print("\nMETRICS")
    print(json.dumps(metrics, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
