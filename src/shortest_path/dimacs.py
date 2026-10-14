"""Streaming readers for 9th DIMACS Challenge graph and coordinate files."""

from __future__ import annotations

import gzip
from pathlib import Path
from typing import TextIO

from .graph import Edge, RoadGraph


def _open_text(path: str | Path) -> TextIO:
    path = Path(path)
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="ascii", errors="strict")
    return path.open("rt", encoding="ascii", errors="strict")


def read_dimacs_graph(graph_path: str | Path, coordinate_path: str | Path | None = None) -> RoadGraph:
    """Load a DIMACS ``.gr`` file and optional ``.co`` file.

    Lines beginning with ``c`` are comments, ``p sp n m`` declares dimensions,
    ``a u v w`` is a directed arc, and ``v id lon lat`` gives coordinates in
    millionths of a degree.
    """

    adjacency: list[list[Edge]] | None = None
    expected_edges: int | None = None
    parsed_edges = 0
    with _open_text(graph_path) as stream:
        for line_no, line in enumerate(stream, 1):
            if not line or line[0] in {"c", "\n"}:
                continue
            fields = line.split()
            if fields[0] == "p":
                if len(fields) != 4 or fields[1] != "sp":
                    raise ValueError(f"invalid problem line at {line_no}: {line.rstrip()}")
                vertices, expected_edges = int(fields[2]), int(fields[3])
                adjacency = [[] for _ in range(vertices + 1)]
            elif fields[0] == "a":
                if adjacency is None or len(fields) != 4:
                    raise ValueError(f"invalid arc line at {line_no}: {line.rstrip()}")
                u, v, weight = map(int, fields[1:])
                if weight < 0:
                    raise ValueError(f"negative weight at line {line_no}")
                adjacency[u].append(Edge(v, weight))
                parsed_edges += 1
    if adjacency is None:
        raise ValueError("DIMACS graph has no 'p sp' problem line")
    if expected_edges != parsed_edges:
        raise ValueError(f"expected {expected_edges} arcs but parsed {parsed_edges}")

    coordinates: list[tuple[float, float] | None] = [None] * len(adjacency)
    if coordinate_path:
        with _open_text(coordinate_path) as stream:
            for line_no, line in enumerate(stream, 1):
                if not line or line[0] in {"c", "p", "\n"}:
                    continue
                fields = line.split()
                if fields[0] != "v" or len(fields) != 4:
                    raise ValueError(f"invalid coordinate line at {line_no}: {line.rstrip()}")
                vertex, lon, lat = map(int, fields[1:])
                coordinates[vertex] = (lon / 1_000_000.0, lat / 1_000_000.0)
    return RoadGraph(adjacency, coordinates, Path(graph_path).stem.replace(".gr", ""))

