from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
import sys
from time import strftime

if __package__ in (None, ""):
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from exp3.graph_coloring import (
    VARIANTS,
    GraphData,
    generate_random_k_colorable_graph,
    load_dimacs_graph,
    run_variant_on_graph,
    small_validation_graph,
    validate_coloring,
)
from exp3.plot_benchmark_results import plot_from_csv


@dataclass(frozen=True)
class ExperimentJob:
    experiment_group: str
    graph_family: str
    dataset: str
    graph: GraphData
    color_limit: int
    max_solutions: int
    timeout_seconds: float


PROVIDED_MAPS = {
    "le450_5a.col": {"color_limit": 5},
    "le450_15b.col": {"color_limit": 15},
    "le450_25a.col": {"color_limit": 25},
}
DATASETS = {name: {"color_limit": config["color_limit"], "max_solutions": 1} for name, config in PROVIDED_MAPS.items()}

RANDOM_GRAPH_SIZES = [20, 40, 60, 80]
RANDOM_GRAPH_DENSITIES = [0.12, 0.24]
RANDOM_GRAPH_SEEDS = [11, 29, 47]
MULTI_SOLUTION_TARGETS = [1, 10, 100, 1000]
DEFAULT_GROUPS = ["correctness", "provided_maps", "pruning_ablation", "scaling_random_graphs", "multi_solution_25"]

FIELDNAMES = [
    "experiment_group",
    "graph_family",
    "dataset",
    "variant",
    "name",
    "target_density",
    "generator_seed",
    "declared_classes",
    "n_vertices",
    "n_edges",
    "density",
    "min_degree",
    "avg_degree",
    "max_degree",
    "component_count",
    "largest_component",
    "clique_lower_bound",
    "used_colors",
    "success",
    "timed_out",
    "pruned_by_clique",
    "search_status",
    "node_expansions",
    "backtracks",
    "runtime_seconds",
    "overhead_ms_per_node",
    "first_fail_depth",
    "timeout_seconds",
    "solutions_found",
    "solution_target",
    "stopped_on_target",
    "color_limit",
    "valid_coloring",
    "explanation_notes",
]
LEGACY_FIELDNAMES = [field for field in FIELDNAMES if field not in {"target_density", "generator_seed"}]


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
    with path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        header = next(reader, None)
        if header is None:
            return []
        rows: list[dict[str, object]] = []
        for values in reader:
            if not values:
                continue
            rows.append(values_to_row(values))
        return rows


def values_to_row(values: list[str]) -> dict[str, object]:
    if len(values) == len(FIELDNAMES):
        return {field: values[index] for index, field in enumerate(FIELDNAMES)}
    if len(values) == len(LEGACY_FIELDNAMES):
        legacy_row = {field: values[index] for index, field in enumerate(LEGACY_FIELDNAMES)}
        expanded: dict[str, object] = {}
        for field in FIELDNAMES:
            if field == "target_density":
                expanded[field] = ""
            elif field == "generator_seed":
                expanded[field] = ""
            else:
                expanded[field] = legacy_row.get(field, "")
        return expanded
    # Fallback: preserve as much aligned data as possible and keep new columns blank.
    padded = values + [""] * max(0, len(FIELDNAMES) - len(values))
    return {field: padded[index] if index < len(padded) else "" for index, field in enumerate(FIELDNAMES)}


def csv_header_matches(csv_path: str | Path, fieldnames: list[str]) -> bool:
    path = Path(csv_path)
    if not path.exists():
        return True
    with path.open("r", newline="", encoding="utf-8") as handle:
        header = next(csv.reader(handle), [])
    return header == fieldnames


