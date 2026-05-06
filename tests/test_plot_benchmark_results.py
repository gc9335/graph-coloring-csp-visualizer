from pathlib import Path

from exp3.plot_benchmark_results import infer_timeout_seconds, load_rows


def test_infer_timeout_seconds_prefers_csv_value(tmp_path: Path):
    csv_path = tmp_path / "benchmark_results.csv"
    csv_path.write_text(
        "\n".join(
            [
                "dataset,declared_classes,variant,name,success,timed_out,pruned_by_clique,clique_lower_bound,used_colors,node_expansions,backtracks,runtime_seconds,overhead_ms_per_node,timeout_seconds,solutions_found,solution_target,stopped_on_target",
                "le450_5a.col,5,V0,OurBase,False,True,False,5,0,100,100,300.0,1.0,300.0,0,1,False",
                "le450_15b.col,15,V1,OurBase + FC,False,True,False,15,0,200,200,300.0,1.0,300.0,0,1,False",
            ]
        ),
        encoding="utf-8",
    )

    rows = load_rows(csv_path)
    assert infer_timeout_seconds(rows) == 300.0
