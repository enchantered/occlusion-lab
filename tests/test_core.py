import json
import os
import random
import subprocess
import sys
import unittest
from collections import deque

from occlusion_lab import core
from occlusion_lab.__main__ import GOAL, OBSERVATION_RADIUS, START, WORLD


def bfs_steps(grid, start, goal):
    """Independent four-neighbor shortest-distance oracle for free observation cells."""
    if grid[start[0]][start[1]] != "." or grid[goal[0]][goal[1]] != ".":
        return None
    queue = deque([(start, 0)])
    seen = {start}
    while queue:
        (r, c), distance = queue.popleft()
        if (r, c) == goal:
            return distance
        for nxt in ((r - 1, c), (r, c - 1), (r, c + 1), (r + 1, c)):
            nr, nc = nxt
            if (0 <= nr < len(grid) and 0 <= nc < len(grid[0])
                    and grid[nr][nc] == "." and nxt not in seen):
                seen.add(nxt)
                queue.append((nxt, distance + 1))
    return None


class ObservationTests(unittest.TestCase):
    def test_ray_stops_at_wall(self):
        observed = core.observe((".....", ".#.#.", "....."), (1, 0))
        self.assertEqual(observed[1], ".#???")
        self.assertEqual(observed[0][0], ".")

    def test_radius_limits_rays(self):
        observed = core.observe((".....", ".....", "....."), (1, 2), radius=1)
        self.assertEqual(sum(row.count(".") for row in observed), 5)
        self.assertEqual(sum(row.count("?") for row in observed), 10)

    def test_zero_radius_and_invalid_radius(self):
        self.assertEqual(core.observe(("...", "..."), (0, 1), radius=0), ("?.?", "???"))
        for radius in (-1, 1.5, "1"):
            with self.subTest(radius=radius), self.assertRaises(core.MapError):
                core.observe(("...",), (0, 0), radius=radius)

    def test_invalid_maps_and_origin(self):
        for grid in ((), ("",), ("..", "."), (".x",)):
            with self.subTest(grid=grid), self.assertRaises(core.MapError):
                core.observe(grid, (0, 0))
        with self.assertRaises(core.MapError):
            core.observe(("#",), (0, 0))

    def test_invalid_observation_shapes_and_characters(self):
        for observation in ((), ("",), ("..", "."), (".x",)):
            with self.subTest(observation=observation), self.assertRaises(core.MapError):
                core.astar(observation, (0, 0), (0, 0))


class AStarTests(unittest.TestCase):
    def test_shortest_path(self):
        result = core.astar((".....", ".###.", "....."), (0, 0), (2, 4))
        self.assertEqual(result.steps, 6)
        self.assertTrue(result.reachable)
        self.assertTrue(all(abs(a[0]-b[0])+abs(a[1]-b[1]) == 1 for a,b in zip(result.path, result.path[1:])))

    def test_astar_matches_bfs_on_100_seeded_grids_including_unknown(self):
        for seed in range(100):
            rng = random.Random(seed)
            height, width = rng.randint(2, 8), rng.randint(2, 8)
            rows = [[rng.choices((".", "#", "?"), weights=(6, 2, 2))[0]
                     for _ in range(width)] for _ in range(height)]
            start, goal = (rng.randrange(height), rng.randrange(width)), (rng.randrange(height), rng.randrange(width))
            rows[start[0]][start[1]] = "."
            rows[goal[0]][goal[1]] = "."
            observation = tuple("".join(row) for row in rows)
            result = core.astar(observation, start, goal)
            with self.subTest(seed=seed, observation=observation, start=start, goal=goal):
                self.assertEqual(result.steps, bfs_steps(observation, start, goal))
                if result.path is not None:
                    self.assertTrue(all(observation[r][c] == "." for r, c in result.path))

    def test_hidden_world_differences_behind_solid_wall_do_not_change_observation_or_route(self):
        world_a = ("...#...", "...#...", "...#...", "...#...", "...#...")
        world_b = ("...####", "...#..#", "...##.#", "...#..#", "...####")
        start, goal = (2, 1), (2, 2)
        observed_a = core.observe(world_a, start)
        observed_b = core.observe(world_b, start)
        self.assertEqual(observed_a, observed_b)
        self.assertEqual(core.astar(observed_a, start, goal), core.astar(observed_b, start, goal))

    def test_occupied_or_unknown_endpoints_are_unreachable(self):
        for observation, start, goal in (((".#",), (0, 0), (0, 1)), ((".?",), (0, 0), (0, 1)), (("?.",), (0, 0), (0, 1))):
            with self.subTest(observation=observation):
                result = core.astar(observation, start, goal)
                self.assertIsNone(result.path)
                self.assertEqual(result.expanded, 0)

    def test_unreachable(self):
        result = core.astar((".#.", "###", "..."), (0, 0), (2, 2))
        self.assertFalse(result.reachable)
        self.assertIsNone(result.steps)

    def test_start_goal_and_bounds(self):
        self.assertEqual(core.astar((".",), (0, 0), (0, 0)).steps, 0)
        with self.assertRaises(core.MapError):
            core.astar(("..",), (0, 0), (0, 2))