def rewrite_results_csv(csv_path: str | Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    path = Path(csv_path)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def result_identity(row: dict[str, object]) -> tuple[str, str, str, str]:
    return (
        str(row["experiment_group"]),
        str(row["dataset"]),
        str(row["variant"]),
        str(row.get("solution_target", "")),
    )


def row_matches_current_plan(row: dict[str, object], timeout_seconds: float) -> bool:
    row_timeout = float(row.get("timeout_seconds", 0.0))
    return abs(row_timeout - timeout_seconds) < 1e-9


def append_result_row(csv_path: str | Path, fieldnames: list[str], row: dict[str, object]) -> None:
    path = Path(csv_path)
    write_header = not path.exists() or path.stat().st_size == 0
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()
        writer.writerow(row)


def build_jobs(groups: list[str], timeout_seconds: float) -> list[ExperimentJob]:
    base_dir = Path(__file__).resolve().parent
    jobs: list[ExperimentJob] = []

    if "correctness" in groups:
        graph = small_validation_graph()
        jobs.append(
            ExperimentJob(
                experiment_group="correctness",
                graph_family="small_validation",
                dataset=str(graph.metadata["dataset_name"]),
                graph=graph,
                color_limit=4,
                max_solutions=1,
                timeout_seconds=min(timeout_seconds, 10.0),
            )
        )

    if "provided_maps" in groups:
        for dataset_name, config in PROVIDED_MAPS.items():
            graph = load_dimacs_graph(base_dir / dataset_name)
            jobs.append(
                ExperimentJob(
                    experiment_group="provided_maps",
                    graph_family="dimacs_leighton",
                    dataset=dataset_name,
                    graph=graph,
                    color_limit=int(config["color_limit"]),
                    max_solutions=1,
                    timeout_seconds=timeout_seconds,
                )
            )

    if "pruning_ablation" in groups:
        for dataset_name, config in PROVIDED_MAPS.items():
            graph = load_dimacs_graph(base_dir / dataset_name)
            jobs.append(
                ExperimentJob(
                    experiment_group="pruning_ablation",
                    graph_family="dimacs_leighton",
                    dataset=dataset_name,
                    graph=graph,
                    color_limit=int(config["color_limit"]),
                    max_solutions=1,
                    timeout_seconds=timeout_seconds,
                )
            )

    if "scaling_random_graphs" in groups:
        for n_vertices in RANDOM_GRAPH_SIZES:
            for density in RANDOM_GRAPH_DENSITIES:
                for seed in RANDOM_GRAPH_SEEDS:
                    graph = generate_random_k_colorable_graph(
                        n_vertices,
                        density,
                        seed,
                        color_limit=4,
                        dataset_name=f"random_colorable_n{n_vertices}_p{density:.2f}_s{seed}",
                    )
                    jobs.append(
                        ExperimentJob(
                            experiment_group="scaling_random_graphs",
                            graph_family="random_k_colorable",
                            dataset=str(graph.metadata["dataset_name"]),
                            graph=graph,
                            color_limit=4,
                            max_solutions=1,
                            timeout_seconds=min(timeout_seconds, 30.0),
                        )
                    )
    if "multi_solution_25" in groups:
        dataset_name = "le450_25a.col"
        graph = load_dimacs_graph(base_dir / dataset_name)
        for target in MULTI_SOLUTION_TARGETS:
            jobs.append(
                ExperimentJob(
                    experiment_group="multi_solution_25",
                    graph_family="dimacs_leighton",
                    dataset=dataset_name,
                    graph=graph,
                    color_limit=25,
                    max_solutions=target,
                    timeout_seconds=timeout_seconds,
                )
            )
    return jobs


def should_run_variant(group: str, variant_id: str) -> bool:
    if group == "correctness":
        return variant_id in {"B0", "B5"}
    return True


def variant_for_job(variant, job: ExperimentJob):
    if job.max_solutions <= 1 or not variant.symmetry_breaking:
        return variant
    # Multi-solution mode should enumerate actual alternative assignments, so
    # disable symmetry breaking for B5 while keeping the rest of its pruning stack.
    return type(variant)(
        id=variant.id,
        name=variant.name,
        forward_checking=variant.forward_checking,
        mrv=variant.mrv,
        degree_tiebreak=variant.degree_tiebreak,
        lcv=variant.lcv,
        symmetry_breaking=False,
        clique_bound=variant.clique_bound,
        component_decomposition=variant.component_decomposition,
    )


def make_result_row(job: ExperimentJob, variant_id: str, variant_name: str, result) -> dict[str, object]:
    graph = job.graph
    valid_coloring = bool(result.success and validate_coloring(graph.adj_list, result.colors))
    degrees = graph.degrees
    return {
        "experiment_group": job.experiment_group,
        "graph_family": job.graph_family,
        "dataset": job.dataset,
        "variant": variant_id,
        "name": variant_name,
        "target_density": graph.metadata.get("edge_probability", ""),
        "generator_seed": graph.metadata.get("seed", ""),
        "declared_classes": graph.metadata.get("declared_classes", job.color_limit),
        "n_vertices": graph.num_nodes,
        "n_edges": graph.num_edges,
        "density": round(graph.density, 6),
        "min_degree": min(degrees, default=0),
        "avg_degree": round(sum(degrees) / len(degrees), 6) if degrees else 0.0,
        "max_degree": max(degrees, default=0),
        "component_count": result.component_count,
        "largest_component": result.largest_component,
        "clique_lower_bound": result.clique_lower_bound,
        "used_colors": result.used_colors,
        "success": result.success,
        "timed_out": result.timed_out,
        "pruned_by_clique": result.pruned_by_clique,
        "search_status": result.search_status,
        "node_expansions": result.node_expansions,
        "backtracks": result.backtracks,
        "runtime_seconds": round(result.runtime_seconds, 6),
        "overhead_ms_per_node": round(result.overhead_ms_per_node, 6),
        "first_fail_depth": result.first_fail_depth if result.first_fail_depth is not None else "",
        "timeout_seconds": round(job.timeout_seconds, 6),
        "solutions_found": result.solutions_found,
        "solution_target": result.solution_target,
        "stopped_on_target": result.stopped_on_target,
        "color_limit": job.color_limit,
        "valid_coloring": valid_coloring,
        "explanation_notes": (
            f"{result.explanation_notes}; multi_solution_target={job.max_solutions}"
            if job.max_solutions > 1
            else result.explanation_notes
        ),
    }


def run_all(
    timeout_seconds: float = 60.0,
    resume: bool = True,
    output_path: str | Path | None = None,
    groups: list[str] | None = None,
) -> list[dict[str, object]]:
    selected_groups = groups or DEFAULT_GROUPS
    jobs = build_jobs(selected_groups, timeout_seconds)
    output_file = Path(output_path) if output_path is not None else Path(__file__).resolve().parent / "benchmark_results.csv"
    rows: list[dict[str, object]] = load_existing_results(output_file) if resume else []

    if not resume and output_file.exists():
        output_file.unlink()
    elif resume and output_file.exists() and not csv_header_matches(output_file, FIELDNAMES):
        rewrite_results_csv(output_file, FIELDNAMES, rows)

    completed = {
        result_identity(row)
        for row in rows
        if row_matches_current_plan(row, timeout_seconds)
    }
    total_jobs = sum(
        1
        for job in jobs
        for variant_id in VARIANTS
        if should_run_variant(job.experiment_group, variant_id)
    )
    completed_count = len(completed)

    log(
        f"Starting experiment run | groups={','.join(selected_groups)} | timeout={timeout_seconds:.0f}s | resume={'on' if resume else 'off'} | output={output_file}",
        completed_count=completed_count,
        total_count=total_jobs,
    )

    for job in jobs:
        log(
            f"Dataset {job.dataset} | group={job.experiment_group} | colors={job.color_limit} | nodes={job.graph.num_nodes}",
            completed_count=completed_count,
            total_count=total_jobs,
        )
        for variant_id, variant in VARIANTS.items():
            if not should_run_variant(job.experiment_group, variant_id):
                continue
            identity = (job.experiment_group, job.dataset, variant_id, str(job.max_solutions))
            if identity in completed:
                log(
                    f"{variant_id} skipped | {job.dataset} already saved",
                    completed_count=completed_count,
                    total_count=total_jobs,
                )
                continue
            log(
                f"{variant_id} started | dataset={job.dataset} | group={job.experiment_group} | target={job.max_solutions}",
                completed_count=completed_count,
                total_count=total_jobs,
            )
            active_variant = variant_for_job(variant, job)
            result = run_variant_on_graph(
                job.graph,
                job.color_limit,
                active_variant,
                timeout_seconds=job.timeout_seconds,
                max_solutions=job.max_solutions,
            )
            row = make_result_row(job, variant_id, variant.name, result)
            rows.append(row)
            completed.add(identity)
            completed_count += 1
            append_result_row(output_file, FIELDNAMES, row)
            log(
                f"{variant_id} finished | status={result.search_status} | valid={row['valid_coloring']} | clique_lb={result.clique_lower_bound} | nodes={result.node_expansions} | backtracks={result.backtracks} | time={result.runtime_seconds:.4f}s",
                completed_count=completed_count,
                total_count=total_jobs,
            )

    if rows:
        log(
            f"Saved experiment table to {output_file}",
            completed_count=completed_count,
            total_count=total_jobs,
        )
        for figure_path in plot_from_csv(output_file):
            log(
                f"Saved artifact to {figure_path}",
                completed_count=completed_count,
                total_count=total_jobs,
            )
    return rows


def parse_groups(argv: list[str]) -> list[str]:
    groups: list[str] = []
    for index, token in enumerate(argv):
        if token == "--group" and index + 1 < len(argv):
            groups.extend(item.strip() for item in argv[index + 1].split(",") if item.strip())
    return groups or DEFAULT_GROUPS


if __name__ == "__main__":
    timeout = float(sys.argv[1]) if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else 60.0
    resume = "--fresh" not in sys.argv[1:]
    groups = parse_groups(sys.argv[1:])
    run_all(timeout_seconds=timeout, resume=resume, groups=groups)
