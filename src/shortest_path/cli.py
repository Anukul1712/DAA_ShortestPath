"""Command-line interface for queries, benchmarks, and bonus experiments."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict

from .algorithms import astar, dijkstra
from .dimacs import read_dimacs_graph
from .experiments import run_benchmarks, run_dynamic_experiment, run_heuristic_study
from .visualization import generate_heuristic_study_plots, generate_plots


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="DIMACS road-network shortest paths")
    root.add_argument("--graph", required=True, help="DIMACS .gr or .gr.gz file")
    root.add_argument("--coordinates", help="DIMACS .co or .co.gz file")
    commands = root.add_subparsers(dest="command", required=True)
    commands.add_parser("stats")
    query = commands.add_parser("query")
    query.add_argument("source", type=int)
    query.add_argument("destination", type=int)
    query.add_argument("--algorithm", choices=("dijkstra", "astar"), default="astar")
    query.add_argument("--heuristic-weight", type=float, default=1.0, help="A* lambda; values above 1 may be suboptimal")
    benchmark = commands.add_parser("benchmark")
    benchmark.add_argument("--sizes", type=int, nargs="+", default=[1000, 5000, 10000, 25000, 50000])
    benchmark.add_argument("--pairs", type=int, default=5)
    benchmark.add_argument("--seed", type=int, default=2026)
    benchmark.add_argument("--repetitions", type=int, default=3, help="timing repetitions per algorithm/query")
    benchmark.add_argument("--output", default="results", help="results root containing tables/ and plots/")
    study = commands.add_parser("heuristic-study")
    study.add_argument("--sizes", type=int, nargs="+", default=[1000, 5000, 10000, 25000, 50000])
    study.add_argument("--pairs", type=int, default=5)
    study.add_argument("--seed", type=int, default=2026)
    study.add_argument("--repetitions", type=int, default=3)
    study.add_argument("--weights", type=float, nargs="+", default=[0, 0.25, 0.5, 0.75, 1, 1.25, 1.5, 2])
    study.add_argument("--output", default="results", help="results root containing tables/ and plots/")
    dynamic = commands.add_parser("dynamic")
    dynamic.add_argument("source", type=int)
    dynamic.add_argument("destination", type=int)
    dynamic.add_argument("--output", default="results/bonus")
    return root


def main() -> None:
    args = parser().parse_args()
    graph = read_dimacs_graph(args.graph, args.coordinates)
    if args.command == "stats":
        result = graph.stats()
    elif args.command == "query":
        if args.algorithm == "dijkstra":
            result = asdict(dijkstra(graph, args.source, args.destination))
        else:
            result = asdict(astar(
                graph,
                args.source,
                args.destination,
                graph.geo_heuristic(args.destination),
                heuristic_weight=args.heuristic_weight,
            ))
    elif args.command == "benchmark":
        from pathlib import Path
        output = Path(args.output)
        _raw, result = run_benchmarks(graph, args.sizes, args.pairs, args.seed, output / "tables", args.repetitions)
        generate_plots(output / "tables", output / "plots")
    elif args.command == "heuristic-study":
        from pathlib import Path
        output = Path(args.output)
        _raw, result = run_heuristic_study(
            graph,
            args.sizes,
            args.pairs,
            args.seed,
            output / "tables",
            tuple(args.weights),
            args.repetitions,
        )
        generate_heuristic_study_plots(output / "tables", output / "plots")
    else:
        result = run_dynamic_experiment(graph, args.source, args.destination, args.output)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

