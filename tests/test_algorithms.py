import math
import tempfile
import unittest
from pathlib import Path

from shortest_path.algorithms import astar, dijkstra
from shortest_path.experiments import run_dynamic_experiment, run_dynamic_parameter_study
from shortest_path.graph import Edge, RoadGraph


class AlgorithmTests(unittest.TestCase):
    def setUp(self):
        adjacency = [[], [Edge(2, 2), Edge(3, 10)], [Edge(3, 3), Edge(4, 9)], [Edge(4, 1)], []]
        coordinates = [None, (0.0, 0.0), (0.00001, 0.0), (0.00002, 0.0), (0.00003, 0.0)]
        self.graph = RoadGraph(adjacency, coordinates, "fixture")

    def test_dijkstra_reconstructs_optimal_path(self):
        result = dijkstra(self.graph, 1, 4)
        self.assertEqual(result.cost, 6)
        self.assertEqual(result.path, [1, 2, 3, 4])

    def test_astar_matches_dijkstra(self):
        expected = dijkstra(self.graph, 1, 4)
        actual = astar(self.graph, 1, 4, self.graph.geo_heuristic(4))
        self.assertEqual(actual.cost, expected.cost)
        self.assertEqual(actual.path, expected.path)

    def test_zero_weight_astar_matches_dijkstra_search(self):
        expected = dijkstra(self.graph, 1, 4)
        actual = astar(
            self.graph,
            1,
            4,
            self.graph.geo_heuristic(4),
            heuristic_weight=0.0,
        )
        self.assertEqual(actual.cost, expected.cost)
        self.assertEqual(actual.vertices_explored, expected.vertices_explored)
        self.assertEqual(actual.edges_examined, expected.edges_examined)

    def test_negative_heuristic_weight_is_rejected(self):
        with self.assertRaises(ValueError):
            astar(self.graph, 1, 4, self.graph.geo_heuristic(4), heuristic_weight=-0.1)

    def test_disconnected_pair(self):
        result = dijkstra(self.graph, 4, 1)
        self.assertFalse(result.reachable)
        self.assertTrue(math.isinf(result.cost))
        self.assertEqual(result.path, [])

    def test_source_equals_destination(self):
        result = dijkstra(self.graph, 2, 2)
        self.assertEqual(result.path, [2])
        self.assertEqual(result.cost, 0)

    def test_induced_subgraph_is_dense_and_traceable(self):
        subgraph = self.graph.bfs_induced_subgraph(3, seed=1)
        self.assertEqual(subgraph.vertex_count, 3)
        self.assertEqual(subgraph.active_vertices, (1, 2, 3))
        self.assertEqual(subgraph.original_vertex_ids[1], 1)
        self.assertEqual(len(subgraph.adjacency), 4)

    def test_dynamic_experiment_reports_distance_cost_and_avoidance(self):
        adjacency = [
            [],
            [Edge(2, 1)],
            [Edge(3, 1), Edge(6, 2)],
            [Edge(4, 1)],
            [Edge(5, 1)],
            [],
            [Edge(4, 2)],
        ]
        graph = RoadGraph(adjacency, [None] * 7, "dynamic-fixture")
        with tempfile.TemporaryDirectory() as directory:
            report = run_dynamic_experiment(graph, 1, 5, Path(directory), congestion_multiplier=5)
        self.assertEqual(report["baseline_base_cost"], 4)
        self.assertEqual(report["baseline_cost_under_congestion"], 12)
        self.assertEqual(report["rerouted_base_cost"], 6)
        self.assertEqual(report["rerouted_dynamic_cost"], 6)
        self.assertEqual(report["congested_edges_avoided"], 2)
        self.assertEqual(report["congested_edges_used_by_reroute"], 0)

    def test_dynamic_parameter_study_depends_on_beta_alpha_ratio(self):
        adjacency = [
            [],
            [Edge(2, 1)],
            [Edge(3, 1), Edge(6, 2)],
            [Edge(4, 1)],
            [Edge(5, 1)],
            [],
            [Edge(4, 2)],
        ]
        graph = RoadGraph(adjacency, [None] * 7, "parameter-fixture")
        with tempfile.TemporaryDirectory() as directory:
            rows = run_dynamic_parameter_study(
                graph, 1, 5, Path(directory), alphas=(1.0, 2.0), betas=(0.5, 1.0)
            )
        by_key = {(row["alpha"], row["beta"]): row for row in rows}
        first = by_key[(1.0, 0.5)]
        scaled = by_key[(2.0, 1.0)]
        self.assertEqual(first["beta_alpha_ratio"], scaled["beta_alpha_ratio"])
        self.assertEqual(first["route_id"], scaled["route_id"])
        self.assertEqual(first["physical_distance_meters"], scaled["physical_distance_meters"])
        self.assertEqual(first["congested_edges_used"], scaled["congested_edges_used"])


if __name__ == "__main__":
    unittest.main()

