# Dataset Reference, Format, and Detailed Explanation

This document satisfies submission criterion 2 and answers every dataset question in Part A of the problem statement.

## 1. Dataset identity

| Property | Value |
|---|---|
| Dataset | 9th DIMACS Implementation Challenge, `USA-road-d.NY` |
| Region | New York road network |
| Original source family | U.S. Census Bureau TIGER/Line road data |
| Challenge collection | 9th DIMACS Implementation Challenge: Shortest Paths |
| Graph type | Sparse weighted road graph represented as directed arcs |
| Full vertices | 264,346 |
| Full directed arcs | 733,846 |
| Coordinate rows | 264,346 |
| Weight metric | Spatial distance between arc endpoints |
| Native stored unit | 0.1 meter per integer unit (decimeter resolution) |
| Coordinate unit | Signed decimal degrees with six implied decimal places |

Authoritative references:

- Challenge download page: <https://www.diag.uniroma1.it/challenge9/download.shtml>
- DIMACS file-format specification: <https://www.diag.uniroma1.it/challenge9/format.shtml>
- TIGER/Line road-network documentation: <https://www.diag.uniroma1.it/challenge9/data/tiger/>

The Challenge page describes `USA-road-d.NY` as the New York distance graph. The underlying road collection was assembled from U.S. Census TIGER/Line data for algorithm research. It is a historical benchmark, not a live road map.

## 2. Why there are two dataset files

The graph topology and coordinates are stored separately:

| File | Purpose | Important records |
|---|---|---|
| `USA-road-d.NY.gr` | Graph structure and edge weights | `p sp n m`, `a U V W` |
| `USA-road-d.NY.co` | Coordinates for graph vertices | `p aux sp co n`, `v ID X Y` |

The `.gz` versions contain exactly the same text compressed with gzip. The downloader keeps both compressed and extracted copies in `data/raw/`.

Separating topology from coordinates is useful because Dijkstra needs only the graph file, while coordinate-aware A* also needs the coordinate file.

## 3. General DIMACS line rules

DIMACS files are ASCII text. Every non-empty line begins with a one-character record type. Fields are separated by whitespace.

| First token | Meaning |
|---|---|
| `c` | Comment line; documentation for humans; ignored by the parser |
| `p` | Problem/declaration line; describes the file and its dimensions |
| `a` | Arc record in a graph file |
| `v` | Vertex-coordinate record in a coordinate file |

Blank lines and comment lines do not create graph data.

## 4. Detailed explanation of `p sp n m`

General form:

```text
p sp n m
```

| Field | Full meaning | Explanation |
|---|---|---|
| `p` | problem | Declares the main problem record. It must be the first non-comment graph line. |
| `sp` | shortest path | Says that this graph is formatted for a shortest-path problem. |
| `n` | number of nodes | Total number of vertex IDs. Valid IDs are `1` through `n`. |
| `m` | number of arcs | Number of directed `a` records expected later in the file. |

Actual NY record:

```text
p sp 264346 733846
```

This means the graph has 264,346 vertices, valid IDs 1 through 264,346, and exactly 733,846 directed arc records. The parser allocates `adjacency[0..264346]`, leaves index 0 unused, and verifies that it reads the declared number of arcs.

The letters `n` and `m` in the general form are variables. They are not written literally in the NY file.

## 5. Detailed explanation of `a U V W`

General form:

```text
a U V W
```

| Field | Full meaning | Explanation |
|---|---|---|
| `a` | arc | Declares one directed weighted edge. |
| `U` | tail/source vertex | Vertex where the permitted movement starts. |
| `V` | head/destination vertex | Vertex where the movement ends. |
| `W` | weight/cost | Non-negative integer distance cost for travelling from `U` to `V`. |

Actual records:

```text
a 1 2 803
a 2 1 803
```

Interpretation:

- `a 1 2 803` creates a directed arc from vertex 1 to vertex 2.
- `a 2 1 803` is a separate directed arc from vertex 2 to vertex 1.
- Both directions happen to exist and have the same weight in this example.
- The stored value `803` uses 0.1-meter units, so it represents 80.3 meters.
- The parser stores the first record as `adjacency[1].append(Edge(to=2, weight=803))`.

