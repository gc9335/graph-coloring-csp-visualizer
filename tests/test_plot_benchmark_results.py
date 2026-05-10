from __future__ import annotations

from pathlib import Path

from exp3.plot_benchmark_results import infer_timeout_seconds, load_rows, plot_from_csv
from exp3.run_experiments import FIELDNAMES


def make_row(**overrides) -> dict[str, object]:
    row = {
        "experiment_group": "provided_maps",
        "graph_family": "dimacs_leighton",
        "dataset": "le450_5a.col",
        "variant": "B0",
        "name": "Base Backtracking",
        "target_density": "",
        "generator_seed": "",
        "declared_classes": 5,
        "n_vertices": 10,
        "n_edges": 20,
        "density": 0.444444,
        "min_degree": 2,
        "avg_degree": 4.0,
        "max_degree": 6,
        "component_count": 1,
        "largest_component": 10,
        "clique_lower_bound": 5,
        "used_colors": 5,
        "success": True,
        "timed_out": False,
        "pruned_by_clique": False,
        "search_status": "success",
        "node_expansions": 42,
        "backtracks": 21,
        "runtime_seconds": 1.25,
        "overhead_ms_per_node": 29.76,
        "first_fail_depth": "",
        "timeout_seconds": 60.0,
        "solutions_found": 1,
        "solution_target": 1,
        "canonical_solutions_found": 1,
        "signature_solutions_found": 1,
        "stopped_on_target": True,
        "color_limit": 5,
        "valid_coloring": True,
        "explanation_notes": "clique_lower_bound=5; density=0.4444; max_degree=6",
    }
    row.update(overrides)
    return row


def test_infer_timeout_seconds_prefers_csv_value(tmp_path: Path):
    csv_path = tmp_path / "benchmark_results.csv"
    rows = [make_row(dataset="le450_5a.col"), make_row(dataset="le450_15b.col", timeout_seconds=120.0)]
    csv_path.write_text(
        "\n".join(
            [
                ",".join(FIELDNAMES),
                *[",".join(str(row[field]) for field in FIELDNAMES) for row in rows],
            ]
        ),
        encoding="utf-8",
    )

    loaded_rows = load_rows(csv_path)
    assert infer_timeout_seconds(loaded_rows) == 120.0


def test_plot_from_csv_generates_grouped_artifacts(tmp_path: Path):
    csv_path = tmp_path / "benchmark_results.csv"
    rows = [
        make_row(experiment_group="correctness", dataset="validation_k4", variant="B0", declared_classes=4, color_limit=4),
        make_row(experiment_group="correctness", dataset="validation_k4", variant="B5", declared_classes=4, color_limit=4),
        make_row(experiment_group="provided_maps", dataset="le450_5a.col", variant="B0"),
        make_row(experiment_group="provided_maps", dataset="le450_5a.col", variant="B5", runtime_seconds=0.5, node_expansions=10),
        make_row(experiment_group="pruning_ablation", dataset="le450_15b.col", variant="B0", timed_out=True, success=False, search_status="timeout"),
        make_row(experiment_group="pruning_ablation", dataset="le450_15b.col", variant="B5", runtime_seconds=2.0, node_expansions=100),
        make_row(experiment_group="scaling_random_graphs", dataset="random_a", variant="B0", n_vertices=20, density=0.08, target_density=0.12, generator_seed=11, runtime_seconds=0.2),
        make_row(experiment_group="scaling_random_graphs", dataset="random_b", variant="B0", n_vertices=40, density=0.10, target_density=0.12, generator_seed=29, runtime_seconds=0.4),
        make_row(experiment_group="scaling_random_graphs", dataset="random_c", variant="B5", n_vertices=20, density=0.22, target_density=0.24, generator_seed=11, runtime_seconds=0.1),
        make_row(experiment_group="scaling_random_graphs", dataset="random_d", variant="B5", n_vertices=40, density=0.25, target_density=0.24, generator_seed=29, runtime_seconds=0.3),
        make_row(experiment_group="multi_solution_25", dataset="le450_25a.col", variant="B0", declared_classes=25, color_limit=25, solution_target=1, solutions_found=1, canonical_solutions_found=1, signature_solutions_found=1, runtime_seconds=0.1, node_expansions=50),
        make_row(experiment_group="multi_solution_25", dataset="le450_25a.col", variant="B0", declared_classes=25, color_limit=25, solution_target=1000, solutions_found=1000, canonical_solutions_found=40, signature_solutions_found=40, runtime_seconds=4.0, node_expansions=500),
        make_row(experiment_group="multi_solution_25", dataset="le450_25a.col", variant="B5", declared_classes=25, color_limit=25, solution_target=1, solutions_found=1, canonical_solutions_found=1, signature_solutions_found=1, runtime_seconds=0.2, node_expansions=40),
        make_row(experiment_group="multi_solution_25", dataset="le450_25a.col", variant="B5", declared_classes=25, color_limit=25, solution_target=1000, solutions_found=1000, canonical_solutions_found=25, signature_solutions_found=25, runtime_seconds=3.5, node_expansions=450),
    ]
    csv_path.write_text(
        "\n".join(
            [
                ",".join(FIELDNAMES),
                *[",".join(str(row[field]) for field in FIELDNAMES) for row in rows],
            ]
        ),
        encoding="utf-8",
    )

    artifacts = plot_from_csv(csv_path, tmp_path / "figures")
    names = {path.name for path in artifacts}
    assert "correctness_validation.png" in names
    assert "provided_maps_analysis.md" in names
    assert "scaling_runtime.png" in names
    assert "provided_maps_horizontal_analysis.md" in names
    assert "multi_solution_analysis.md" in names
    assert "multi_solution_1000_compare.png" in names
    assert "multi_solution_1000_uniques_compare.png" in names
