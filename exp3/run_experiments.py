from __future__ import annotations

import csv
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from exp3.graph_coloring import VARIANTS, load_dimacs_graph, run_variant_on_file
from exp3.plot_benchmark_results import plot_from_csv


DATASETS = {
    "le450_5a.col": 5,
    "le450_15b.col": 15,
    "le450_25a.col": 25,
}


def run_all(timeout_seconds: float = 60.0) -> list[dict[str, object]]:
    base_dir = Path(__file__).resolve().parent
    rows: list[dict[str, object]] = []

    for dataset_name, color_limit in DATASETS.items():
        dataset_path = base_dir / dataset_name
        graph = load_dimacs_graph(dataset_path)
        print(f"\n=== {dataset_name} | colors={color_limit} | nodes={graph.num_nodes} ===")

        for variant_id, variant in VARIANTS.items():
            _, result = run_variant_on_file(dataset_path, color_limit, variant, timeout_seconds)
            row = {
                "dataset": dataset_name,
                "declared_classes": graph.metadata.get("declared_classes"),
                "variant": variant_id,
                "name": variant.name,
                "success": result.success,
                "timed_out": result.timed_out,
                "pruned_by_clique": result.pruned_by_clique,
                "clique_lower_bound": result.clique_lower_bound,
                "used_colors": result.used_colors,
                "node_expansions": result.node_expansions,
                "backtracks": result.backtracks,
                "runtime_seconds": round(result.runtime_seconds, 6),
                "overhead_ms_per_node": round(result.overhead_ms_per_node, 6),
            }
            rows.append(row)
            print(
                f"{variant_id:>2} | success={str(result.success):5s} | "
                f"clique_lb={result.clique_lower_bound:2d} | "
                f"used={result.used_colors:2d} | "
                f"nodes={result.node_expansions:8d} | "
                f"backtracks={result.backtracks:8d} | "
                f"time={result.runtime_seconds:9.4f}s"
            )

    output_path = base_dir / "benchmark_results.csv"
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nSaved benchmark table to {output_path}")
    for figure_path in plot_from_csv(output_path):
        print(f"Saved figure to {figure_path}")
    return rows


if __name__ == "__main__":
    timeout = float(sys.argv[1]) if len(sys.argv) > 1 else 60.0
    run_all(timeout_seconds=timeout)
