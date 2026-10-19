# Occlusion Lab

A small, deterministic grid-world for exploring **occupancy mapping under occlusion** and navigation when the planner can only use observations. It is a transparent algorithmic toy for spatial-reasoning/world-model evaluation—not a learned model or a benchmark claim.

## Why this exists

Pathfinding and obstacle avoidance are related but distinct: a planner searches a representation of traversable space, while obstacle avoidance concerns reacting to obstacles in the environment. A [Godot community discussion](https://forum.godotengine.org/t/obstacles-in-pathfinding-do-not-work/59417), opened in 2024 with further replies in 2026, illustrates that this distinction continues to cause confusion. Mapping also has its own failure modes: [ROS2 point-cloud-to-occupancy-grid troubleshooting notes](https://github.com/hermanumrao/ROS2_pcd_to_occupancy_grid/blob/main/README.md) discuss unknown or sparse maps versus noisy ones. This tiny controlled example makes visibility, unknown cells, and planning assumptions inspectable. **It does not fix, model, or stand in for Godot avoidance, ROS mapping, or any real robotics system.**

## Living consumer research

The [consumer-behavior log](docs/consumer-behavior-log.md) starts with a **2026-10-19** source-backed baseline on AI apps versus established tools, recurring user friction, and small project hypotheses. Future runs should append evidence, competitor checks, validation results, and maintenance notes. These research ideas are not implemented consumer features, and the log does not activate the paused daily schedule.

## Quickstart

Requires Python 3.10+. Runtime code uses only the standard library; installation uses the build tooling declared in `pyproject.toml`.

Recommended: create an isolated environment and install the package in editable mode from the project root:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
python -m occlusion_lab demo
python -m occlusion_lab demo --json
python -m unittest discover -s tests -v
```

Alternatively, without installing the package, run from the repository root with its `src` directory on the import path:

```sh
PYTHONPATH=src python -m occlusion_lab demo
PYTHONPATH=src python -m occlusion_lab demo --json
PYTHONPATH=src python -m unittest discover -s tests -v
```

The ordinary demo prints ground truth followed by the partial observed map, with `?` unknown cells, `#` occupied walls, `.` observed free cells, `S`/`G` endpoints, and `*` the route. Counts exclude markers. `--json` emits stable, sorted JSON without the ASCII display.

Actual JSON metrics from the fixed fixture (formatted compactly here):

```json
{
  "expanded_nodes": 9,
  "goal": [3, 9],
  "grid_size": {"columns": 11, "rows": 7},
  "observation_radius_manhattan": 8,
  "observed_free_cells": 29,
  "path_cells": [[3, 1], [3, 2], [3, 3], [3, 4], [3, 5], [3, 6], [3, 7], [3, 8], [3, 9]],
  "path_steps": 8,
  "reachable_on_observed_free_cells": true,
  "start": [3, 1],
  "unknown_cells": 31
}
```

The route lists `[row, column]` coordinate pairs, including both endpoints. Run `python -m occlusion_lab demo --json` for the same payload in the CLI's pretty-printed format.

## Architecture

- `src/occlusion_lab/core.py`: grid validation, integer Bresenham ray tracing, visibility/occupancy construction, and A*.
- `src/occlusion_lab/__main__.py`: fixed hand-authored synthetic scene and CLI.
- `tests/`: standard-library `unittest` coverage for ray occlusion, map validation, navigation, deterministic CLI output, and A* shortest lengths against a breadth-first-search oracle on seeded maps.

Coordinates are `(row, column)`. Ground truth accepts `.` free cells and `#` walls. Observation maps add `?` for unknown. `observe` casts a ray from a free origin to each target within optional Manhattan radius; each ray reveals cells through the first wall, includes that occupied wall, then stops. Free cells behind a wall remain unknown unless another ray can see them.

A* uses four-connected movement, unit step cost, and Manhattan distance (admissible/consistent for this movement model). It only traverses observed `.` cells: occupied **and unknown** cells are blocked. It returns a shortest path or a graceful unreachable result; start equal to goal is a zero-step path. Invalid grids and out-of-bounds coordinates raise `MapError`.

## Troubleshooting

- **`No module named occlusion_lab`:** this is a `src`-layout package. Activate the environment and run `python -m pip install -e .` from the repository root, or use `PYTHONPATH=src` as shown above. Use the same Python executable for installation and invocation (`python -m pip ...`, then `python -m ...`).
- **A route is unreachable:** A* treats both `#` and `?` as blocked. Check whether the endpoints are observed `.` cells and whether a continuous four-neighbor corridor is known free; unseen space is not assumed safe or traversable.
- **Unexpected visibility:** rays are discrete Bresenham lines, limited by Manhattan radius when supplied, and stop at the first wall. Other target rays can independently reveal around an occluder; this is not a full physical sensor model.
- **Validation errors:** ground truth rows must be nonempty, rectangular, and contain only `.`/`#`; observations may also contain `?`. Coordinates are `(row, column)`, in bounds, and observation origins must be free.

## Maintenance

Keep the implementation dependency-free at runtime and preserve the small, explicit grid semantics. When changing visibility or movement behavior, update both the explanatory scope and tests. In particular, use an independent shortest-path oracle for A* changes, keep seeded cases reproducible, and retain checks that planning consumes observations rather than hidden ground truth. Validate an editable install, the test suite, and both CLI modes before release. Fixture metric values in this document should be regenerated from `python -m occlusion_lab demo --json` whenever the fixture or algorithms change.

## Scope and limitations

This is a deterministic 2D discrete simulator with a fixed synthetic fixture: no sensor noise, robot motion, probabilistic belief updates, continuous geometry, or learned perception/planning. A shortest path through observed free cells describes this simple grid, not real-world safety or general spatial intelligence. Rays use a discrete line approximation, and alternative lines may reveal cells independently. The original fixture and code require no external assets, image files, network access, or runtime dependencies. No license is assigned.
