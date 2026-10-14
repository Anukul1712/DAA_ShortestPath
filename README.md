# Shortest-Path Planning on a Large-Scale Mobility Network - Complete Solution

This repository is a complete, reproducible solution to the problem statement in [PS_README.md](PS_README.md). It parses a real 264,346-vertex road network, constructs an adjacency list, implements Dijkstra and A* without graph-library shortest-path calls, benchmarks five graph sizes and five queries per size, reconstructs paths, handles unreachable destinations, generates plots, and completes the dynamic-edge-cost bonus.

## Headline findings

- Dataset: **9th DIMACS Implementation Challenge, USA-road-d.NY** (New York road network).
- Full graph: **264,346 vertices** and **733,846 directed arcs**.
- Representation: directed weighted adjacency list; native weights use 0.1-meter distance units.
- Correctness: Dijkstra and A* returned the **same optimal cost in all 25 measured queries**.
- Search work: A* examined 44.04%-77.73% fewer vertices across the tested sizes.
- Runtime: A* was faster at every tested size after its heuristic was calibrated in the dataset's native distance units.
- Bonus: applying 5x cost to 124 arcs in the middle third of a route changed the route; cost rose from **47,023.1 m to 47,747.8 m (+1.54%)**.

## Repository map

```text
.
|-- PS_README.md                     original problem statement
|-- README.md                        this report and complete Q&A
|-- requirements.txt                plotting dependency
|-- data/
|   |-- README.md                   dataset source, schema, hashes, citation
|   `-- raw/                        downloaded DIMACS archives (git-ignored)
|-- docs/
|   |-- PREPROCESSING.md            graph-construction procedure
|   `-- REPORT.md                   concise submission report
|-- scripts/
|   |-- download_data.py            official-data downloader + SHA-256 output
|   `-- run_all.py                  one-command experiment pipeline
|-- src/shortest_path/
|   |-- graph.py                    adjacency list, statistics, subgraphs, heuristic
|   |-- dimacs.py                   streaming .gr/.co/.gz parser
|   |-- algorithms.py               Dijkstra, A*, metrics, path reconstruction
|   |-- experiments.py              sampling, benchmarks, CSV/JSON, bonus
|   |-- visualization.py            four result plots
|   `-- cli.py                      query/stats/benchmark/dynamic CLI
|-- tests/                           parser, correctness, and edge-case tests
`-- results/
    |-- tables/                      raw, summary, statistics, metadata
    |-- plots/                       all PNG figures
    `-- bonus/                       dynamic-cost JSON output
```

## 1. Reproduce everything

Python 3.10+ is recommended. The algorithms and parser use only the standard library; Matplotlib is required only for plots.

### Windows PowerShell

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python scripts/download_data.py
python scripts/run_all.py
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -v
```

### Linux/macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/download_data.py
python scripts/run_all.py
PYTHONPATH=src python -m unittest discover -s tests -v
```

Optional: `python -m pip install -e .` installs the package in editable mode and exposes the `shortest-path` console command, removing the need to set `PYTHONPATH`.

Expected final pipeline message:

```text
Wrote 50 raw rows, 10 summary rows, and 4 plots under .../results
```

The data downloader is idempotent and prints hashes. The files used for this report were:

| File | Compressed bytes | SHA-256 |
|---|---:|---|
| `USA-road-d.NY.gr.gz` | 3,667,907 | `7b2446c7ffe6179efbc42af6812448e8cb782f12968ca2bb1d50d979343056d4` |
| `USA-road-d.NY.co.gz` | 2,058,598 | `02547a628742164e02bd73f59e33a65d23dfac8fc54c09275c8b9169c38eafdf` |

## 2. Dataset selection (Part A)

