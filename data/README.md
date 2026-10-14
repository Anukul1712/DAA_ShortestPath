# Dataset Reference and Schema

This folder satisfies submission criterion 2: **dataset source/reference**.

## Selected dataset

- **Name:** 9th DIMACS Implementation Challenge - `USA-road-d.NY`
- **Scenario:** New York vehicular road network
- **Source:** <https://www.diag.uniroma1.it/challenge9/download.shtml>
- **Format:** <https://www.diag.uniroma1.it/challenge9/format.shtml>
- **Road-data documentation:** <https://www.diag.uniroma1.it/challenge9/data/tiger/>
- **Full graph:** 264,346 vertices and 733,846 directed arcs
- **Weight:** physical distance in metres

## Download

From the repository root:

```bash
python scripts/download_data.py
```

The downloader places these archives in `data/raw/`:

| File | SHA-256 |
|---|---|
| `USA-road-d.NY.gr.gz` | `7b2446c7ffe6179efbc42af6812448e8cb782f12968ca2bb1d50d979343056d4` |
| `USA-road-d.NY.co.gz` | `02547a628742164e02bd73f59e33a65d23dfac8fc54c09275c8b9169c38eafdf` |

Raw archives are excluded from Git because they are reproducibly downloadable third-party data. The downloader is idempotent and prints the file hashes after verification.

## Raw schema

```text
p sp n m       declares n vertices and m directed arcs
a U V W        directed arc U -> V with integer weight W
v ID X Y       vertex coordinate; X/Y have six implied decimal places
```

## Graph interpretation

- Vertex: road-network location/intersection.
- Directed edge: permitted movement along a road segment.
- Weight: physical road-segment distance in metres.
- Coordinate: `(longitude, latitude)` after division by `1,000,000`.

The official source warns that this historical dataset contains map errors and gaps in some roads and bridges. It is suitable for algorithmic experiments, not current turn-by-turn navigation.

