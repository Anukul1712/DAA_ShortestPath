# Shortest-Path Planning on a Large-Scale Mobility Network - Complete Solution

This repository is a complete, reproducible solution to the problem statement in [PS_README.md](PS_README.md). It parses a real 264,346-vertex road network, constructs an adjacency list, implements Dijkstra and A* without graph-library shortest-path calls, benchmarks five graph sizes and five queries per size, reconstructs paths, handles unreachable destinations, generates plots, and completes the dynamic-edge-cost bonus.

## Headline findings

- Dataset: **9th DIMACS Implementation Challenge, USA-road-d.NY** (New York road network).
- Full graph: **264,346 vertices** and **733,846 directed arcs**.
- Representation: directed weighted adjacency list; arc weights are physical distance in metres.
- Correctness: Dijkstra and A* returned the **same optimal cost in all 25 measured queries**.
- Search work: A* examined fewer vertices and edges at every tested size (3.18%-7.85% fewer vertices).
- Runtime: Dijkstra was faster in this Python implementation because the conservative geometric heuristic saved relatively few expansions but added floating-point work to each queue insertion.
- Bonus: applying 5x cost to 124 arcs in the middle third of a route changed the route; cost rose from **470,231 m to 477,478 m (+1.54%)**.

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
| Edge weight | Physical endpoint-to-endpoint distance in metres |
| Coordinates | Longitude and latitude stored as signed integers with six implied decimal places |
| Public status | The challenge download page states that files are public domain unless noted otherwise |

