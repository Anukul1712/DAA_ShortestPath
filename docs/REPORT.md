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

## Bonus result

The middle 124 arcs of one original route received a 5x simulated congestion cost. Recalculation changed the route from 373 to 388 vertices and increased distance from 47,023.1 m to 47,747.8 m (+1.54%). The alternative route avoids most of the penalized segment, demonstrating adaptive mobility routing.

## Limitations

The historical road data contains documented map errors. The experiment uses one city, distance weights, five queries per size, and one Python implementation. Operation counts are more portable than elapsed times. A larger research study should add more cities, more queries, confidence intervals, memory profiling, and optimized implementations.

