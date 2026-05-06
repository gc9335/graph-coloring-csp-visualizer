from __future__ import annotations

import csv
from pathlib import Path
import sys
from time import strftime

if __package__ in (None, ""):
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from exp3.graph_coloring import VARIANTS, load_dimacs_graph, run_variant_on_file
from exp3.plot_benchmark_results import plot_from_csv


DATASETS = {
    "le450_5a.col": {"color_limit": 5, "max_solutions": 1},
    "le450_15b.col": {"color_limit": 15, "max_solutions": 1},
    "le450_25a.col": {"color_limit": 25, "max_solutions": 1000},
}

FIELDNAMES = [
    "dataset",
    "declared_classes",
    "variant",
    "name",
    "success",
    "timed_out",
    "pruned_by_clique",
    "clique_lower_bound",
    "used_colors",
    "node_expansions",
    "backtracks",
    "runtime_seconds",
    "overhead_ms_per_node",
    "timeout_seconds",
    "solutions_found",
    "solution_target",
    "stopped_on_target",
]


def timestamp() -> str:
    return strftime("%H:%M:%S")


def format_progress(completed_count: int, total_count: int) -> str:
    return f"[{completed_count}/{total_count}]"


def log(message: str, *, completed_count: int | None = None, total_count: int | None = None) -> None:
    parts = [f"[{timestamp()}]"]
    if completed_count is not None and total_count is not None:
        parts.append(format_progress(completed_count, total_count))
    parts.append(message)
    print(" ".join(parts), flush=True)


def load_existing_results(csv_path: str | Path) -> list[dict[str, object]]:
    path = Path(csv_path)
    if not path.exists():
        return []

    rows: list[dict[str, object]] = []
    with path.open("r", newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            rows.append(dict(row))
    return rows


def result_identity(row: dict[str, object]) -> tuple[str, str]:
    return (str(row["dataset"]), str(row["variant"]))


def row_matches_current_plan(
    row: dict[str, object],
    dataset_config: dict[str, int],
    timeout_seconds: float,
) -> bool:
    row_target = int(row.get("solution_target", 1))
    row_timeout = float(row.get("timeout_seconds", 0.0))
    return (
        row_target == int(dataset_config["max_solutions"])
        and abs(row_timeout - timeout_seconds) < 1e-9
    )


def append_result_row(csv_path: str | Path, fieldnames: list[str], row: dict[str, object]) -> None:
    path = Path(csv_path)
    write_header = not path.exists() or path.stat().st_size == 0
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()
        writer.writerow(row)


def run_all(
    timeout_seconds: float = 60.0,
    resume: bool = True,
    output_path: str | Path | None = None,
) -> list[dict[str, object]]:
    base_dir = Path(__file__).resolve().parent
    output_file = Path(output_path) if output_path is not None else base_dir / "benchmark_results.csv"
    rows: list[dict[str, object]] = load_existing_results(output_file) if resume else []

    if not resume and output_file.exists():
        output_file.unlink()

    completed = {
        result_identity(row)
        for row in rows
        if row_matches_current_plan(
            row,
            DATASETS[str(row["dataset"])],
            timeout_seconds,
        )
    }
    total_jobs = len(DATASETS) * len(VARIANTS)
    completed_count = len(completed)

    log(
        f"Starting benchmark run | timeout={timeout_seconds:.0f}s | resume={'on' if resume else 'off'} | output={output_file}",
        completed_count=completed_count,
        total_count=total_jobs,
    )

    for dataset_name, dataset_config in DATASETS.items():
        color_limit = int(dataset_config["color_limit"])
        max_solutions = int(dataset_config["max_solutions"])
        dataset_path = base_dir / dataset_name
        graph = load_dimacs_graph(dataset_path)
        log(
            f"Dataset {dataset_name} | colors={color_limit} | nodes={graph.num_nodes} | target_solutions={max_solutions}",
            completed_count=completed_count,
            total_count=total_jobs,
        )

        for variant_id, variant in VARIANTS.items():
            identity = (dataset_name, variant_id)
            if identity in completed:
                log(
                    f"{variant_id} skipped | already saved in {output_file.name}",
                    completed_count=completed_count,
                    total_count=total_jobs,
                )
                continue

            log(
                f"{variant_id} started | dataset={dataset_name} | variant={variant.name}",
                completed_count=completed_count,
                total_count=total_jobs,
            )
            _, result = run_variant_on_file(
                dataset_path,
                color_limit,
                variant,
                timeout_seconds,
                max_solutions=max_solutions,
            )
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
                "timeout_seconds": round(timeout_seconds, 6),
                "solutions_found": result.solutions_found,
                "solution_target": result.solution_target,
                "stopped_on_target": result.stopped_on_target,
            }
            rows.append(row)
            completed.add(identity)
            completed_count += 1
            append_result_row(output_file, FIELDNAMES, row)
            log(
                f"{variant_id} finished | success={result.success} | "
                f"timed_out={result.timed_out} | "
                f"solutions={result.solutions_found}/{result.solution_target} | "
                f"clique_lb={result.clique_lower_bound} | "
                f"used={result.used_colors} | "
                f"nodes={result.node_expansions} | "
                f"backtracks={result.backtracks} | "
                f"time={result.runtime_seconds:.4f}s",
                completed_count=completed_count,
                total_count=total_jobs,
            )
            log(
                f"{variant_id} saved -> {output_file}",
                completed_count=completed_count,
                total_count=total_jobs,
            )

    if rows:
        log(
            f"Saved benchmark table to {output_file}",
            completed_count=completed_count,
            total_count=total_jobs,
        )
        for figure_path in plot_from_csv(output_file):
            log(
                f"Saved figure to {figure_path}",
                completed_count=completed_count,
                total_count=total_jobs,
            )
    return rows


if __name__ == "__main__":
    timeout = float(sys.argv[1]) if len(sys.argv) > 1 else 60.0
    resume = "--fresh" not in sys.argv[2:]
    run_all(timeout_seconds=timeout, resume=resume)
