"""One-command reproducible experiment pipeline."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shortest_path.dimacs import read_dimacs_graph
from shortest_path.experiments import run_benchmarks, run_dynamic_experiment
from shortest_path.visualization import generate_plots, plot_dynamic_routes


def main() -> None:
    raw = ROOT / "data" / "raw"
    output = ROOT / "results" / "generated"
    graph = read_dimacs_graph(raw / "USA-road-d.NY.gr.gz", raw / "USA-road-d.NY.co.gz")
    rows, summary = run_benchmarks(graph, [1000, 5000, 10000, 25000, 50000], 5, 2026, output, timing_repetitions=5)
    largest = [r for r in rows if r["graph_size"] == max(x["graph_size"] for x in rows) and r["algorithm"] == "dijkstra"]
    chosen = max(largest, key=lambda row: row["path_length_vertices"])
    subgraph = graph.bfs_induced_subgraph(50000, seed=1)
    run_dynamic_experiment(subgraph, chosen["subgraph_source"], chosen["subgraph_destination"], output)
    paths = generate_plots(output)
    paths.append(plot_dynamic_routes(subgraph, output))
    print(f"Wrote {len(rows)} raw rows, {len(summary)} summary rows, and {len(paths)} plots to {output}")


if __name__ == "__main__":
    main()

