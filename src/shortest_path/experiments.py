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
                    "weight_unit_meters": subgraph.weight_unit_meters,
                    "cost_meters": result.cost * subgraph.weight_unit_meters,
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
            "average_cost_meters": statistics.fmean(float(x["cost_meters"]) for x in items),
            "average_vertices_explored": statistics.fmean(int(x["vertices_explored"]) for x in items),
            "average_edges_examined": statistics.fmean(int(x["edges_examined"]) for x in items),
            "average_execution_time_ms": statistics.fmean(float(x["execution_time_ms"]) for x in items),
            "median_execution_time_ms": statistics.median(float(x["execution_time_ms"]) for x in items),
        })
    return summary


def run_heuristic_study(
    graph: RoadGraph,
    sizes: list[int],
    pairs_per_size: int,
    seed: int,
    output_dir: str | Path,
    heuristic_weights: tuple[float, ...] = (0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0),
    timing_repetitions: int = 3,
) -> tuple[list[dict], list[dict]]:
    """Measure how heuristic strength changes work, time, and optimality.

    Weights from zero through one retain the guarantee of an admissible base
    heuristic. Values above one are weighted A*: they may search less but no
    longer have the exact-optimality guarantee used by standard A*.
    """

    if not heuristic_weights or any(weight < 0 for weight in heuristic_weights):
        raise ValueError("heuristic weights must be a non-empty set of non-negative values")
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    for size_index, size in enumerate(sizes):
        subgraph = graph.bfs_induced_subgraph(size, seed=1)
        scale = subgraph.safe_geo_scale()
        pairs = choose_pairs(subgraph, pairs_per_size, seed + size_index)
        original_ids = getattr(subgraph, "original_vertex_ids", None)
        for pair_index, (source, destination) in enumerate(pairs, 1):
            optimum = dijkstra(subgraph, source, destination)
            base_heuristic = subgraph.geo_heuristic(destination, scale)
            for weight in heuristic_weights:
                runs = [
                    astar(
                        subgraph,
                        source,
                        destination,
                        base_heuristic,
                        heuristic_weight=weight,
                    )
                    for _ in range(timing_repetitions)
                ]
                result = _median_timed_result(runs)
                cost_ratio = result.cost / optimum.cost
                if weight == 0:
                    heuristic_class = "zero_heuristic"
                elif weight < 1:
                    heuristic_class = "scaled_admissible"
                elif weight == 1:
                    heuristic_class = "standard_admissible"
                else:
                    heuristic_class = "weighted_no_exact_guarantee"
                rows.append({
                    "graph_size": len(subgraph.active_vertices),
                    "pair": pair_index,
                    "source": original_ids[source] if original_ids is not None else source,
                    "destination": original_ids[destination] if original_ids is not None else destination,
                    "heuristic_weight": weight,
                    "heuristic_class": heuristic_class,
                    "safe_heuristic_scale": scale,
                    "optimal_cost": optimum.cost,
                    "returned_cost": result.cost,
                    "cost_ratio": cost_ratio,
                    "optimality_gap_percent": 100.0 * (cost_ratio - 1.0),
                    "is_optimal": result.cost == optimum.cost,
                    "vertices_explored": result.vertices_explored,
                    "edges_examined": result.edges_examined,
                    "execution_time_ms": result.execution_time_ms,
                    "path_length_vertices": len(result.path),
                })

    groups: dict[tuple[int, float], list[dict]] = {}
    for row in rows:
        key = (int(row["graph_size"]), float(row["heuristic_weight"]))
        groups.setdefault(key, []).append(row)
    summary: list[dict] = []
    for (size, weight), items in sorted(groups.items()):
        summary.append({
            "graph_size": size,
            "heuristic_weight": weight,
            "heuristic_class": items[0]["heuristic_class"],
            "queries": len(items),
            "optimal_queries": sum(str(item["is_optimal"]).lower() == "true" for item in items),
            "optimality_rate_percent": 100.0 * sum(bool(item["is_optimal"]) for item in items) / len(items),
            "average_optimality_gap_percent": statistics.fmean(float(item["optimality_gap_percent"]) for item in items),
            "maximum_optimality_gap_percent": max(float(item["optimality_gap_percent"]) for item in items),
            "average_vertices_explored": statistics.fmean(int(item["vertices_explored"]) for item in items),
            "average_edges_examined": statistics.fmean(int(item["edges_examined"]) for item in items),
            "average_execution_time_ms": statistics.fmean(float(item["execution_time_ms"]) for item in items),
        })
    zero_by_size = {
        int(row["graph_size"]): row for row in summary if float(row["heuristic_weight"]) == 0.0
    }
    for row in summary:
        zero = zero_by_size[int(row["graph_size"])]
        row["vertices_percent_of_zero"] = (
            100.0 * float(row["average_vertices_explored"]) / float(zero["average_vertices_explored"])
        )
        row["edges_percent_of_zero"] = (
            100.0 * float(row["average_edges_examined"]) / float(zero["average_edges_examined"])
        )
        row["runtime_percent_of_zero"] = (
            100.0 * float(row["average_execution_time_ms"]) / float(zero["average_execution_time_ms"])
        )

    _write_csv(output / "heuristic_study_raw.csv", rows)
    _write_csv(output / "heuristic_study_summary.csv", summary)
    (output / "heuristic_study_metadata.json").write_text(json.dumps({
        "seed": seed,
        "pairs_per_size": pairs_per_size,
        "sizes": sizes,
        "heuristic_weights": list(heuristic_weights),
        "timing_repetitions_per_query": timing_repetitions,
        "interpretation": "weights <= 1 preserve base-heuristic admissibility; weights > 1 are weighted A*",
    }, indent=2), encoding="utf-8")
    return rows, summary


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

    def path_cost(path: list[int], use_dynamic_weights: bool) -> float:
        total = 0.0
        for u, v in zip(path, path[1:]):
            candidates = [edge for edge in graph.adjacency[u] if edge.to == v]
            if not candidates:
                raise AssertionError(f"path contains missing edge {u}->{v}")
            if use_dynamic_weights:
                total += min(dynamic_weight(u, edge) for edge in candidates)
            else:
                total += min(edge.weight for edge in candidates)
        return total

    baseline_edges = list(zip(baseline.path, baseline.path[1:]))
    updated_edges = list(zip(updated.path, updated.path[1:]))
    baseline_edge_set = set(baseline_edges)
    updated_edge_set = set(updated_edges)
    shared_edges = baseline_edge_set & updated_edge_set
    union_edges = baseline_edge_set | updated_edge_set
    congested_used = congested & updated_edge_set
    baseline_cost_under_congestion = path_cost(baseline.path, True)
    updated_base_cost = path_cost(updated.path, False)

    prefix_edges = 0
    for baseline_edge, updated_edge in zip(baseline_edges, updated_edges):
        if baseline_edge != updated_edge:
            break
        prefix_edges += 1
    suffix_edges = 0
    for baseline_edge, updated_edge in zip(reversed(baseline_edges), reversed(updated_edges)):
        if baseline_edge != updated_edge:
            break
        suffix_edges += 1

    unit = graph.weight_unit_meters
    distance_increase = updated_base_cost - baseline.cost
    dynamic_savings = baseline_cost_under_congestion - updated.cost
    original_ids = getattr(graph, "original_vertex_ids", None)

    report = {
        "source": original_ids[source] if original_ids is not None else source,
        "destination": original_ids[destination] if original_ids is not None else destination,
        "subgraph_source": source,
        "subgraph_destination": destination,
        "alpha": 1.0,
        "beta": 1.0,
        "congestion_multiplier": congestion_multiplier,
        "congested_edges": len(congested),
        "congested_subgraph_edges": [list(edge) for edge in sorted(congested)],
        "baseline_cost": baseline.cost,
        "dynamic_cost": updated.cost,
        "baseline_base_cost": baseline.cost,
        "baseline_cost_under_congestion": baseline_cost_under_congestion,
        "rerouted_base_cost": updated_base_cost,
        "rerouted_dynamic_cost": updated.cost,
        "weight_unit_meters": unit,
        "baseline_cost_meters": baseline.cost * unit,
        "dynamic_cost_meters": updated.cost * unit,
        "baseline_base_distance_meters": baseline.cost * unit,
        "baseline_cost_under_congestion_meters_equivalent": baseline_cost_under_congestion * unit,
        "rerouted_base_distance_meters": updated_base_cost * unit,
        "rerouted_dynamic_cost_meters_equivalent": updated.cost * unit,
        "distance_increase_meters": distance_increase * unit,
        "distance_increase_percent": 100.0 * distance_increase / baseline.cost,
        "dynamic_savings_vs_staying_meters_equivalent": dynamic_savings * unit,
        "dynamic_savings_vs_staying_percent": 100.0 * dynamic_savings / baseline_cost_under_congestion,
        "baseline_path": [original_ids[v] for v in baseline.path] if original_ids is not None else baseline.path,
        "dynamic_path": [original_ids[v] for v in updated.path] if original_ids is not None else updated.path,
        "baseline_subgraph_path": baseline.path,
        "dynamic_subgraph_path": updated.path,
        "route_changed": baseline.path != updated.path,
        "baseline_path_vertices": len(baseline.path),
        "rerouted_path_vertices": len(updated.path),
        "baseline_path_edges": len(baseline_edges),
        "rerouted_path_edges": len(updated_edges),
        "shared_path_edges": len(shared_edges),
        "baseline_only_edges": len(baseline_edge_set - updated_edge_set),
        "rerouted_only_edges": len(updated_edge_set - baseline_edge_set),
        "edge_jaccard_similarity_percent": 100.0 * len(shared_edges) / len(union_edges),
        "common_prefix_edges": prefix_edges,
        "common_suffix_edges": suffix_edges,
        "congested_edges_used_by_reroute": len(congested_used),
        "congested_edges_avoided": len(congested - updated_edge_set),
        "congested_edges_avoided_percent": 100.0 * len(congested - updated_edge_set) / len(congested),
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

