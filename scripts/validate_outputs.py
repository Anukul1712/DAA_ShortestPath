"""Validate the complete generated-results manifest and core invariants."""

from __future__ import annotations

import csv
import json
from pathlib import Path


EXPECTED_PLOTS = {
    "runtime_comparison.png",
    "vertices_explored.png",
    "edges_examined.png",
    "search_work_reduction.png",
    "runtime_speedup.png",
    "per_query_runtime.png",
    "cost_agreement.png",
    "graph_scaling.png",
    "heuristic_strength_vertices.png",
    "heuristic_strength_runtime.png",
    "heuristic_tradeoff.png",
    "dynamic_route_comparison.png",
    "dynamic_cost_comparison.png",
    "dynamic_route_overlap.png",
    "dynamic_congestion_profile.png",
    "dynamic_parameter_sensitivity.png",
    "dynamic_alpha_beta_heatmap.png",
}


def _read_csv(path: Path, expected_rows: int) -> list[dict[str, str]]:
    if not path.is_file():
        raise AssertionError(f"missing output: {path}")
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != expected_rows:
        raise AssertionError(f"{path.name}: expected {expected_rows} rows, found {len(rows)}")
    return rows


def validate_outputs(root: Path) -> None:
    tables = root / "results" / "tables"
    bonus = root / "results" / "bonus"
    plots = root / "results" / "plots"

    raw = _read_csv(tables / "raw_results.csv", 50)
    _read_csv(tables / "summary_results.csv", 10)
    _read_csv(tables / "graph_statistics.csv", 5)
    heuristic_raw = _read_csv(tables / "heuristic_study_raw.csv", 200)
    _read_csv(tables / "heuristic_study_summary.csv", 40)
    parameter_rows = _read_csv(bonus / "dynamic_parameter_study.csv", 24)

    query_costs: dict[tuple[str, str], set[str]] = {}
    for row in raw:
        query_costs.setdefault((row["graph_size"], row["pair"]), set()).add(row["cost"])
    if len(query_costs) != 25 or any(len(costs) != 1 for costs in query_costs.values()):
        raise AssertionError("Dijkstra and A* costs do not agree for all 25 query pairs")

    admissible_rows = [row for row in heuristic_raw if float(row["heuristic_weight"]) <= 1.0]
    if len(admissible_rows) != 125 or any(row["is_optimal"].lower() != "true" for row in admissible_rows):
        raise AssertionError("all 125 admissible heuristic configurations must be optimal")

    ratio_groups: dict[float, set[tuple[str, str, str]]] = {}
    for row in parameter_rows:
        ratio = round(float(row["beta_alpha_ratio"]), 10)
        signature = (row["route_id"], row["physical_distance_meters"], row["congested_edges_used"])
        ratio_groups.setdefault(ratio, set()).add(signature)
    if any(len(signatures) != 1 for signatures in ratio_groups.values()):
        raise AssertionError("equal beta/alpha ratios produced inconsistent route outcomes")

    dynamic_path = bonus / "dynamic_result.json"
    if not dynamic_path.is_file():
        raise AssertionError(f"missing output: {dynamic_path}")
    dynamic = json.loads(dynamic_path.read_text(encoding="utf-8"))
    required_dynamic = {
        "baseline_path",
        "dynamic_path",
        "baseline_cost_under_congestion",
        "rerouted_dynamic_cost",
        "congested_edges_avoided",
        "dynamic_savings_vs_staying_percent",
    }
    missing_dynamic = required_dynamic - dynamic.keys()
    if missing_dynamic:
        raise AssertionError(f"dynamic_result.json is missing fields: {sorted(missing_dynamic)}")

    required_json = {
        tables / "metadata.json",
        tables / "heuristic_study_metadata.json",
        bonus / "dynamic_parameter_study_metadata.json",
    }
    missing_json = [path for path in required_json if not path.is_file()]
    if missing_json:
        raise AssertionError(f"missing metadata: {missing_json}")

    missing_plots = [name for name in sorted(EXPECTED_PLOTS) if not (plots / name).is_file()]
    empty_plots = [name for name in sorted(EXPECTED_PLOTS) if (plots / name).is_file() and (plots / name).stat().st_size == 0]
    if missing_plots or empty_plots:
        raise AssertionError(f"plot validation failed; missing={missing_plots}, empty={empty_plots}")

    print(
        "Validated complete output manifest: 50 benchmark rows, 200 heuristic rows, "
        "24 alpha-beta rows, and 17 plots."
    )


def main() -> None:
    validate_outputs(Path(__file__).resolve().parents[1])


if __name__ == "__main__":
    main()
