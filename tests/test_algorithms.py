import math
import unittest

from shortest_path.algorithms import astar, dijkstra
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


if __name__ == "__main__":
    unittest.main()

