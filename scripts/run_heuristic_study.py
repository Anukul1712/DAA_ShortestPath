"""Run only the A* heuristic-strength experiment and its plots."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shortest_path.dimacs import read_dimacs_graph
from shortest_path.experiments import run_heuristic_study
from shortest_path.visualization import generate_heuristic_study_plots


def main() -> None:
    raw = ROOT / "data" / "raw"
    tables = ROOT / "results" / "tables"
    plots = ROOT / "results" / "plots"
    graph = read_dimacs_graph(raw / "USA-road-d.NY.gr.gz", raw / "USA-road-d.NY.co.gz")
    rows, summary = run_heuristic_study(
        graph,
        [1000, 5000, 10000, 25000, 50000],
        pairs_per_size=5,
        seed=2026,
        output_dir=tables,
        timing_repetitions=5,
    )
    paths = generate_heuristic_study_plots(tables, plots)
    print(f"Wrote {len(rows)} raw rows, {len(summary)} summary rows, and {len(paths)} heuristic-study plots")


if __name__ == "__main__":
    main()
