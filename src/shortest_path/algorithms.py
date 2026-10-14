"""Independent Dijkstra and A* implementations with instrumentation."""

from __future__ import annotations

from dataclasses import dataclass
from heapq import heappop, heappush
from math import inf
from time import perf_counter_ns
from typing import Callable

from .graph import Edge, RoadGraph

WeightFunction = Callable[[int, Edge], float]


@dataclass(slots=True)
class SearchResult:
    algorithm: str
    source: int
    destination: int
    cost: float
    path: list[int]
    vertices_explored: int
    edges_examined: int
    execution_time_ms: float
    reachable: bool


def _path(parent: list[int], source: int, destination: int) -> list[int]:
    if source == destination:
        return [source]
    if parent[destination] == -1:
        return []
    result = [destination]
    while result[-1] != source:
        result.append(parent[result[-1]])
        if result[-1] == -1:
            return []
    result.reverse()
    return result


def dijkstra(
    graph: RoadGraph,
    source: int,
    destination: int,
    weight_fn: WeightFunction | None = None,
) -> SearchResult:
    """Shortest path with a binary min-heap; no library graph routines used."""

    graph.validate_vertex(source)
    graph.validate_vertex(destination)
    started = perf_counter_ns()
    distances = [inf] * (graph.vertex_count + 1)
    parent = [-1] * (graph.vertex_count + 1)
    settled = bytearray(graph.vertex_count + 1)
    distances[source] = 0.0
    heap: list[tuple[float, int]] = [(0.0, source)]
    vertices_explored = edges_examined = 0
    while heap:
        distance_u, u = heappop(heap)
        if settled[u] or distance_u != distances[u]:
            continue
        settled[u] = 1
        vertices_explored += 1
        if u == destination:
            break
        for edge in graph.adjacency[u]:
            edges_examined += 1
            weight = edge.weight if weight_fn is None else weight_fn(u, edge)
            if weight < 0:
                raise ValueError("Dijkstra requires non-negative edge weights")
            candidate = distance_u + weight
            if candidate < distances[edge.to]:
                distances[edge.to] = candidate
                parent[edge.to] = u
                heappush(heap, (candidate, edge.to))
    elapsed = (perf_counter_ns() - started) / 1_000_000
    reachable = distances[destination] < inf
    return SearchResult(
        "dijkstra", source, destination, distances[destination],
        _path(parent, source, destination) if reachable else [],
        vertices_explored, edges_examined, elapsed, reachable,
    )


def astar(
    graph: RoadGraph,
    source: int,
    destination: int,
    heuristic: Callable[[int], float],
    weight_fn: WeightFunction | None = None,
    heuristic_weight: float = 1.0,
) -> SearchResult:
    """A* graph search with reopen support and explicit path reconstruction.

    A weight in [0,1] preserves admissibility when the supplied heuristic is
    admissible. Values above 1 implement weighted A* and may be suboptimal.
    """

    graph.validate_vertex(source)
    graph.validate_vertex(destination)
    if heuristic_weight < 0:
        raise ValueError("heuristic_weight must be non-negative")

    def estimate(vertex: int) -> float:
        return 0.0 if heuristic_weight == 0 else heuristic_weight * heuristic(vertex)

    started = perf_counter_ns()
    g_score = [inf] * (graph.vertex_count + 1)
    parent = [-1] * (graph.vertex_count + 1)
    closed = bytearray(graph.vertex_count + 1)
    g_score[source] = 0.0
    heap: list[tuple[float, float, int]] = [(estimate(source), 0.0, source)]
    vertices_explored = edges_examined = 0
    while heap:
        _f, distance_u, u = heappop(heap)
        if closed[u] or distance_u != g_score[u]:
            continue
        closed[u] = 1
        vertices_explored += 1
        if u == destination:
            break
        for edge in graph.adjacency[u]:
            edges_examined += 1
            weight = edge.weight if weight_fn is None else weight_fn(u, edge)
            if weight < 0:
                raise ValueError("A* requires non-negative edge weights")
            candidate = distance_u + weight
            if candidate < g_score[edge.to]:
                g_score[edge.to] = candidate
                parent[edge.to] = u
                if closed[edge.to]:
                    closed[edge.to] = 0
                heappush(heap, (candidate + estimate(edge.to), candidate, edge.to))
    elapsed = (perf_counter_ns() - started) / 1_000_000
    reachable = g_score[destination] < inf
    return SearchResult(
        "astar", source, destination, g_score[destination],
        _path(parent, source, destination) if reachable else [],
        vertices_explored, edges_examined, elapsed, reachable,
    )

