"""Reproducible benchmark and dynamic-cost experiment orchestration."""

from __future__ import annotations

import csv
import json
import random
import statistics
from dataclasses import asdict, replace
from pathlib import Path

from .algorithms import SearchResult, astar, dijkstra
from .graph import Edge, RoadGraph


def choose_pairs(graph: RoadGraph, count: int, seed: int) -> list[tuple[int, int]]:
    """Choose deterministic reachable pairs with meaningful geographic separation.

    Because subgraphs are BFS prefixes, pairing vertices near the beginning and
    end of discovery order avoids a benchmark dominated by trivial local trips.
    A fixed-seed random fallback handles unusual one-way/disconnected inputs.
    """

    vertices = list(getattr(graph, "active_vertices", graph.vertices()))
    if len(vertices) < 2:
        raise ValueError("at least two active vertices are required")
    rng = random.Random(seed)
    candidates: list[tuple[int, int]] = []
    stride = max(1, len(vertices) // (count * 8))
    for index in range(count * 3):
        source = vertices[min(len(vertices) - 1, index * stride)]
        destination = vertices[max(0, len(vertices) - 1 - index * stride)]
        result = dijkstra(graph, source, destination)
        if result.reachable and len(result.path) >= 5:
            candidates.append((source, destination))
            if len(candidates) == count:
                return candidates
    attempts = 0
    while len(candidates) < count and attempts < count * 100:
        attempts += 1
        source, destination = rng.sample(vertices, 2)
        result = dijkstra(graph, source, destination)
        if result.reachable and len(result.path) >= 5:
            candidates.append((source, destination))
    if len(candidates) != count:
        raise RuntimeError(f"could find only {len(candidates)} reachable query pairs")
    return candidates


def run_benchmarks(
    graph: RoadGraph,
    sizes: list[int],
    pairs_per_size: int,
    seed: int,
    output_dir: str | Path,
    timing_repetitions: int = 3,
) -> tuple[list[dict], list[dict]]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    graph_rows: list[dict] = []
    for size_index, size in enumerate(sizes):
        subgraph = graph.bfs_induced_subgraph(size, seed=1)
        active = list(subgraph.active_vertices)
        edge_count = sum(len(subgraph.adjacency[v]) for v in active)
        out_degrees = [len(subgraph.adjacency[v]) for v in active]
        graph_rows.append({
            "requested_size": size,
            "vertices": len(active),
            "directed_edges": edge_count,
            "average_out_degree": edge_count / len(active),
            "maximum_out_degree": max(out_degrees, default=0),
        })
        scale = subgraph.safe_geo_scale()
        pairs = choose_pairs(subgraph, pairs_per_size, seed + size_index)
        for pair_index, (source, destination) in enumerate(pairs, 1):
            dij_runs = [dijkstra(subgraph, source, destination) for _ in range(timing_repetitions)]
            heuristic = subgraph.geo_heuristic(destination, scale)
            ast_runs = [astar(subgraph, source, destination, heuristic) for _ in range(timing_repetitions)]
            dij = _median_timed_result(dij_runs)
            ast = _median_timed_result(ast_runs)
            if dij.cost != ast.cost:
                raise AssertionError(f"cost mismatch for {source}->{destination}: {dij.cost} != {ast.cost}")
            for result in (dij, ast):
                row = asdict(result)
                original_ids = getattr(subgraph, "original_vertex_ids", None)
                row["subgraph_source"] = result.source
                row["subgraph_destination"] = result.destination
                if original_ids is not None:
                    row["source"] = original_ids[result.source]
                    row["destination"] = original_ids[result.destination]
                row.update({
                    "graph_size": len(active),
                    "pair": pair_index,
                    "path_length_vertices": len(result.path),
                    "heuristic_scale": scale,
                })
                path = [original_ids[v] for v in result.path] if original_ids is not None else result.path
                row["path"] = " ".join(map(str, path))
                rows.append(row)
    _write_csv(output / "raw_results.csv", rows)
    _write_csv(output / "graph_statistics.csv", graph_rows)
    summary = summarize(rows)
    _write_csv(output / "summary_results.csv", summary)
    (output / "metadata.json").write_text(json.dumps({
        "seed": seed,
        "pairs_per_size": pairs_per_size,
        "sizes": sizes,
        "dataset": graph.name,
        "timing_repetitions_per_query": timing_repetitions,
    }, indent=2), encoding="utf-8")
    return rows, summary


def _median_timed_result(results: list[SearchResult]) -> SearchResult:
    if not results:
        raise ValueError("at least one timing result is required")
    representative = sorted(results, key=lambda item: item.execution_time_ms)[len(results) // 2]
    return replace(representative)


def summarize(rows: list[dict]) -> list[dict]:
    groups: dict[tuple[int, str], list[dict]] = {}
    for row in rows:
        groups.setdefault((int(row["graph_size"]), str(row["algorithm"])), []).append(row)
    summary: list[dict] = []
    for (size, algorithm), items in sorted(groups.items()):
        summary.append({
            "graph_size": size,
            "algorithm": algorithm,
            "queries": len(items),
            "average_cost": statistics.fmean(float(x["cost"]) for x in items),
            "average_vertices_explored": statistics.fmean(int(x["vertices_explored"]) for x in items),
            "average_edges_examined": statistics.fmean(int(x["edges_examined"]) for x in items),
            "average_execution_time_ms": statistics.fmean(float(x["execution_time_ms"]) for x in items),
            "median_execution_time_ms": statistics.median(float(x["execution_time_ms"]) for x in items),
        })
    return summary


def run_dynamic_experiment(
    graph: RoadGraph,
    source: int,
    destination: int,
    output_dir: str | Path,
    congestion_multiplier: float = 5.0,
) -> dict:
    """Congest the middle third of a baseline path and recompute the route."""

    baseline = dijkstra(graph, source, destination)
    if not baseline.reachable or len(baseline.path) < 4:
        raise ValueError("dynamic experiment needs a reachable path of at least four vertices")
    first = len(baseline.path) // 3
    last = max(first + 1, 2 * len(baseline.path) // 3)
    congested = set(zip(baseline.path[first:last], baseline.path[first + 1:last + 1]))

    def dynamic_weight(u: int, edge: Edge) -> float:
        # alpha=1; c(u,v)=4*d(u,v) on congested arcs and 0 otherwise; beta=1.
        return edge.weight * (congestion_multiplier if (u, edge.to) in congested else 1.0)

    updated = dijkstra(graph, source, destination, dynamic_weight)
    report = {
        "source": getattr(graph, "original_vertex_ids", [])[source] if hasattr(graph, "original_vertex_ids") else source,
        "destination": getattr(graph, "original_vertex_ids", [])[destination] if hasattr(graph, "original_vertex_ids") else destination,
        "subgraph_source": source,
        "subgraph_destination": destination,
        "alpha": 1.0,
        "beta": 1.0,
        "congestion_multiplier": congestion_multiplier,
        "congested_edges": len(congested),
        "baseline_cost": baseline.cost,
        "dynamic_cost": updated.cost,
        "baseline_path": [graph.original_vertex_ids[v] for v in baseline.path] if hasattr(graph, "original_vertex_ids") else baseline.path,
        "dynamic_path": [graph.original_vertex_ids[v] for v in updated.path] if hasattr(graph, "original_vertex_ids") else updated.path,
        "baseline_subgraph_path": baseline.path,
        "dynamic_subgraph_path": updated.path,
        "route_changed": baseline.path != updated.path,
        "shared_path_edges": len(set(zip(baseline.path, baseline.path[1:])) & set(zip(updated.path, updated.path[1:]))),
    }
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    (output / "dynamic_result.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def _write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