One arc record does not automatically imply a reverse arc. If only `a U V W` exists, movement is allowed from `U` to `V`, but not necessarily from `V` to `U`. The algorithm follows only explicitly stored outgoing arcs.

The DIMACS format can represent parallel arcs and self-loops. This implementation preserves them. All weights in this selected distance graph are non-negative, as required by Dijkstra and the implemented A* search.

## 6. Detailed explanation of `p aux sp co n`

The coordinate file begins with:

```text
p aux sp co n
```

| Field | Meaning |
|---|---|
| `p` | problem/declaration record |
| `aux` | this is an auxiliary file associated with the main graph |
| `sp` | the associated problem family is shortest path |
| `co` | the auxiliary data contains coordinates |
| `n` | number of coordinate records that follow |

The actual record `p aux sp co 264346` declares one coordinate record for each of the 264,346 vertices.

## 7. Detailed explanation of `v ID X Y`

General form:

```text
v ID X Y
```

| Field | Full meaning | Explanation |
|---|---|---|
| `v` | vertex coordinate | Declares the location of one vertex. |
| `ID` | vertex identifier | Refers to the same numbered vertex used in `.gr` arc records. |
| `X` | x-coordinate/longitude | Signed longitude with six implied decimal places. |
| `Y` | y-coordinate/latitude | Signed latitude with six implied decimal places. |

Actual record:

```text
v 1 -73530767 41085396
```

Conversion:

```text
longitude = -73530767 / 1,000,000 = -73.530767 degrees
latitude  =  41085396 / 1,000,000 =  41.085396 degrees
```

Vertex 1 is therefore located at `(longitude, latitude) = (-73.530767, 41.085396)`. Negative longitude is expected because New York is west of Greenwich; positive latitude is expected because it is north of the equator.

Integers avoid locale and floating-point text-format problems, are fast to parse, and preserve the six supplied decimal places. Conversion to floating point happens only when geometry is required.

## 8. Understanding the weight unit correctly

The official TIGER/Line page describes the metric as spatial distance in meters. The final distributed `USA-road-d` graph retains one decimal place using integer decimeters: one stored unit is 0.1 meter.

This can be checked directly:

```text
a 1 2 803
v 1 -73530767 41085396
v 2 -73530538 41086098
```

The coordinate distance from vertex 1 to 2 is approximately 80.3 meters, while the stored weight is 803. Therefore:

```text
physical distance in meters = W * 0.1
```

The project preserves native integers for exact shortest-path arithmetic and records `weight_unit_meters = 0.1`. Generated results contain both native cost and converted meter cost. A uniform positive scale does not change which path is shortest, but correct conversion is essential for reporting and for expressing the A* heuristic in the same unit as `g(v)`.

## 9. How the raw files become a graph

```text
raw graph record                    in-memory representation
----------------                    ------------------------
p sp n m                            allocate n + 1 adjacency lists
a U V W                             adjacency[U].append(Edge(V, W))
v ID X Y                            coordinates[ID] = (X/1e6, Y/1e6)
```

The resulting model is:

```text
G = (V, E)
V = road-network points identified by integers 1..264346
E = explicitly listed directed road movements
w(U,V) = stored non-negative distance cost W
```

The implementation retains vertex identifiers, outgoing adjacency lists, arc destinations and weights, and longitude/latitude. Comments and unneeded metadata are discarded after parsing.

## 10. Full graph statistics

| Statistic | Value | Interpretation |
|---|---:|---|
| Vertices | 264,346 | Number of road-network points |
| Directed arcs | 733,846 | Number of permitted directed movements |
| Average out-degree | 2.7761 | Mean outgoing arcs per vertex, `E/V` |
| Maximum out-degree | 8 | Largest outgoing adjacency list |
| Average total degree | 5.5522 | Mean in-degree plus out-degree, `2E/V` |
| Maximum total degree | 16 | Largest in-degree plus out-degree |

The graph is sparse because `E` is only about 2.78 times `V`. An adjacency list is much more appropriate than a `V x V` matrix.

## 11. Detailed answers to all Part A questions

### 1. What is the dataset name?

