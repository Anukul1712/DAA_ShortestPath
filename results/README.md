# Experimental Outputs

This folder satisfies submission criteria 5 and 6 and separates machine-readable tables, visual results, and the bonus experiment.

## `tables/`

- `raw_results.csv` - all 50 algorithm/query rows, native costs, meter conversions, metrics, and complete official-ID paths.
- `summary_results.csv` - average native cost, average meters, work metrics, and timing by size and algorithm.
- `graph_statistics.csv` - vertex, arc, and degree statistics at every size.
- `metadata.json` - seed, sizes, query count, and timing repetitions.
- `heuristic_study_raw.csv` - all 200 combinations of graph size, query, and heuristic weight.
- `heuristic_study_summary.csv` - optimality, work, and runtime summarized by size and weight.
- `heuristic_study_metadata.json` - tested weights and reproducibility parameters.

## `plots/`

- `runtime_comparison.png`
- `vertices_explored.png`
- `edges_examined.png`
- `search_work_reduction.png` - percentage of Dijkstra's search work avoided by A*.
- `runtime_speedup.png` - mean Dijkstra runtime divided by mean A* runtime.
- `per_query_runtime.png` - side-by-side timings for every one of the 25 query pairs.
- `cost_agreement.png` - Dijkstra and A* distance agreement for all query pairs.
- `graph_scaling.png` - directed-edge growth and average out-degree by graph size.
- `heuristic_strength_vertices.png` - search work as heuristic strength changes.
- `heuristic_strength_runtime.png` - runtime response to heuristic strength.
- `heuristic_tradeoff.png` - solution-quality and efficiency tradeoff.
- `dynamic_route_comparison.png` - geographic overlay of the original and rerouted paths.
- `dynamic_cost_comparison.png` - physical route length compared with congestion-adjusted objective cost.
- `dynamic_route_overlap.png` - shared/unique path edges and the number of congested edges avoided.
- `dynamic_congestion_profile.png` - edge-by-edge normal and penalized costs along the original route.
- `dynamic_parameter_sensitivity.png` - route distance and congestion avoidance across beta values.
- `dynamic_alpha_beta_heatmap.png` - route IDs, affected-edge usage, and savings for all alpha-beta combinations.

## `bonus/`

- `dynamic_result.json` - formula parameters, all selected congested edges, four cost comparisons, overlap metrics, savings, and complete original/new paths.
- `dynamic_parameter_study.csv` - full results for 24 combinations of alpha and beta.
- `dynamic_parameter_study_metadata.json` - tested grid, scenario count, route count, and interpretation.

All artifacts are regenerated with:

```bash
python scripts/run_all.py
```

Run only the parameter study with:

```bash
python scripts/run_heuristic_study.py
```

