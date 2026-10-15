"""Plot benchmark summaries and road-network routes."""

from __future__ import annotations

import csv
from pathlib import Path

from .graph import RoadGraph


def generate_plots(tables_dir: str | Path, plots_dir: str | Path | None = None) -> list[Path]:
    try:
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise RuntimeError("Install dependencies with: pip install -r requirements.txt") from exc

    tables = Path(tables_dir)
    plots = Path(plots_dir) if plots_dir is not None else tables
    plots.mkdir(parents=True, exist_ok=True)
    with (tables / "summary_results.csv").open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    with (tables / "raw_results.csv").open(newline="", encoding="utf-8") as stream:
        raw_rows = list(csv.DictReader(stream))
    with (tables / "graph_statistics.csv").open(newline="", encoding="utf-8") as stream:
        graph_rows = list(csv.DictReader(stream))
    outputs: list[Path] = []
    specs = [
        ("average_execution_time_ms", "Mean execution time (ms)", "runtime_comparison.png"),
        ("average_vertices_explored", "Mean vertices explored", "vertices_explored.png"),
        ("average_edges_examined", "Mean edges examined", "edges_examined.png"),
    ]
    colors = {"dijkstra": "#D1495B", "astar": "#00798C"}
    for field, ylabel, filename in specs:
        fig, ax = plt.subplots(figsize=(8, 5), dpi=160)
        for algorithm in ("dijkstra", "astar"):
            selected = [row for row in rows if row["algorithm"] == algorithm]
            selected.sort(key=lambda x: int(x["graph_size"]))
            ax.plot(
                [int(row["graph_size"]) for row in selected],
                [float(row[field]) for row in selected],
                marker="o", linewidth=2.2, label="A*" if algorithm == "astar" else "Dijkstra",
                color=colors[algorithm],
            )
        ax.set_xlabel("Vertices in induced graph")
        ax.set_ylabel(ylabel)
        ax.grid(alpha=0.25)
        ax.legend()
        ax.set_title(f"{ylabel}: Dijkstra vs A*")
        fig.tight_layout()
        path = plots / filename
        fig.savefig(path)
        plt.close(fig)
        outputs.append(path)

    sizes = sorted({int(row["graph_size"]) for row in rows})
    by_key = {(int(row["graph_size"]), row["algorithm"]): row for row in rows}

    # Show the percentage of Dijkstra's search work avoided by A*.
    vertex_reduction = []
    edge_reduction = []
    for size in sizes:
        dijkstra = by_key[(size, "dijkstra")]
        astar = by_key[(size, "astar")]
        vertex_reduction.append(
            100.0 * (1.0 - float(astar["average_vertices_explored"]) / float(dijkstra["average_vertices_explored"]))
        )
        edge_reduction.append(
            100.0 * (1.0 - float(astar["average_edges_examined"]) / float(dijkstra["average_edges_examined"]))
        )
    fig, ax = plt.subplots(figsize=(9, 5.5), dpi=170)
    positions = list(range(len(sizes)))
    width = 0.36
    bars_vertices = ax.bar(
        [position - width / 2 for position in positions], vertex_reduction, width,
        label="Vertices explored", color="#00798C",
    )
    bars_edges = ax.bar(
        [position + width / 2 for position in positions], edge_reduction, width,
        label="Edges examined", color="#EDAE49",
    )
    ax.bar_label(bars_vertices, fmt="%.1f%%", padding=3, fontsize=8)
    ax.bar_label(bars_edges, fmt="%.1f%%", padding=3, fontsize=8)
    ax.set_xticks(positions, [f"{size:,}" for size in sizes])
    ax.set_xlabel("Vertices in induced graph")
    ax.set_ylabel("Reduction relative to Dijkstra (%)")
    ax.set_ylim(0, max(vertex_reduction + edge_reduction) * 1.18)
    ax.set_title("A* reduces search work on every tested graph")
    ax.grid(axis="y", alpha=0.25)
    ax.legend()
    fig.tight_layout()
    path = plots / "search_work_reduction.png"
    fig.savefig(path)
    plt.close(fig)
    outputs.append(path)

    # A ratio above one means A* completed the same query faster.
    speedups = [
        float(by_key[(size, "dijkstra")]["average_execution_time_ms"])
        / float(by_key[(size, "astar")]["average_execution_time_ms"])
        for size in sizes
    ]
    fig, ax = plt.subplots(figsize=(8, 5), dpi=170)
    bars = ax.bar(positions, speedups, color="#7A5195", width=0.62)
    ax.bar_label(bars, fmt="%.2fx", padding=4)
    ax.axhline(1.0, color="#333333", linewidth=1.2, linestyle="--", label="Equal runtime")
    ax.set_xticks(positions, [f"{size:,}" for size in sizes])
    ax.set_xlabel("Vertices in induced graph")
    ax.set_ylabel("Dijkstra time / A* time")
    ax.set_ylim(0, max(speedups) * 1.18)
    ax.set_title("Observed mean runtime speedup from A*")
    ax.grid(axis="y", alpha=0.25)
    ax.legend()
    fig.tight_layout()
    path = plots / "runtime_speedup.png"
    fig.savefig(path)
    plt.close(fig)
    outputs.append(path)

    # Display every timed run, not only the mean, in one panel per graph size.
    raw_by_key = {
        (int(row["graph_size"]), int(row["pair"]), row["algorithm"]): row
        for row in raw_rows
    }
    fig, axes = plt.subplots(2, 3, figsize=(12, 7.5), dpi=170)
    for ax, size in zip(axes.flat, sizes):
        pairs = sorted(
            int(row["pair"]) for row in raw_rows
            if int(row["graph_size"]) == size and row["algorithm"] == "dijkstra"
        )
        x = list(range(len(pairs)))
        width = 0.36
        ax.bar(
            [value - width / 2 for value in x],
            [float(raw_by_key[(size, pair, "dijkstra")]["execution_time_ms"]) for pair in pairs],
            width, label="Dijkstra", color=colors["dijkstra"],
        )
        ax.bar(
            [value + width / 2 for value in x],
            [float(raw_by_key[(size, pair, "astar")]["execution_time_ms"]) for pair in pairs],
            width, label="A*", color=colors["astar"],
        )
        ax.set_xticks(x, [f"Q{pair}" for pair in pairs])
        ax.set_title(f"{size:,} vertices")
        ax.grid(axis="y", alpha=0.2)
    axes.flat[-1].axis("off")
    axes[0, 0].set_ylabel("Execution time (ms)")
    axes[1, 0].set_ylabel("Execution time (ms)")
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower right", bbox_to_anchor=(0.88, 0.16))
    fig.suptitle("All 25 benchmark queries: measured execution time", fontsize=14)
    fig.supxlabel("Deterministic query number within each graph")
    fig.tight_layout(rect=(0, 0.04, 1, 0.95))
    path = plots / "per_query_runtime.png"
    fig.savefig(path)
    plt.close(fig)
    outputs.append(path)

    # Correct algorithms must agree on cost for every source-destination pair.
    dijkstra_costs = []
    astar_costs = []
    for size in sizes:
        pairs = sorted(
            int(row["pair"]) for row in raw_rows
            if int(row["graph_size"]) == size and row["algorithm"] == "dijkstra"
        )
        for pair in pairs:
            dijkstra_costs.append(float(raw_by_key[(size, pair, "dijkstra")]["cost_meters"]) / 1000.0)
            astar_costs.append(float(raw_by_key[(size, pair, "astar")]["cost_meters"]) / 1000.0)
    lower = min(dijkstra_costs + astar_costs)
    upper = max(dijkstra_costs + astar_costs)
    padding = max((upper - lower) * 0.05, 0.1)
    fig, ax = plt.subplots(figsize=(6.5, 6), dpi=170)
    ax.plot([lower - padding, upper + padding], [lower - padding, upper + padding],
            color="#555555", linestyle="--", linewidth=1.4, label="Exact agreement")
    ax.scatter(dijkstra_costs, astar_costs, color="#00798C", edgecolor="white", s=55,
               linewidth=0.7, alpha=0.9, label="25 query pairs")
    ax.set_xlim(lower - padding, upper + padding)
    ax.set_ylim(lower - padding, upper + padding)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("Dijkstra path cost (km)")
    ax.set_ylabel("A* path cost (km)")
    ax.set_title("Shortest-path cost agreement: 25 of 25 queries")
    ax.grid(alpha=0.2)
    ax.legend()
    fig.tight_layout()
    path = plots / "cost_agreement.png"
    fig.savefig(path)
    plt.close(fig)
    outputs.append(path)

    # Confirm how the induced benchmark graphs grow with the requested size.
    graph_rows.sort(key=lambda row: int(row["vertices"]))
    graph_sizes = [int(row["vertices"]) for row in graph_rows]
    edge_counts = [int(row["directed_edges"]) for row in graph_rows]
    average_degrees = [float(row["average_out_degree"]) for row in graph_rows]
    fig, (ax_edges, ax_degree) = plt.subplots(1, 2, figsize=(11, 4.8), dpi=170)
    ax_edges.plot(graph_sizes, edge_counts, marker="o", color="#003F5C", linewidth=2.2)
    ax_edges.set_xlabel("Vertices")
    ax_edges.set_ylabel("Directed edges")
    ax_edges.set_title("Induced graph growth")
    ax_edges.grid(alpha=0.25)
    ax_degree.plot(graph_sizes, average_degrees, marker="o", color="#FFA600", linewidth=2.2)
    for x_value, y_value in zip(graph_sizes, average_degrees):
        ax_degree.annotate(f"{y_value:.2f}", (x_value, y_value), xytext=(0, 7),
                           textcoords="offset points", ha="center", fontsize=8)
    ax_degree.set_xlabel("Vertices")
    ax_degree.set_ylabel("Average out-degree")
    ax_degree.set_title("Road-network sparsity remains stable")
    ax_degree.grid(alpha=0.25)
    fig.suptitle("Scale characteristics of the five benchmark graphs", fontsize=14)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    path = plots / "graph_scaling.png"
    fig.savefig(path)
    plt.close(fig)
    outputs.append(path)
    return outputs


