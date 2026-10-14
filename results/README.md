# Experimental Outputs

This folder satisfies submission criteria 5 and 6 and separates machine-readable tables, visual results, and the bonus experiment.

## `tables/`

- `raw_results.csv` - all 50 algorithm/query rows and complete official-ID paths.
- `summary_results.csv` - averages and median timing by size and algorithm.
- `graph_statistics.csv` - vertex, arc, and degree statistics at every size.
- `metadata.json` - seed, sizes, query count, and timing repetitions.

## `plots/`

- `runtime_comparison.png`
- `vertices_explored.png`
- `edges_examined.png`
- `dynamic_route_comparison.png`

## `bonus/`

- `dynamic_result.json` - formula parameters, changed costs, route comparison, and complete original/new paths.

All artifacts are regenerated with:

```bash
python scripts/run_all.py
```

