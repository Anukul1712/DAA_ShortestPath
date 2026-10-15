# Short Report: Large-Scale Mobility Shortest Paths

This document satisfies submission criterion 7. The fully detailed report, setup instructions, tables, plots, analysis, and extended viva questions are in [`../README.md`](../README.md).

## Objective

The project evaluates independently implemented Dijkstra and A* algorithms on a realistic vehicular mobility graph and studies their correctness, search effort, execution time, scaling, and response to dynamic edge costs.

## Dataset and model

The selected dataset is the public 9th DIMACS Implementation Challenge New York distance graph. It contains 264,346 road-network vertices and 733,846 directed arcs. Native integer arc weights have 0.1-meter resolution. Longitude/latitude coordinates support a destination-aware heuristic.

The compressed DIMACS files are streamed into a directed adjacency list. Five nested BFS-prefix induced graphs contain 1,000, 5,000, 10,000, 25,000, and 50,000 vertices. Dense internal IDs make resource use match the sample size, while a reverse map ensures every published path uses official dataset IDs.

## Algorithms

Dijkstra uses a binary min-heap with lazy stale-entry deletion. A* uses the same relaxation logic and orders vertices by `g(v)+h(v)`. Its heuristic is fixed-projection straight-line distance calibrated against every graph arc. The calibration plus the projection's triangle inequality makes the heuristic consistent and admissible.

Both algorithms explicitly maintain parent arrays and reconstruct complete paths. Disconnected pairs return an empty path and infinite cost.

## Experiment

Five reachable, non-trivial source-destination pairs are tested at every graph size. Each algorithm/query timing is repeated five times and the median is recorded. Results include cost, full path, vertices explored, edges examined, and elapsed time. The pipeline aborts if the two algorithms disagree on optimal cost.

## Main findings

- Dijkstra and A* agreed on all 25 optimal costs.
- A* examined 44.04%-77.73% fewer vertices, depending on size.
- A* was faster at every tested size after the heuristic was calibrated to native cost units.
- Execution time and examined edges increased substantially with graph and query span.
- Sparse road-network structure strongly favors adjacency lists.

The practical conclusion is that A* is preferable for these coordinate-equipped point-to-point queries. Dijkstra remains the correctness baseline and fallback when a safe heuristic is unavailable.

## Heuristic parameter study

An additional experiment evaluates `f(v)=g(v)+lambda*h(v)` at eight weights from 0 through 2 on the same 25 queries. Values through 1 preserve the admissibility/consistency guarantee; values above 1 are weighted A* and may return approximate routes.

- Search work decreased monotonically from `lambda=0` to standard A* at `lambda=1` for every graph size.
- Standard A* used 39.74% of zero-heuristic vertices and 60.77% of zero-heuristic runtime on average across sizes, while remaining optimal on 25/25 queries.
- Weighted `lambda=1.25` used only 22.29% of zero-heuristic vertices, but only 13/25 routes remained optimal and the largest cost gap was 3.689%.
- More aggressive values were not monotonically better. `lambda=1.5` caused substantial reopen work on the 50,000-vertex graph and produced a maximum cost gap of 10.876%.

The study establishes why `lambda=1` is the preferred configuration: it is the strongest tested setting that combines proven exactness with substantial goal-directed pruning. Weighted A* should be used only when approximate routes are acceptable.

## Bonus result

The middle 124 arcs of one original route received a simulated congestion cost. A 24-scenario study varied `alpha` over 0.5, 1, and 2 and `beta` over eight values from 0 through 2, producing four distinct optimal routes. It confirms that route selection depends on `beta/alpha`: equivalent ratios return the same path. With `alpha=1, beta=1`, staying on the original route would raise its objective from 47,023.1 m to 106,790.7 m-equivalent. Recalculation increased physical distance to 47,747.8 m (+1.54%), avoided all 124 penalized arcs, and reduced dynamic cost by 55.29% versus staying. The main README provides both complete bonus tables and six explained bonus figures.

## Limitations

The historical road data contains documented map errors. The experiment uses one city, distance weights, five queries per size, and one Python implementation. Operation counts are more portable than elapsed times. A larger research study should add more cities, more queries, confidence intervals, memory profiling, and optimized implementations.

