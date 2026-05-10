from pathlib import Path

from exp3 import run_experiments
from exp3.run_experiments import append_result_row, format_progress, load_existing_results, result_identity


def make_row(dataset: str, variant: str) -> dict[str, object]:
    dataset_target = run_experiments.DATASETS[dataset]["max_solutions"]
    return {
        "experiment_group": "provided_maps",
        "graph_family": "dimacs_leighton",
        "dataset": dataset,
        "target_density": "",
        "generator_seed": "",
        "declared_classes": 5,
        "variant": variant,
        "name": variant,
        "n_vertices": 450,
        "n_edges": 5714,
        "density": 0.05656,
        "min_degree": 13,
        "avg_degree": 25.395556,
        "max_degree": 42,
        "component_count": 1,
        "largest_component": 450,
        "success": False,
        "timed_out": True,
        "pruned_by_clique": False,
        "clique_lower_bound": 5,
        "used_colors": 0,
        "node_expansions": 123,
        "backtracks": 456,
        "runtime_seconds": 60.0,
        "overhead_ms_per_node": 1.23,
        "first_fail_depth": 31,
        "timeout_seconds": 60.0,
        "solutions_found": 0,
        "solution_target": dataset_target,
        "canonical_solutions_found": 0,
        "signature_solutions_found": 0,
        "stopped_on_target": False,
        "color_limit": 5,
        "valid_coloring": False,
        "search_status": "timeout",
        "explanation_notes": "component_strategy=single-search",
    }


def test_append_result_row_creates_csv_and_preserves_rows(tmp_path: Path):
    csv_path = tmp_path / "benchmark_results.csv"
    first = make_row("le450_5a.col", "B0")
    second = make_row("le450_5a.col", "B1")

    append_result_row(csv_path, run_experiments.FIELDNAMES, first)
    append_result_row(csv_path, run_experiments.FIELDNAMES, second)

    rows = load_existing_results(csv_path)
    assert [row["variant"] for row in rows] == ["B0", "B1"]


def test_result_identity_uses_dataset_and_variant():
    row = make_row("le450_15b.col", "B3")
    assert result_identity(row) == ("provided_maps", "le450_15b.col", "B3", "1")


def test_load_existing_results_returns_empty_for_missing_file(tmp_path: Path):
    csv_path = tmp_path / "missing.csv"
    assert load_existing_results(csv_path) == []


def test_format_progress_shows_completed_and_total():
    assert format_progress(3, 18) == "[3/18]"


def test_run_all_skips_completed_entries_when_resume_enabled(tmp_path: Path, monkeypatch):
    csv_path = tmp_path / "benchmark_results.csv"
    groups = ["provided_maps"]
    for dataset in run_experiments.DATASETS:
        for variant in run_experiments.VARIANTS:
            append_result_row(csv_path, run_experiments.FIELDNAMES, make_row(dataset, variant))

    monkeypatch.setattr(run_experiments, "load_dimacs_graph", lambda path: type("G", (), {"num_nodes": 450, "metadata": {"declared_classes": 5}})())
    monkeypatch.setattr(run_experiments, "plot_from_csv", lambda path: [])

    def fail_run_variant(*args, **kwargs):
        raise AssertionError("run_variant_on_graph should not be called for completed entries")

    monkeypatch.setattr(run_experiments, "run_variant_on_graph", fail_run_variant)

    rows = run_experiments.run_all(timeout_seconds=60.0, resume=True, output_path=csv_path, groups=groups)
    assert len(rows) == len(run_experiments.DATASETS) * len(run_experiments.VARIANTS)
