from pathlib import Path

from exp3 import run_experiments
from exp3.run_experiments import append_result_row, format_progress, load_existing_results, result_identity


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


def make_row(dataset: str, variant: str) -> dict[str, object]:
    dataset_target = run_experiments.DATASETS[dataset]["max_solutions"]
    return {
        "dataset": dataset,
        "declared_classes": 5,
        "variant": variant,
        "name": variant,
        "success": False,
        "timed_out": True,
        "pruned_by_clique": False,
        "clique_lower_bound": 5,
        "used_colors": 0,
        "node_expansions": 123,
        "backtracks": 456,
        "runtime_seconds": 60.0,
        "overhead_ms_per_node": 1.23,
        "timeout_seconds": 60.0,
        "solutions_found": 0,
        "solution_target": dataset_target,
        "stopped_on_target": False,
    }


def test_append_result_row_creates_csv_and_preserves_rows(tmp_path: Path):
    csv_path = tmp_path / "benchmark_results.csv"
    first = make_row("le450_5a.col", "V0")
    second = make_row("le450_5a.col", "V1")

    append_result_row(csv_path, FIELDNAMES, first)
    append_result_row(csv_path, FIELDNAMES, second)

    rows = load_existing_results(csv_path)
    assert [row["variant"] for row in rows] == ["V0", "V1"]


def test_result_identity_uses_dataset_and_variant():
    row = make_row("le450_15b.col", "V3")
    assert result_identity(row) == ("le450_15b.col", "V3")


def test_load_existing_results_returns_empty_for_missing_file(tmp_path: Path):
    csv_path = tmp_path / "missing.csv"
    assert load_existing_results(csv_path) == []


def test_format_progress_shows_completed_and_total():
    assert format_progress(3, 18) == "[3/18]"


def test_run_all_skips_completed_entries_when_resume_enabled(tmp_path: Path, monkeypatch):
    csv_path = tmp_path / "benchmark_results.csv"
    for dataset in run_experiments.DATASETS:
        for variant in run_experiments.VARIANTS:
            append_result_row(csv_path, FIELDNAMES, make_row(dataset, variant))

    monkeypatch.setattr(run_experiments, "load_dimacs_graph", lambda path: type("G", (), {"num_nodes": 450, "metadata": {"declared_classes": 5}})())
    monkeypatch.setattr(run_experiments, "plot_from_csv", lambda path: [])

    def fail_run_variant(*args, **kwargs):
        raise AssertionError("run_variant_on_file should not be called for completed entries")

    monkeypatch.setattr(run_experiments, "run_variant_on_file", fail_run_variant)

    rows = run_experiments.run_all(timeout_seconds=60.0, resume=True, output_path=csv_path)
    assert len(rows) == len(run_experiments.DATASETS) * len(run_experiments.VARIANTS)
