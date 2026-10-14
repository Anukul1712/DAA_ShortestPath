"""Command-line interface for queries, benchmarks, and bonus experiments."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict

from .algorithms import astar, dijkstra
from .dimacs import read_dimacs_graph
from .experiments import run_benchmarks, run_dynamic_experiment
from .visualization import generate_plots


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
    benchmark = commands.add_parser("benchmark")
    benchmark.add_argument("--sizes", type=int, nargs="+", default=[1000, 5000, 10000, 25000, 50000])
    benchmark.add_argument("--pairs", type=int, default=5)
    benchmark.add_argument("--seed", type=int, default=2026)
    benchmark.add_argument("--repetitions", type=int, default=3, help="timing repetitions per algorithm/query")
    benchmark.add_argument("--output", default="results/generated")
    dynamic = commands.add_parser("dynamic")
    dynamic.add_argument("source", type=int)
    dynamic.add_argument("destination", type=int)
    dynamic.add_argument("--output", default="results/generated")
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
            result = asdict(astar(graph, args.source, args.destination, graph.geo_heuristic(args.destination)))
    elif args.command == "benchmark":
        _raw, result = run_benchmarks(graph, args.sizes, args.pairs, args.seed, args.output, args.repetitions)
        generate_plots(args.output)
    else:
        result = run_dynamic_experiment(graph, args.source, args.destination, args.output)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