The [official DIMACS format specification](https://www.diag.uniroma1.it/challenge9/format.shtml) defines `p sp n m`, `a U V W`, and `v id X Y`. The [TIGER/Line conversion documentation](https://www.diag.uniroma1.it/challenge9/data/tiger/) states that the distance variant stores spatial distance in metres. The official page also warns that the historical dataset has road-data errors, including some gaps in major roads and bridges; results are algorithmically valid for the supplied graph but are not a modern navigation service.

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

Comments are skipped. Files remain gzip-compressed and are streamed as text, so no manual decompression or duplicate raw file is needed. IDs stay 1-based, matching the dataset and making path output directly traceable to raw records. The parser verifies the declared arc count and rejects invalid lines or negative weights.

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
scale = min(1, min over arcs (u,v) of weight(u,v) / projected_distance(u,v))
h(v) = scale * projected_distance(v, destination)
```

Therefore, for every arc `(u,v)`, `h(u) <= w(u,v) + h(v)` by the triangle inequality and the per-edge scale bound. The heuristic is consistent; consistency implies admissibility. The measured scale was `1.0` at all five sizes. A zero heuristic remains a correct fallback when coordinates are absent.

A* has worst-case `O((V+E) log V)` time and `O(V+E)` total storage, but an informative heuristic can reduce the explored subset substantially.

### Metric definitions

- **Shortest-path cost:** sum of weights on the reconstructed path, in metres.
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

| Graph size | Algorithm | Mean cost (m) | Mean vertices explored | Mean edges examined | Mean time (ms) |
|---:|---|---:|---:|---:|---:|
| 1,000 | Dijkstra | 34,416.4 | 764.4 | 1,924.8 | 0.445 |
| 1,000 | A* | 34,416.4 | 704.4 | 1,784.4 | 0.594 |
| 5,000 | Dijkstra | 138,648.8 | 4,531.0 | 11,086.6 | 2.797 |
| 5,000 | A* | 138,648.8 | 4,333.2 | 10,627.2 | 4.021 |
| 10,000 | Dijkstra | 241,135.6 | 8,626.8 | 20,814.4 | 6.325 |
| 10,000 | A* | 241,135.6 | 8,283.6 | 20,014.0 | 8.886 |
| 25,000 | Dijkstra | 316,543.2 | 20,878.8 | 52,167.4 | 27.587 |
| 25,000 | A* | 316,543.2 | 19,638.0 | 49,158.0 | 48.398 |
| 50,000 | Dijkstra | 482,078.2 | 46,075.8 | 120,559.8 | 107.668 |
| 50,000 | A* | 482,078.2 | 44,526.4 | 116,729.0 | 130.883 |

Full precision is preserved in [`summary_results.csv`](results/tables/summary_results.csv), and individual queries are in [`raw_results.csv`](results/tables/raw_results.csv).

### Search-space reductions from A*

| Graph size | Fewer vertices | Fewer edges |
|---:|---:|---:|
| 1,000 | 7.85% | 7.29% |
| 5,000 | 4.37% | 4.14% |
| 10,000 | 3.98% | 3.85% |
| 25,000 | 5.94% | 5.77% |
| 50,000 | 3.36% | 3.18% |

The key result is nuanced: A* did less graph work but took longer here. A heap operation in Dijkstra is cheap Python integer/list work; each A* insertion also evaluates a coordinate heuristic and uses floating-point priorities. For these boundary-to-boundary queries, the safe geometric heuristic eliminates only a modest portion of the sparse road graph, so saved expansions do not repay heuristic overhead. In a lower-level implementation, with precomputed heuristics, a stronger landmark heuristic, expensive edge evaluation, or more local queries, the balance may change.

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
| Original cost | 470,231 m |
| New cost | 477,478 m |
| Cost increase | 7,247 m (1.54%) |
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

Each `a U V W` record becomes an `Edge(V,W)` in `adjacency[U]`. Each `v ID X Y` record becomes decimal longitude/latitude. Comments and unused metadata are discarded; original IDs, direction, and distance weights are preserved.

### Q3. Do Dijkstra and A* produce the same cost?

Yes, on all 25 queries. Both optimize the same non-negative weights. Dijkstra is optimal by settled-distance order. A* is optimal because its heuristic is consistent/admissible. The pipeline asserts equality and aborts on any mismatch.

### Q4. Which explores fewer vertices, and why?

A* explored fewer at all sizes. Dijkstra orders only by distance already travelled, so it expands broadly around the source. A* adds a lower bound to the goal and preferentially expands promising directions.

### Q5. How does time vary with graph size?

Mean time increased with size and query span: Dijkstra rose from 0.445 ms at 1,000 vertices to 107.668 ms at 50,000; A* rose from 0.594 ms to 130.883 ms. Growth is not determined by `V` alone: endpoint position, explored region, degree, heap duplicates, OS scheduling, and cache behavior also matter.

### Q6. What is the effect of graph density?

More outgoing arcs cause more relaxations per expanded vertex. With adjacency lists and a heap, cost is `O((V+E) log V)`, so increasing `E` directly raises scan work and may increase heap updates. This road network is sparse (full-graph average out-degree 2.776), which strongly favors adjacency lists over an `O(V^2)` matrix.

### Q7. What is Dijkstra's theoretical complexity?

With a binary heap and adjacency list: `O((V+E) log V)` time and `O(V+E)` total storage including the graph. The auxiliary search state is `O(V)` plus heap entries. On a connected sparse graph, the time is usually stated as `O(E log V)`.

### Q8. Which A* heuristic is used; is it admissible/consistent?

A fixed equirectangular projection estimates straight-line distance, multiplied by a global scale no greater than `weight(u,v)/projected_distance(u,v)` for every arc. The projection's Euclidean metric obeys the triangle inequality, and calibration makes the edge consistency condition hold. It is therefore consistent and admissible. Missing coordinates fall back to zero.

### Q9. What conversion difficulties arose?

The graph is directed, IDs are 1-based, files are compressed, coordinates use implied six-decimal precision, the declared edge count must be validated, and induced samples can create unreachable directed pairs. The implementation streams gzip, preserves IDs, validates counts/weights, retains only induced edges, tests reachability, and records historical-data limitations.

### Q10. Which algorithm is recommended for large-scale IoV/UAV planning?

For this exact pure-Python distance-routing workload, Dijkstra is the measured latency winner. For production point-to-point routing, A* is the better framework when a stronger inexpensive heuristic or preprocessing (for example ALT landmarks) is available, because it reduces search work and can exploit destination knowledge. Use Dijkstra as a robust baseline/fallback; use A* after verifying that heuristic savings exceed evaluation overhead on the target hardware and query distribution.

## 9. Additional viva, review, and defense questions

This section intentionally goes beyond the ten supplied questions.

### Dataset and modelling

**Why use a directed graph?** Roads can be one-way. Treating every arc as undirected could create illegal paths and different costs.

**What does one vertex represent?** A TIGER/Line road-network location/intersection with a geographic coordinate, not a vehicle.

**What does one edge represent?** A permitted movement along a road segment from its tail vertex to its head vertex.

**Why choose distance rather than travel time?** Distance is stable, directly documented in metres, and makes a geometric A* heuristic natural. The same parser works with the official `USA-road-t` time graph, but the heuristic would need a documented maximum-speed lower bound.

**Is this live traffic data?** No. It is a historical static road topology. The bonus simulates dynamic congestion; it does not claim to be live traffic.

**Why not use a manually drawn graph?** It would fail the scale and realism goals and hide parsing, sparsity, reachability, and measurement issues.

**Why are the raw archives ignored by Git?** They are reproducibly downloadable, externally owned data. Avoiding duplication keeps the repository small; hashes provide identity.

**Are parallel edges/self-loops allowed?** The DIMACS format permits them. The algorithms remain correct with non-negative parallel arcs and self-loops.

### Correctness and algorithms

**Why does Dijkstra require non-negative weights?** Once a vertex is settled, the proof assumes no later path through an unsettled vertex can reduce it. A negative edge breaks that invariant.

**Could Bellman-Ford be used?** Yes for negative edges, at `O(VE)`, but it is unnecessary and far slower for positive road distances.

**Why stop when the destination is popped, not first discovered?** Discovery gives only a tentative distance. Popping under the algorithm's ordering establishes optimality.

**How is a path reconstructed?** Every successful relaxation assigns `parent[v]=u`. Starting at the destination, parent links are followed to the source and reversed.

**What if no path exists?** The heap empties without settling the destination. The result reports `reachable=false`, an empty path, and infinite cost.

**What if source equals destination?** Both algorithms return cost 0 and path `[source]`.

**Why use lazy heap deletion?** Python's heap has no efficient decrease-key. Pushing the improved pair and skipping stale pops is simple, correct, and keeps logarithmic heap operations.

**Can A* reopen a vertex?** Yes, the implementation supports reopening after a better `g` value. A consistent heuristic normally makes this unnecessary, but the behavior is robust.

**What happens if `h=0`?** A* becomes Dijkstra, preserving correctness.

**Could an overestimating heuristic be faster?** Possibly, but it can lose optimality. This assignment requires shortest paths, so the implementation uses a proven safe lower bound.

**Why do equal optimal costs not always imply equal paths?** Multiple distinct paths may have the same total cost. Heap tie-breaking and relaxation order can select different but equally optimal paths.

### Representation and complexity

**Why adjacency lists instead of a matrix?** The 264,346^2 matrix has about 69.9 billion cells, almost all empty. Adjacency lists store `O(V+E)` information and enumerate real outgoing arcs directly.

**Why keep 1-based arrays?** It avoids a large ID mapping and makes paths correspond exactly to DIMACS IDs. Index 0 is intentionally unused.

**What dominates memory?** Python edge objects/lists and per-query `distance`, `parent`, and state arrays. A production implementation could use packed integer arrays or C++ structs.

**Is average degree `E/V` or `2E/V`?** For a directed graph, average out-degree and in-degree are each `E/V`; average total degree is `2E/V`. This report states both to remove ambiguity.

**Does A* improve worst-case complexity?** No. Its worst case matches Dijkstra's asymptotic bound. Its benefit is reducing the practical explored subset.

### Experimental validity

**Why use induced subgraphs?** They preserve every original arc between selected vertices and avoid fabricating graph structure or weights.

**Why BFS-prefix sampling?** It creates nested, geographically coherent road regions and exact sizes. Uniform random vertices would usually yield a fragmented graph.

**Does sampling bias results?** Yes. BFS prefixes emphasize one connected region, and boundary-separated pairs are deliberately difficult. Conclusions are scoped to this protocol; raw configuration is exposed for alternative studies.

**Why five query pairs?** It satisfies the assignment minimum while averaging over endpoint variation. A research-grade study should use hundreds or thousands and confidence intervals.

**Why median-of-five timing?** One Python timing can be distorted by scheduling or runtime noise. The median rejects isolated spikes; the final table averages the five per-query medians.

**Why report operation counts as well as time?** Counts are machine-independent evidence of algorithmic work; wall time depends on CPU, interpreter, OS, caches, and background load.

**Why did A* do fewer operations but run slower?** Its heuristic adds projection and floating-point work to each candidate. The 3%-8% scan reduction was too small to offset this overhead in Python.

**How is reproducibility enforced?** Official fixed URLs, SHA-256 hashes, fixed seed, fixed sizes, stored metadata, deterministic sampling, raw CSV rows, explicit dependencies, and a single pipeline command.

**What threats to validity remain?** One city, distance weights only, historical map errors, one Python runtime/hardware environment, five pairs per size, induced-subgraph boundaries, and no memory profiling in the main table.

### Dynamic routing and extensions

**Does the bonus update the graph permanently?** No. A weight callback overlays congestion costs, so the immutable base graph remains reusable.

**Why recompute instead of using a dynamic shortest-path data structure?** The assignment asks to modify costs and recompute. Re-running is simple and correct; frequent real-time updates could justify incremental algorithms.

**Why did a 5x penalty increase total cost by only 1.54%?** The solver found a detour avoiding most penalized arcs. That is precisely the adaptive behavior routing systems need.

**How could the model include UAVs?** Vertices could be 3D waypoints; edges could encode feasible flight segments; weights could combine distance, energy, wind, risk, and no-fly constraints. The algorithms remain valid if weights stay non-negative and the heuristic is a lower bound.

**How could production road routing be faster?** Use packed data structures, bidirectional Dijkstra/A*, contraction hierarchies, ALT landmarks, arc flags, multi-level overlays, and batched/preprocessed queries.

**How would travel-time A* remain admissible?** Divide straight-line distance by a true upper bound on possible speed; never use average speed as a lower-bound time estimate if faster travel is possible.

## 10. Testing and verification evidence

The test suite covers:

- known optimal cost and exact path;
- A*/Dijkstra agreement;
- disconnected destinations;
- source equals destination;
- compressed DIMACS graph and coordinate parsing.

Last local result:

```text
Ran 5 tests ... OK
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

## 11. Useful CLI commands

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

## 12. Final conclusion

The project demonstrates more than calling a shortest-path routine: it selects and verifies a public mobility dataset, parses a documented interchange format, models direction and weights explicitly, implements and instruments two algorithms, designs reproducible nested-scale experiments, validates optimality, exposes raw paths/results, visualizes scaling, and shows rerouting under dynamic costs.

The central empirical lesson is that **fewer expansions do not automatically mean lower latency**. A* consistently reduced search work, but its heuristic overhead outweighed that saving in this Python setup. That distinction - algorithmic work versus end-to-end implementation cost - is exactly why real experimental evaluation matters.

