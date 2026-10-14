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