class CLITests(unittest.TestCase):
    def test_json_deterministic_and_routes_observation(self):
        root = os.path.dirname(os.path.dirname(__file__))
        env = dict(os.environ, PYTHONPATH=os.path.join(root, "src"))
        command = [sys.executable, "-m", "occlusion_lab", "demo", "--json"]
        one = subprocess.check_output(command, cwd=root, env=env, text=True)
        two = subprocess.check_output(command, cwd=root, env=env, text=True)
        self.assertEqual(one, two)
        metrics = json.loads(one)
        observed = core.observe(WORLD, START, OBSERVATION_RADIUS)
        planned = core.astar(observed, START, GOAL)
        self.assertEqual(metrics["path_steps"], planned.steps)
        self.assertTrue(all(observed[r][c] == "." for r,c in planned.path))
        self.assertTrue(metrics["reachable_on_observed_free_cells"])
        self.assertEqual(len(metrics["path_cells"]), planned.steps + 1)

    def test_default_radius_metrics_and_configurable_zero_radius(self):
        root = os.path.dirname(os.path.dirname(__file__))
        env = dict(os.environ, PYTHONPATH=os.path.join(root, "src"))
        command = [sys.executable, "-m", "occlusion_lab", "demo", "--json"]
        default = json.loads(subprocess.check_output(command, cwd=root, env=env, text=True))
        self.assertEqual(default["observation_radius_manhattan"], OBSERVATION_RADIUS)
        self.assertEqual((default["path_steps"], default["expanded_nodes"],
                          default["observed_free_cells"], default["unknown_cells"]), (8, 9, 29, 31))
        limited = json.loads(subprocess.check_output(command + ["--radius", "0"], cwd=root, env=env, text=True))
        self.assertEqual(limited["observation_radius_manhattan"], 0)
        self.assertFalse(limited["reachable_on_observed_free_cells"])
        self.assertIsNone(limited["path_cells"])
        self.assertEqual(limited["unknown_cells"], len(WORLD) * len(WORLD[0]) - 1)

    def test_negative_radius_rejected_and_unreachable_explained(self):
        root = os.path.dirname(os.path.dirname(__file__))
        env = dict(os.environ, PYTHONPATH=os.path.join(root, "src"))
        command = [sys.executable, "-m", "occlusion_lab", "demo"]
        bad = subprocess.run(command + ["--radius", "-1"], cwd=root, env=env, text=True, capture_output=True)
        self.assertNotEqual(bad.returncode, 0)
        self.assertIn("--radius must be a non-negative integer", bad.stderr)
        limited = subprocess.check_output(command + ["--radius", "0"], cwd=root, env=env, text=True)
        self.assertIn("unknown cells are blocked for planning", limited)
        self.assertIn("does not prove the goal is unreachable in the hidden world", limited)

    def test_ascii_demo(self):
        root = os.path.dirname(os.path.dirname(__file__))
        env = dict(os.environ, PYTHONPATH=os.path.join(root, "src"))
        output = subprocess.check_output([sys.executable, "-m", "occlusion_lab", "demo"], cwd=root, env=env, text=True)
        self.assertIn("GROUND TRUTH", output)
        self.assertIn("OBSERVED MAP", output)
        self.assertIn("?", output)


if __name__ == "__main__":
    unittest.main()
