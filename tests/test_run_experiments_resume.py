from __future__ import annotations

from pathlib import Path

from exp3 import run_experiments
from exp3.graph_coloring import GraphData
from exp3.run_experiments import append_result_row, format_progress, load_existing_results, result_identity


def make_graph() -> GraphData:
    return GraphData(adj_list=[[1], [0]], metadata={"dataset_name": "tiny", "declared_classes": 2})


def make_row(dataset: str, variant: str, *, experiment_group: str = "provided_maps") -> dict[str, object]:
    return {
        "experiment_group": experiment_group,
        "graph_family": "unit_test",
        "dataset": dataset,
        "variant": variant,
        "name": variant,
        "target_density": "",
        "generator_seed": "",
        "declared_classes": 4,
        "n_vertices": 2,
        "n_edges": 1,
        "density": 1.0,
        "min_degree": 1,
        "avg_degree": 1.0,
        "max_degree": 1,
        "component_count": 1,
        "largest_component": 2,
        "clique_lower_bound": 2,
        "used_colors": 2,
        "success": True,
        "timed_out": False,
        "pruned_by_clique": False,
        "search_status": "success",
        "node_expansions": 1,
        "backtracks": 0,
        "runtime_seconds": 0.01,
        "overhead_ms_per_node": 10.0,
        "first_fail_depth": "",
        "timeout_seconds": 60.0,
        "solutions_found": 1,
        "solution_target": 1,
        "stopped_on_target": True,
        "color_limit": 4,
        "valid_coloring": True,
        "explanation_notes": "unit-test",
    }


def test_append_result_row_creates_csv_and_preserves_rows(tmp_path: Path):
    csv_path = tmp_path / "benchmark_results.csv"
    first = make_row("demo_a", "B0")
    second = make_row("demo_a", "B1")

    append_result_row(csv_path, run_experiments.FIELDNAMES, first)
    append_result_row(csv_path, run_experiments.FIELDNAMES, second)

    rows = load_existing_results(csv_path)
    assert [row["variant"] for row in rows] == ["B0", "B1"]
    assert rows[0]["experiment_group"] == "provided_maps"


def test_result_identity_uses_group_dataset_and_variant():
    row = make_row("demo_b", "B3", experiment_group="correctness")
    assert result_identity(row) == ("correctness", "demo_b", "B3", "1")


def test_load_existing_results_returns_empty_for_missing_file(tmp_path: Path):
    csv_path = tmp_path / "missing.csv"
    assert load_existing_results(csv_path) == []


def test_format_progress_shows_completed_and_total():
    assert format_progress(3, 18) == "[3/18]"


def test_run_all_skips_completed_entries_when_resume_enabled(tmp_path: Path, monkeypatch):
    csv_path = tmp_path / "benchmark_results.csv"
    append_result_row(csv_path, run_experiments.FIELDNAMES, make_row("tiny_validation", "B0", experiment_group="correctness"))
    append_result_row(csv_path, run_experiments.FIELDNAMES, make_row("tiny_validation", "B5", experiment_group="correctness"))

    jobs = [
        run_experiments.ExperimentJob(
            experiment_group="correctness",
            graph_family="small_validation",
            dataset="tiny_validation",
            graph=make_graph(),
            color_limit=2,
            max_solutions=1,
            timeout_seconds=60.0,
        )
    ]
    monkeypatch.setattr(run_experiments, "build_jobs", lambda groups, timeout_seconds: jobs)
    monkeypatch.setattr(run_experiments, "plot_from_csv", lambda path: [])

    def fail_run_variant(*args, **kwargs):
        raise AssertionError("run_variant_on_graph should not be called for completed entries")

    monkeypatch.setattr(run_experiments, "run_variant_on_graph", fail_run_variant)

    rows = run_experiments.run_all(timeout_seconds=60.0, resume=True, output_path=csv_path, groups=["correctness"])
    assert len(rows) == 2