| Required item | Answer |
|---|---|
| Dataset name | 9th DIMACS Implementation Challenge - `USA-road-d.NY` |
| Source | [Official Challenge download page](https://www.diag.uniroma1.it/challenge9/download.shtml) |
| Provenance | US road network derived from the TIGER/Line collection |
| Scenario | Vehicular/IoV point-to-point routing in New York |
| Full records | 733,846 arc records plus 264,346 coordinate records |
| Vertices | 264,346 road-network locations/intersections |
| Directed edges | 733,846 feasible directed road movements |
| Edge weight | Integer spatial distance; one stored unit is 0.1 meter |
| Coordinates | Longitude and latitude stored as signed integers with six implied decimal places |
| Public status | The challenge download page states that files are public domain unless noted otherwise |

The [official DIMACS format specification](https://www.diag.uniroma1.it/challenge9/format.shtml) defines the graph and coordinate records. The [TIGER/Line documentation](https://www.diag.uniroma1.it/challenge9/data/tiger/) identifies the metric as spatial endpoint distance. The downloaded graph uses integer decimeter resolution: for example, `W=803` represents 80.3 meters. The official page also warns that the historical dataset has road-data errors, including some gaps in major roads and bridges; results are algorithmically valid for the supplied graph but are not a modern navigation service.

### How to read the DIMACS records

The graph file contains:

| Record | Field-by-field meaning | Project action |
|---|---|---|
| `c ...` | `c` means comment | Ignore it |
| `p sp n m` | `p` = problem, `sp` = shortest path, `n` = vertices, `m` = directed arcs | Allocate `n+1` adjacency lists and verify `m` arcs |
| `a U V W` | `a` = arc, `U` = source, `V` = destination, `W` = non-negative native distance | Append `Edge(V,W)` to `adjacency[U]` |

The coordinate file contains:

| Record | Field-by-field meaning | Project action |
|---|---|---|
| `p aux sp co n` | auxiliary shortest-path coordinate file with `n` coordinate rows | Validate the coordinate-file declaration |
| `v ID X Y` | coordinate for vertex `ID`; `X` = longitude and `Y` = latitude with six implied decimals | Store `(X/1e6, Y/1e6)` |

Actual examples:

```text
p sp 264346 733846
a 1 2 803
p aux sp co 264346
v 1 -73530767 41085396
```

These records mean that the graph has 264,346 vertices and 733,846 directed arcs; it contains an arc `1 -> 2` with cost 803 native units (80.3 meters); and vertex 1 is located at longitude -73.530767, latitude 41.085396.

An `a U V W` record is directional. A reverse movement exists only if a separate `a V U W2` record is present. Complete file semantics, field explanations, real examples, unit discussion, limitations, and detailed answers to all nine Part A questions are provided in [data/README.md](data/README.md).

Why New York rather than the entire USA graph?

- It is real, sparse, weighted, directed, geographic, and far larger than the required 50,000-vertex experiment.
- It supports a meaningful coordinate heuristic.
- At roughly 5.7 MB compressed for graph plus coordinates, every evaluator can reproduce the work on a laptop.
- The full-USA instance (23,947,347 vertices and 58,333,344 arcs) would add hardware and download constraints without improving the assignment's algorithm comparison.

## 3. Graph construction (Part B)

### Input mapping

```text
p sp 264346 733846     -> allocate adjacency[0..264346]
a U V W                -> adjacency[U].append(Edge(to=V, weight=W))
v ID X Y               -> coordinates[ID] = (X/1e6, Y/1e6)
```

Comments are skipped. The downloader provides compressed and extracted files; the parser accepts either form. IDs stay 1-based, matching the dataset and making path output directly traceable to raw records. The parser verifies the declared arc count and rejects invalid lines or negative weights. Native integer distances are preserved for exact arithmetic, while generated output also reports `cost_meters = cost * 0.1`.

### Full-graph statistics

| Statistic | Value |
|---|---:|
| Vertices | 264,346 |
| Directed arcs | 733,846 |
| Average out-degree | 2.7761 |
| Maximum out-degree | 8 |
| Average total degree (in + out) | 5.5522 |
| Maximum total degree | 16 |

The assignment's "average degree" can be ambiguous for a directed graph. This project reports both average out-degree, `E/V`, and average total degree, `2E/V`. Experiments use average out-degree because the algorithms scan outgoing adjacency lists.

### Experiment subgraphs

The experiment uses nested BFS-prefix induced subgraphs. Beginning at vertex 1, outgoing BFS discovers vertices; the first `N` are retained, and only arcs whose two endpoints are retained remain. Selected vertices are densely renumbered internally so arrays and timings truly scale with `N`; an `original_vertex_ids` map converts every reported source, destination, and path back to official DIMACS IDs. This provides exact requested sizes, locality, connectivity from the seed, and identical raw-data provenance at every scale.

| Vertices | Directed arcs | Average out-degree | Maximum out-degree |
|---:|---:|---:|---:|
| 1,000 | 2,438 | 2.4380 | 4 |
| 5,000 | 12,126 | 2.4252 | 6 |
| 10,000 | 23,954 | 2.3954 | 6 |
| 25,000 | 62,164 | 2.4866 | 6 |
| 50,000 | 130,522 | 2.6104 | 7 |

## 4. Algorithms (Parts C and D)

### Dijkstra with a binary min-heap

```text
distance[S] = 0; push (0,S)
while heap is not empty:
    pop the unsettled vertex u with smallest distance
    stop if u == D
    for every outgoing edge (u,v,w):
        if distance[u] + w < distance[v]:
            update distance[v], parent[v], and push v
reconstruct D -> S through parent[], then reverse
```

The heap uses lazy deletion: improved entries are pushed, and stale entries are ignored on pop. With an adjacency list and binary heap, time is `O((V+E) log V)`, commonly written `O(E log V)` for a connected sparse graph. Space is `O(V+E)` for the graph plus `O(V)` search arrays and heap entries.

### A*

A* uses the same relaxation and parent reconstruction, but orders the heap by

```text
f(v) = g(v) + h(v)
```

where `g(v)` is the best known source cost and `h(v)` is straight-line distance to the target in a fixed local equirectangular projection.

#### Why the heuristic is admissible and consistent

The projection is fixed for the graph, so its Euclidean distances obey the triangle inequality. The implementation computes

```text
scale = min over arcs (u,v) of native_weight(u,v) / projected_distance_meters(u,v)
h(v) = scale * projected_distance(v, destination)
```

The scale converts geometric meters into the graph's native 0.1-meter cost units while remaining no larger than any observed edge-cost-to-projected-distance ratio. Therefore, for every arc `(u,v)`, `h(u) <= w(u,v) + h(v)` by the triangle inequality and the per-edge scale bound. The heuristic is consistent; consistency implies admissibility. Measured safe scales ranged from 8.7218 to 9.9610 native units per projected meter across the five samples. A zero heuristic remains a correct fallback when coordinates are absent.

A* has worst-case `O((V+E) log V)` time and `O(V+E)` total storage, but an informative heuristic can reduce the explored subset substantially.

### Metric definitions

- **Native shortest-path cost:** exact sum of integer weights, where one unit is 0.1 meter.
- **Shortest-path distance:** native cost multiplied by 0.1, reported in meters.
- **Vertices explored:** vertices removed from the priority queue and settled/expanded.
- **Edges examined:** outgoing arcs scanned from expanded vertices.
- **Execution time:** wall-clock time inside the search, measured with `perf_counter_ns`.
- **Path:** explicit sequence obtained from the `parent` array.
- **Unreachable pair:** `reachable=false`, empty path, and infinite cost.

## 5. Experimental design (Part E)

- Sizes: 1,000; 5,000; 10,000; 25,000; 50,000 vertices.
- Queries: five distinct reachable pairs per size.
- Pair design: vertices near the beginning of BFS order are paired with vertices near the end. This avoids trivial nearby trips and makes scaling meaningful.
- Seed: `2026`; stored in `metadata.json`.
- Repetitions: each algorithm/query is run five times; the per-query median is recorded to reduce scheduler/GC noise.
- Correctness oracle: every query asserts `Dijkstra cost == A* cost` before results are written.
- Total reported rows: 5 sizes x 5 pairs x 2 algorithms = 50.
- Raw results include the complete path for every run in [`raw_results.csv`](results/tables/raw_results.csv).

Exact machine-dependent times will vary. Operation counts and optimal costs are deterministic for the supplied data and seed.

## 6. Results

### Mean of five queries at every size

| Graph size | Algorithm | Mean native cost | Mean distance (m) | Mean vertices explored | Mean edges examined | Mean time (ms) |
|---:|---|---:|---:|---:|---:|---:|
| 1,000 | Dijkstra | 34,416.4 | 3,441.64 | 764.4 | 1,924.8 | 0.525 |
| 1,000 | A* | 34,416.4 | 3,441.64 | 170.2 | 445.0 | 0.183 |
| 5,000 | Dijkstra | 138,648.8 | 13,864.88 | 4,531.0 | 11,086.6 | 3.709 |
| 5,000 | A* | 138,648.8 | 13,864.88 | 1,257.2 | 3,132.6 | 1.443 |
| 10,000 | Dijkstra | 241,135.6 | 24,113.56 | 8,626.8 | 20,814.4 | 6.462 |
| 10,000 | A* | 241,135.6 | 24,113.56 | 4,297.2 | 10,630.0 | 4.865 |
| 25,000 | Dijkstra | 316,543.2 | 31,654.32 | 20,878.8 | 52,167.4 | 29.842 |
| 25,000 | A* | 316,543.2 | 31,654.32 | 8,962.4 | 22,695.0 | 29.613 |
| 50,000 | Dijkstra | 482,078.2 | 48,207.82 | 46,075.8 | 120,559.8 | 103.634 |
| 50,000 | A* | 482,078.2 | 48,207.82 | 25,784.2 | 67,842.6 | 81.859 |

Full precision is preserved in [`summary_results.csv`](results/tables/summary_results.csv), and individual queries are in [`raw_results.csv`](results/tables/raw_results.csv).

### Search-space reductions from A*

| Graph size | Fewer vertices | Fewer edges | Faster runtime |
|---:|---:|---:|---:|
| 1,000 | 77.73% | 76.88% | 65.03% |
| 5,000 | 72.25% | 71.74% | 61.08% |
| 10,000 | 50.19% | 48.93% | 24.71% |
| 25,000 | 57.07% | 56.50% | 0.77% |
| 50,000 | 44.04% | 43.73% | 21.01% |

With the heuristic expressed in the same native cost units as `g(v)`, A* substantially reduces the search space. It was faster at all sizes, although the 25,000-vertex mean was nearly tied because heuristic calculations have their own cost. The operation-count reductions are more portable than wall-clock timings and clearly show the benefit of destination guidance.

### Plots

![Runtime comparison](results/plots/runtime_comparison.png)

![Vertices explored](results/plots/vertices_explored.png)

![Edges examined](results/plots/edges_examined.png)

## 7. Bonus: dynamic edge costs

The experiment models congestion with

```text
w'(u,v) = alpha * d(u,v) + beta * c(u,v)
alpha = 1, beta = 1
c(u,v) = 4 * d(u,v) for selected congested arcs, otherwise 0
```

Thus selected arcs cost `5d`, while unaffected arcs remain at `d`. The middle third of the original 50,000-vertex route is marked congested, then shortest path is recomputed from scratch.

| Bonus metric | Result |
|---|---:|
| Source -> destination | 2,069 -> 13,771 |
| Congested original-route arcs | 124 |
| Original native cost | 470,231 units |
| New native cost | 477,478 units |
| Original distance | 47,023.1 m |
| New distance | 47,747.8 m |
| Distance increase | 724.7 m (1.54%) |
| Original path length | 373 vertices |
| New path length | 388 vertices |
| Route changed | Yes |
| Shared directed path edges | 168 |

![Dynamic route comparison](results/plots/dynamic_route_comparison.png)

The new route deliberately accepts a slightly larger uncongested distance to avoid the heavily penalized central segment. The exact paths and parameters are in [`dynamic_result.json`](results/bonus/dynamic_result.json).

## 8. Answers to the ten assignment questions (Part F)

### Q1. Why is this dataset suitable?

It is a public, real road network with positive physical-distance weights, directionality, coordinates, and 264,346 vertices - large enough for realistic sparse-graph behavior and every requested experiment size. Vertices, arcs, and weights map directly to IoV routing.

### Q2. How was it transformed into a weighted graph?

Each `a U V W` record becomes an `Edge(V,W)` in `adjacency[U]`. Each `v ID X Y` record becomes decimal longitude/latitude. Comments and unused metadata are discarded; original IDs, direction, and native integer distance weights are preserved. One native weight unit is 0.1 meter.

### Q3. Do Dijkstra and A* produce the same cost?

Yes, on all 25 queries. Both optimize the same non-negative weights. Dijkstra is optimal by settled-distance order. A* is optimal because its heuristic is consistent/admissible. The pipeline asserts equality and aborts on any mismatch.

### Q4. Which explores fewer vertices, and why?

A* explored fewer at all sizes. Dijkstra orders only by distance already travelled, so it expands broadly around the source. A* adds a lower bound to the goal and preferentially expands promising directions.

### Q5. How does time vary with graph size?

Mean time increased with size and query span: Dijkstra rose from 0.525 ms at 1,000 vertices to 103.634 ms at 50,000; A* rose from 0.183 ms to 81.859 ms. Growth is not determined by `V` alone: endpoint position, explored region, degree, heap duplicates, OS scheduling, and cache behavior also matter.

### Q6. What is the effect of graph density?

More outgoing arcs cause more relaxations per expanded vertex. With adjacency lists and a heap, cost is `O((V+E) log V)`, so increasing `E` directly raises scan work and may increase heap updates. This road network is sparse (full-graph average out-degree 2.776), which strongly favors adjacency lists over an `O(V^2)` matrix.

### Q7. What is Dijkstra's theoretical complexity?

With a binary heap and adjacency list: `O((V+E) log V)` time and `O(V+E)` total storage including the graph. The auxiliary search state is `O(V)` plus heap entries. On a connected sparse graph, the time is usually stated as `O(E log V)`.

### Q8. Which A* heuristic is used; is it admissible/consistent?

A fixed equirectangular projection estimates straight-line distance, multiplied by a global scale no greater than `weight(u,v)/projected_distance(u,v)` for every arc. The projection's Euclidean metric obeys the triangle inequality, and calibration makes the edge consistency condition hold. It is therefore consistent and admissible. Missing coordinates fall back to zero.

### Q9. What conversion difficulties arose?

The graph is directed, IDs are 1-based, files are compressed, coordinates use implied six-decimal precision, the declared edge count must be validated, and induced samples can create unreachable directed pairs. The implementation streams gzip, preserves IDs, validates counts/weights, retains only induced edges, tests reachability, and records historical-data limitations.

### Q10. Which algorithm is recommended for large-scale IoV/UAV planning?

For this point-to-point distance-routing workload, A* is recommended because it returned the same optimal costs while exploring 44.04%-77.73% fewer vertices and running faster at every tested size. Dijkstra remains the essential correctness baseline and a robust choice when coordinates or a safe heuristic are unavailable. Production systems should still benchmark on their own hardware and query distribution.


## 9. Testing and verification evidence

The test suite covers:

- known optimal cost and exact path;
- A*/Dijkstra agreement;
- disconnected destinations;
- source equals destination;
- compressed DIMACS graph and coordinate parsing.

Last local result:

```text
Ran 7 tests ... OK
```

The real-data pipeline adds 25 cross-algorithm cost assertions. The final generated artifacts are:

| Artifact | Purpose |
|---|---|
| [`graph_statistics.csv`](results/tables/graph_statistics.csv) | graph-size/edge/degree table |
| [`raw_results.csv`](results/tables/raw_results.csv) | all queries, metrics, and complete paths |
| [`summary_results.csv`](results/tables/summary_results.csv) | mean/median comparison table |
| [`metadata.json`](results/tables/metadata.json) | seed, sizes, query count, repetitions |
| [`dynamic_result.json`](results/bonus/dynamic_result.json) | bonus parameters and both complete routes |
| [`runtime_comparison.png`](results/plots/runtime_comparison.png) | timing plot |
| [`vertices_explored.png`](results/plots/vertices_explored.png) | vertex-work plot |
| [`edges_examined.png`](results/plots/edges_examined.png) | edge-work plot |
| [`dynamic_route_comparison.png`](results/plots/dynamic_route_comparison.png) | geographic bonus-route plot |

## 10. Useful CLI commands

After setting `PYTHONPATH=src` (or `$env:PYTHONPATH="src"` in PowerShell):

```bash
# Full graph statistics
python -m shortest_path.cli --graph data/raw/USA-road-d.NY.gr.gz --coordinates data/raw/USA-road-d.NY.co.gz stats

# One A* query with complete path and metrics
python -m shortest_path.cli --graph data/raw/USA-road-d.NY.gr.gz --coordinates data/raw/USA-road-d.NY.co.gz query 2069 13771 --algorithm astar

# Custom benchmark
python -m shortest_path.cli --graph data/raw/USA-road-d.NY.gr.gz --coordinates data/raw/USA-road-d.NY.co.gz benchmark --sizes 1000 5000 10000 --pairs 5 --repetitions 5

# Custom dynamic-cost experiment
python -m shortest_path.cli --graph data/raw/USA-road-d.NY.gr.gz --coordinates data/raw/USA-road-d.NY.co.gz dynamic 2069 13771
```

## 11. Final conclusion

The project demonstrates more than calling a shortest-path routine: it selects and verifies a public mobility dataset, parses a documented interchange format, models direction and weights explicitly, implements and instruments two algorithms, designs reproducible nested-scale experiments, validates optimality, exposes raw paths/results, visualizes scaling, and shows rerouting under dynamic costs.

The central empirical lesson is that unit-aware modelling matters. Once the geometric heuristic is calibrated to the dataset's native 0.1-meter weights, A* remains admissible, explores far less of the graph, and improves point-to-point runtime while producing exactly the same optimal cost as Dijkstra.