The dataset is the **9th DIMACS Implementation Challenge New York distance road graph**, identified by `USA-road-d.NY`. `USA-road` identifies the family, `d` identifies the distance metric, and `NY` identifies the New York region.

### 2. What is the source or URL?

The official download page is <https://www.diag.uniroma1.it/challenge9/download.shtml>. Format details are at <https://www.diag.uniroma1.it/challenge9/format.shtml>, and road-network provenance is at <https://www.diag.uniroma1.it/challenge9/data/tiger/>.

### 3. What does the dataset contain?

It contains a historical road topology for the New York region. The `.gr` file lists numbered vertices and weighted directed arcs. The `.co` file gives the geographic coordinate of each numbered vertex. Together they support point-to-point routing, A* guidance, and map visualization.

### 4. How many records, nodes, and edges are used?

The full data has 264,346 graph vertices, 733,846 directed arc records, and 264,346 coordinate records, plus declaration and comment lines. The complete graph is loaded before induced experimental samples of 1,000, 5,000, 10,000, 25,000, and 50,000 vertices are constructed.

### 5. How is it converted into a graph?

The problem line determines array size. Each arc record becomes one `Edge` in the source vertex's adjacency list. Each coordinate record becomes one `(longitude, latitude)` value indexed by vertex ID. Direction, IDs, and integer weights are preserved. Sampled graphs retain only edges whose two endpoints are selected.

### 6. What does each vertex represent?

A vertex represents a numbered road-network point, normally a road junction, intersection, or segment endpoint in the TIGER/Line topology. It represents a location, not a vehicle. A vehicle moves through the network by traversing arcs.

### 7. What does each edge represent?

An edge represents a permitted directed movement between two road-network points. Two-way travel is represented by two opposite arc records. This explicit representation also supports one-way movement when only one direction exists.

### 8. What edge weight is used?

The `USA-road-d` variant uses spatial distance. Each native integer `W` has 0.1-meter resolution. The algorithms optimize sums of native weights exactly, and reports convert using `meters = cost * 0.1`. The separate `USA-road-t` collection uses a travel-time-like cost and is not used here.

### 9. Why is this dataset suitable?

It is real, public, documented, sparse, non-negatively weighted, geographic, directly related to vehicular/IoV routing, much larger than the 50,000-vertex target, and a recognized shortest-path benchmark. It is small enough to reproduce on a laptop but large enough to expose meaningful scaling, heap, memory, reachability, and heuristic behavior.

## 12. Download, extraction, and checksums

Run:

```bash
python scripts/download_data.py
```

Generated local files:

| File | Size | Purpose |
|---|---:|---|
| `USA-road-d.NY.gr.gz` | 3,667,907 bytes | Compressed graph |
| `USA-road-d.NY.gr` | 14,437,459 bytes | Extracted graph |
| `USA-road-d.NY.co.gz` | 2,058,598 bytes | Compressed coordinates |
| `USA-road-d.NY.co` | 7,290,781 bytes | Extracted coordinates |

| Archive | SHA-256 |
|---|---|
| `USA-road-d.NY.gr.gz` | `7b2446c7ffe6179efbc42af6812448e8cb782f12968ca2bb1d50d979343056d4` |
| `USA-road-d.NY.co.gz` | `02547a628742164e02bd73f59e33a65d23dfac8fc54c09275c8b9169c38eafdf` |

Use `python scripts/download_data.py --no-extract` to retain only archives. All raw files are ignored by `data/raw/*` and are not included in commits.

## 13. Validation performed

The project verifies the problem line, declared arc count, record shapes, integer fields, non-negative weights, vertex ranges, Dijkstra/A* cost equality, and path endpoints. Unit tests also cover compressed parsing, disconnected pairs, source-equals-destination, and explicit reconstruction.

## 14. Limitations

The Challenge warns of historical map errors, including gaps in some highways and bridges. The data lacks current closures, live congestion, turn restrictions, road names, speed limits, elevation, weather, vehicle restrictions, and UAV-specific 3D information.

The computed paths are optimal for the supplied graph and selected weight function, but they are not modern driving directions. These limitations do not reduce the dataset's value as a reproducible large-scale algorithm benchmark.

