# Preprocessing and Graph Construction

This document satisfies submission criterion 3: **preprocessing details**.

## Pipeline

```text
Official .gr.gz + .co.gz files
              |
              v
Streaming DIMACS parser
              |
              v
Directed weighted adjacency list + coordinates
              |
              v
BFS-prefix induced samples
1k / 5k / 10k / 25k / 50k vertices
              |
              v
Dijkstra, A*, and dynamic-cost experiments
```

## Parsing

The parser is implemented in `src/shortest_path/dimacs.py`.

1. Open `.gz` inputs in streaming text mode; no extracted copy is created.
2. Ignore DIMACS comment lines beginning with `c`.
3. Read `p sp n m` and allocate a 1-based adjacency list.
4. Convert each `a U V W` record to `adjacency[U].append(Edge(V, W))`.
5. Reject negative weights because Dijkstra and A* require non-negative costs.
6. Check that the parsed arc count equals the declared value.
7. Convert coordinate integers to decimal degrees with division by `1,000,000`.

Unneeded metadata is not retained.

## Experimental graph sizes

The full network is not truncated by raw file order. Starting from vertex 1, outgoing BFS constructs a locality-preserving discovery order. For each requested size `N`:

1. retain the first `N` discovered vertices;
2. retain only arcs whose source and destination are both selected;
3. densely renumber the selected vertices from 1 to `N` for honest memory/timing scaling;
4. preserve a reverse map to the official DIMACS IDs;
5. report all sources, destinations, and complete paths using official IDs.

This produces nested, reproducible, geographically coherent induced subgraphs without inventing edges or weights.

## Query selection

Five distinct reachable pairs are used at every size. Vertices near the start of BFS discovery are paired with vertices near the end so benchmarks are not dominated by trivial local trips. A fixed-seed fallback handles unusual directed reachability cases.

## Validation

- Dijkstra and A* costs are asserted equal for every query.
- Every reported path begins at its source and ends at its destination.
- Parser and algorithm edge cases are covered by `tests/`.
- Dataset hashes are recorded in `data/README.md`.