def plot_dynamic_routes(
    graph: RoadGraph,
    bonus_dir: str | Path,
    plots_dir: str | Path | None = None,
) -> Path:
    """Plot the baseline and congestion-aware paths in geographic coordinates."""

    import json
    try:
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise RuntimeError("Install dependencies with: pip install -r requirements.txt") from exc

    bonus = Path(bonus_dir)
    plots = Path(plots_dir) if plots_dir is not None else bonus
    plots.mkdir(parents=True, exist_ok=True)
    report = json.loads((bonus / "dynamic_result.json").read_text(encoding="utf-8"))
    fig, ax = plt.subplots(figsize=(8, 6), dpi=170)
    for key, label, color, width, alpha in (
        ("baseline_subgraph_path", "Original shortest path", "#D1495B", 3.0, 0.8),
        ("dynamic_subgraph_path", "Route after congestion", "#00798C", 2.0, 0.9),
    ):
        points = [graph.coordinates[v] for v in report[key] if graph.coordinates[v] is not None]
        ax.plot([p[0] for p in points], [p[1] for p in points], label=label, color=color, linewidth=width, alpha=alpha)
    endpoints = [graph.coordinates[report["subgraph_source"]], graph.coordinates[report["subgraph_destination"]]]
    ax.scatter([p[0] for p in endpoints], [p[1] for p in endpoints], color="#222222", s=35, zorder=5)
    ax.annotate("S", endpoints[0], xytext=(5, 5), textcoords="offset points", weight="bold")
    ax.annotate("D", endpoints[1], xytext=(5, 5), textcoords="offset points", weight="bold")
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_title("Bonus: route change after simulated congestion")
    ax.grid(alpha=0.2)
    ax.legend()
    ax.set_aspect("equal", adjustable="datalim")
    fig.tight_layout()
    destination = plots / "dynamic_route_comparison.png"
    fig.savefig(destination)
    plt.close(fig)
    return destination


