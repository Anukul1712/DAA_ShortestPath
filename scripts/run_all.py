"""One-command reproducible experiment pipeline."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ.setdefault("MPLBACKEND", "Agg")

from shortest_path.dimacs import read_dimacs_graph
from shortest_path.experiments import (
    run_benchmarks,
    run_dynamic_experiment,
    run_dynamic_parameter_study,
    run_heuristic_study,
)
from shortest_path.visualization import (
    generate_dynamic_analysis_plots,
    generate_dynamic_parameter_study_plots,
    generate_heuristic_study_plots,
    generate_plots,
    plot_dynamic_routes,
)
from validate_outputs import validate_outputs


def main() -> None:
    raw = ROOT / "data" / "raw"
    tables = ROOT / "results" / "tables"
    plots = ROOT / "results" / "plots"
    bonus = ROOT / "results" / "bonus"
    graph_path = raw / "USA-road-d.NY.gr.gz"
    coordinate_path = raw / "USA-road-d.NY.co.gz"
    missing = [path for path in (graph_path, coordinate_path) if not path.is_file()]
    if missing:
        names = ", ".join(path.name for path in missing)
        raise SystemExit(f"Missing dataset file(s): {names}. Run: python scripts/download_data.py")
    graph = read_dimacs_graph(graph_path, coordinate_path)
    rows, summary = run_benchmarks(graph, [1000, 5000, 10000, 25000, 50000], 5, 2026, tables, timing_repetitions=5)
    largest = [r for r in rows if r["graph_size"] == max(x["graph_size"] for x in rows) and r["algorithm"] == "dijkstra"]
    chosen = max(largest, key=lambda row: row["path_length_vertices"])
    subgraph = graph.bfs_induced_subgraph(50000, seed=1)
    run_dynamic_experiment(subgraph, chosen["subgraph_source"], chosen["subgraph_destination"], bonus)
    run_dynamic_parameter_study(subgraph, chosen["subgraph_source"], chosen["subgraph_destination"], bonus)
    run_heuristic_study(
        graph, [1000, 5000, 10000, 25000, 50000], 5, 2026, tables,
        timing_repetitions=5,
    )
    paths = generate_plots(tables, plots)
    paths.extend(generate_heuristic_study_plots(tables, plots))
    paths.append(plot_dynamic_routes(subgraph, bonus, plots))
    paths.extend(generate_dynamic_analysis_plots(subgraph, bonus, plots))
    paths.extend(generate_dynamic_parameter_study_plots(bonus, plots))
    print(f"Wrote {len(rows)} raw rows, {len(summary)} summary rows, and {len(paths)} plots under {ROOT / 'results'}")
    validate_outputs(ROOT)


if __name__ == "__main__":
    main()

