"""Compact adjacency-list representation for a directed road network."""

from __future__ import annotations

from dataclasses import dataclass
from math import asin, cos, hypot, radians, sin, sqrt
from typing import Callable, Iterable


@dataclass(frozen=True, slots=True)
class Edge:
    """A directed weighted arc."""

    to: int
    weight: int


class RoadGraph:
    """Directed weighted graph with 1-based vertex identifiers.

    ``adjacency[0]`` and ``coordinates[0]`` are unused so DIMACS vertex IDs can
    be used directly without a hash-table translation.
    """

    def __init__(
        self,
        adjacency: list[list[Edge]],
        coordinates: list[tuple[float, float] | None] | None = None,
        name: str = "road-network",
    ) -> None:
        if not adjacency:
            adjacency = [[]]
        self.adjacency = adjacency
        self.coordinates = coordinates or [None] * len(adjacency)
        if len(self.coordinates) < len(adjacency):
            self.coordinates.extend([None] * (len(adjacency) - len(self.coordinates)))
        self.name = name
        self.edge_count = sum(len(edges) for edges in adjacency)
        known_latitudes = [point[1] for point in self.coordinates if point is not None]
        mean_latitude = sum(known_latitudes) / len(known_latitudes) if known_latitudes else 0.0
        self._projection_cosine = cos(radians(mean_latitude))

    @property
    def vertex_count(self) -> int:
        return len(self.adjacency) - 1

    def vertices(self) -> range:
        return range(1, len(self.adjacency))

    def validate_vertex(self, vertex: int) -> None:
        if not 1 <= vertex <= self.vertex_count:
            raise ValueError(f"vertex {vertex} is outside 1..{self.vertex_count}")

    def stats(self) -> dict[str, float | int | str]:
        out_degrees = [len(self.adjacency[v]) for v in self.vertices()]
        indegrees = [0] * (self.vertex_count + 1)
        for u in self.vertices():
            for edge in self.adjacency[u]:
                indegrees[edge.to] += 1
        total_degrees = [out_degrees[v - 1] + indegrees[v] for v in self.vertices()]
        return {
            "name": self.name,
            "vertices": self.vertex_count,
            "directed_edges": self.edge_count,
            "average_out_degree": self.edge_count / self.vertex_count if self.vertex_count else 0.0,
            "maximum_out_degree": max(out_degrees, default=0),
            "average_total_degree": sum(total_degrees) / self.vertex_count if self.vertex_count else 0.0,
            "maximum_total_degree": max(total_degrees, default=0),
        }

    def bfs_induced_subgraph(self, target_size: int, seed: int = 1) -> "RoadGraph":
        """Return a connected, BFS-prefix induced subgraph of at most target_size.

        Selected vertices are densely renumbered for honest size-dependent memory
        and timing measurements. ``original_vertex_ids`` preserves provenance.
        """

        self.validate_vertex(seed)
        if target_size <= 0:
            raise ValueError("target_size must be positive")
        target_size = min(target_size, self.vertex_count)
        seen = bytearray(self.vertex_count + 1)
        queue = [seed]
        seen[seed] = 1
        head = 0
        while head < len(queue) and len(queue) < target_size:
            u = queue[head]
            head += 1
            for edge in self.adjacency[u]:
                if not seen[edge.to]:
                    seen[edge.to] = 1
                    queue.append(edge.to)
                    if len(queue) == target_size:
                        break
        new_id = {old_id: index for index, old_id in enumerate(queue, 1)}
        adjacency = [[] for _ in range(len(queue) + 1)]
        coords = [None] * (len(queue) + 1)
        for old_u in queue:
            u = new_id[old_u]
            adjacency[u] = [Edge(new_id[edge.to], edge.weight) for edge in self.adjacency[old_u] if edge.to in new_id]
            coords[u] = self.coordinates[old_u]
        subgraph = RoadGraph(adjacency, coords, f"{self.name}-{len(queue)}")
        subgraph.active_vertices = tuple(range(1, len(queue) + 1))
        subgraph.original_vertex_ids = [0, *queue]
        return subgraph

    def safe_geo_scale(self) -> float:
        """Largest globally safe multiplier for a great-circle A* heuristic.

        For each usable edge we require ``scale * geo(u,v) <= weight(u,v)``.
        Combined with the triangle inequality this makes the heuristic consistent.
        """

        scale = 1.0
        found = False
        for u in self.vertices():
            cu = self.coordinates[u]
            if cu is None:
                continue
            for edge in self.adjacency[u]:
                cv = self.coordinates[edge.to]
                if cv is None:
                    continue
                straight = projected_distance_m(cu, cv, self._projection_cosine)
                if straight > 0:
                    scale = min(scale, edge.weight / straight)
                    found = True
        return max(0.0, min(1.0, scale)) if found else 0.0

    def geo_heuristic(self, destination: int, scale: float | None = None) -> Callable[[int], float]:
        self.validate_vertex(destination)
        goal = self.coordinates[destination]
        multiplier = self.safe_geo_scale() if scale is None else scale
        projection_cosine = self._projection_cosine
        if goal is None or multiplier <= 0:
            return lambda _vertex: 0.0

        def estimate(vertex: int) -> float:
            point = self.coordinates[vertex]
            return 0.0 if point is None else multiplier * projected_distance_m(point, goal, projection_cosine)

        return estimate


def haversine_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Great-circle distance in metres for ``(longitude, latitude)`` pairs."""

    lon1, lat1 = map(radians, a)
    lon2, lat2 = map(radians, b)
    dlon, dlat = lon2 - lon1, lat2 - lat1
    h = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 2 * 6_371_008.8 * asin(min(1.0, sqrt(h)))


def projected_distance_m(a: tuple[float, float], b: tuple[float, float], cosine_latitude: float) -> float:
    """Euclidean distance in a fixed local equirectangular projection.

    A fixed linear projection preserves the triangle inequality and is much
    cheaper to evaluate inside A* than trigonometric great-circle distance.
    ``safe_geo_scale`` calibrates it against every road arc.
    """

    metres_per_degree = 111_195.08
    return metres_per_degree * hypot((a[0] - b[0]) * cosine_latitude, a[1] - b[1])