def generate_dynamic_analysis_plots(
    graph: RoadGraph,
    bonus_dir: str | Path,
    plots_dir: str | Path | None = None,
) -> list[Path]:
    """Create explanatory plots for the dynamic-cost bonus experiment."""

    import json
    try:
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise RuntimeError("Install dependencies with: pip install -r requirements.txt") from exc

    bonus = Path(bonus_dir)
    plots = Path(plots_dir) if plots_dir is not None else bonus
    plots.mkdir(parents=True, exist_ok=True)
    report = json.loads((bonus / "dynamic_result.json").read_text(encoding="utf-8"))
    outputs: list[Path] = []

    # Compare physical distance with the objective value after congestion costs.
    labels = ["Original route", "Rerouted path"]
    base_km = [
        report["baseline_base_distance_meters"] / 1000.0,
        report["rerouted_base_distance_meters"] / 1000.0,
    ]
    dynamic_km = [
        report["baseline_cost_under_congestion_meters_equivalent"] / 1000.0,
        report["rerouted_dynamic_cost_meters_equivalent"] / 1000.0,
    ]
    positions = [0, 1]
    width = 0.36
    fig, ax = plt.subplots(figsize=(8, 5.4), dpi=170)
    base_bars = ax.bar([x - width / 2 for x in positions], base_km, width,
                       label="Physical distance", color="#00798C")
    dynamic_bars = ax.bar([x + width / 2 for x in positions], dynamic_km, width,
                          label="Cost with congestion", color="#D1495B")
    ax.bar_label(base_bars, fmt="%.2f", padding=3)
    ax.bar_label(dynamic_bars, fmt="%.2f", padding=3)
    ax.set_xticks(positions, labels)
    ax.set_ylabel("Kilometers or kilometer-equivalent cost")
    ax.set_title("Bonus: rerouting avoids the cost of staying on the original path")
    ax.grid(axis="y", alpha=0.22)
    ax.legend()
    fig.tight_layout()
    path = plots / "dynamic_cost_comparison.png"
    fig.savefig(path)
    plt.close(fig)
    outputs.append(path)

    # Make route overlap and congestion avoidance visible without relying on the map.
    fig, (ax_overlap, ax_avoid) = plt.subplots(1, 2, figsize=(11, 5), dpi=170)
    shared = report["shared_path_edges"]
    original_only = report["baseline_only_edges"]
    rerouted_only = report["rerouted_only_edges"]
    ax_overlap.barh([0], [shared], color="#7A5195", label="Shared edges")
    ax_overlap.barh([0], [original_only], left=[shared], color="#D1495B", label="Original only")
    ax_overlap.barh([1], [shared], color="#7A5195")
    ax_overlap.barh([1], [rerouted_only], left=[shared], color="#00798C", label="Reroute only")
    ax_overlap.set_yticks([0, 1], ["Original route", "Rerouted path"])
    ax_overlap.set_xlabel("Directed path edges")
    ax_overlap.set_title("Route overlap")
    ax_overlap.grid(axis="x", alpha=0.2)
    ax_overlap.legend(fontsize=8)

    avoided = report["congested_edges_avoided"]
    used = report["congested_edges_used_by_reroute"]
    bars = ax_avoid.bar(["Avoided", "Still used"], [avoided, used],
                        color=["#00798C", "#D1495B"], width=0.62)
    ax_avoid.bar_label(bars, padding=3)
    ax_avoid.set_ylabel("Congested directed edges")
    ax_avoid.set_title("How much congestion the new route avoids")
    ax_avoid.grid(axis="y", alpha=0.2)
    fig.suptitle(
        f"Path structure: {report['edge_jaccard_similarity_percent']:.1f}% edge-set similarity",
        fontsize=14,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    path = plots / "dynamic_route_overlap.png"
    fig.savefig(path)
    plt.close(fig)
    outputs.append(path)

    # Show exactly where the multiplier changes the original route's edge costs.
    congested = {tuple(edge) for edge in report["congested_subgraph_edges"]}
    baseline_path = report["baseline_subgraph_path"]
    base_values = []
    dynamic_values = []
    for u, v in zip(baseline_path, baseline_path[1:]):
        weight = min(edge.weight for edge in graph.adjacency[u] if edge.to == v)
        meters = weight * graph.weight_unit_meters
        base_values.append(meters)
        dynamic_values.append(meters * report["congestion_multiplier"] if (u, v) in congested else meters)
    edge_indices = list(range(1, len(base_values) + 1))
    fig, ax = plt.subplots(figsize=(11, 5), dpi=170)
    ax.plot(edge_indices, base_values, color="#00798C", linewidth=1.3, label="Normal edge cost")
    ax.plot(edge_indices, dynamic_values, color="#D1495B", linewidth=1.3,
            label="Edge cost after congestion")
    congested_indices = [index for index, edge in enumerate(zip(baseline_path, baseline_path[1:]), 1)
                         if edge in congested]
    if congested_indices:
        ax.axvspan(min(congested_indices), max(congested_indices), color="#EDAE49", alpha=0.16,
                   label="Congested middle section")
    ax.set_xlabel("Edge position along the original route")
    ax.set_ylabel("Edge cost (meter-equivalent)")
    ax.set_title("Where the congestion penalty is applied")
    ax.grid(alpha=0.2)
    ax.legend()
    fig.tight_layout()
    path = plots / "dynamic_congestion_profile.png"
    fig.savefig(path)
    plt.close(fig)
    outputs.append(path)
    return outputs


def generate_heuristic_study_plots(
    tables_dir: str | Path,
    plots_dir: str | Path | None = None,
) -> list[Path]:
    """Plot the effect of scaling the admissible A* heuristic."""

    try:
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise RuntimeError("Install dependencies with: pip install -r requirements.txt") from exc

    tables = Path(tables_dir)
    plots = Path(plots_dir) if plots_dir is not None else tables
    plots.mkdir(parents=True, exist_ok=True)
    with (tables / "heuristic_study_summary.csv").open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    sizes = sorted({int(row["graph_size"]) for row in rows})
    weights = sorted({float(row["heuristic_weight"]) for row in rows})
    by_key = {(int(row["graph_size"]), float(row["heuristic_weight"])): row for row in rows}
    palette = ["#003F5C", "#2F4B7C", "#665191", "#A05195", "#D45087"]
    outputs: list[Path] = []

    for field, ylabel, title, filename in (
        (
            "vertices_percent_of_zero",
            "Vertices explored (% of zero heuristic)",
            "Stronger heuristics reduce A* search work",
            "heuristic_strength_vertices.png",
        ),
        (
            "runtime_percent_of_zero",
            "Runtime (% of zero heuristic)",
            "Runtime response to heuristic strength",
            "heuristic_strength_runtime.png",
        ),
    ):
        fig, ax = plt.subplots(figsize=(9, 5.5), dpi=170)
        for color, size in zip(palette, sizes):
            ax.plot(
                weights,
                [float(by_key[(size, weight)][field]) for weight in weights],
                marker="o",
                linewidth=2,
                color=color,
                label=f"{size:,} vertices",
            )
        ax.axvline(1.0, color="#222222", linestyle="--", linewidth=1.2, label="Standard A*")
        ax.axhline(100.0, color="#777777", linestyle=":", linewidth=1.0)
        ax.axvspan(1.0, max(weights), color="#EDAE49", alpha=0.12, label="Weighted A*: no exact guarantee")
        ax.set_xlabel("Heuristic weight lambda")
        ax.set_ylabel(ylabel)
        ax.set_title(title)
        ax.set_xticks(weights)
        ax.grid(alpha=0.22)
        ax.legend(fontsize=8, ncol=2)
        fig.tight_layout()
        path = plots / filename
        fig.savefig(path)
        plt.close(fig)
        outputs.append(path)

    aggregate = []
    for weight in weights:
        selected = [row for row in rows if float(row["heuristic_weight"]) == weight]
        aggregate.append({
            "weight": weight,
            "optimality_rate": sum(float(row["optimality_rate_percent"]) for row in selected) / len(selected),
            "maximum_gap": max(float(row["maximum_optimality_gap_percent"]) for row in selected),
            "vertices_percent": sum(float(row["vertices_percent_of_zero"]) for row in selected) / len(selected),
            "runtime_percent": sum(float(row["runtime_percent_of_zero"]) for row in selected) / len(selected),
        })
    fig, (ax_quality, ax_work) = plt.subplots(1, 2, figsize=(12, 5), dpi=170)
    ax_quality.plot(weights, [row["optimality_rate"] for row in aggregate], marker="o",
                    color="#00798C", linewidth=2.2, label="Optimal queries (%)")
    ax_quality.set_xlabel("Heuristic weight lambda")
    ax_quality.set_ylabel("Optimal queries (%)")
    ax_quality.set_ylim(0, 105)
    ax_quality.set_title("Solution quality")
    ax_quality.grid(alpha=0.22)
    gap_axis = ax_quality.twinx()
    gap_axis.plot(weights, [row["maximum_gap"] for row in aggregate], marker="s",
                  color="#D1495B", linewidth=1.8, label="Maximum cost gap (%)")
    gap_axis.set_ylabel("Maximum cost gap (%)")
    lines_a, labels_a = ax_quality.get_legend_handles_labels()
    lines_b, labels_b = gap_axis.get_legend_handles_labels()
    ax_quality.legend(lines_a + lines_b, labels_a + labels_b, loc="lower left", fontsize=8)

    ax_work.plot(weights, [row["vertices_percent"] for row in aggregate], marker="o",
                 color="#003F5C", linewidth=2.2, label="Vertices explored")
    ax_work.plot(weights, [row["runtime_percent"] for row in aggregate], marker="s",
                 color="#7A5195", linewidth=2.2, label="Runtime")
    ax_work.axhline(100.0, color="#777777", linestyle=":", linewidth=1.0)
    ax_work.set_xlabel("Heuristic weight lambda")
    ax_work.set_ylabel("Mean across sizes (% of zero heuristic)")
    ax_work.set_title("Efficiency tradeoff")
    ax_work.grid(alpha=0.22)
    ax_work.legend(fontsize=8)
    for axis in (ax_quality, ax_work):
        axis.axvline(1.0, color="#222222", linestyle="--", linewidth=1.1)
        axis.axvspan(1.0, max(weights), color="#EDAE49", alpha=0.12)
        axis.set_xticks(weights)
    fig.suptitle("Heuristic strength: efficiency versus optimality", fontsize=14)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    path = plots / "heuristic_tradeoff.png"
    fig.savefig(path)
    plt.close(fig)
    outputs.append(path)
    return outputs

