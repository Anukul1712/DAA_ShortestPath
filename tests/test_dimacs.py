import gzip
import tempfile
import unittest
from pathlib import Path

from shortest_path.dimacs import read_dimacs_graph


class DimacsTests(unittest.TestCase):
    def test_reads_compressed_graph_and_coordinates(self):
        with tempfile.TemporaryDirectory() as folder:
            graph_path = Path(folder) / "tiny.gr.gz"
            coords_path = Path(folder) / "tiny.co.gz"
            with gzip.open(graph_path, "wt", encoding="ascii") as stream:
                stream.write("c demo\np sp 3 2\na 1 2 7\na 2 3 4\n")
            with gzip.open(coords_path, "wt", encoding="ascii") as stream:
                stream.write(
                    "p aux sp co 3\n"
                    "v 1 -74000000 40700000\n"
                    "v 2 -73900000 40800000\n"
                    "v 3 -73800000 40900000\n"
                )
            graph = read_dimacs_graph(graph_path, coords_path)
            self.assertEqual(graph.vertex_count, 3)
            self.assertEqual(graph.edge_count, 2)
            self.assertEqual(graph.coordinates[1], (-74.0, 40.7))
            self.assertEqual(graph.weight_unit_meters, 1.0)

    def test_usa_distance_family_uses_decimeter_unit(self):
        with tempfile.TemporaryDirectory() as folder:
            graph_path = Path(folder) / "USA-road-d.TEST.gr"
            graph_path.write_text("p sp 2 1\na 1 2 803\n", encoding="ascii")
            graph = read_dimacs_graph(graph_path)
            self.assertEqual(graph.weight_unit_meters, 0.1)
            self.assertAlmostEqual(graph.adjacency[1][0].weight * graph.weight_unit_meters, 80.3)


if __name__ == "__main__":
    unittest.main()

