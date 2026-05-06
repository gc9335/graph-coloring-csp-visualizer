from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from exp3.graph_coloring import VARIANTS, run_variant_on_file


DATASETS = {
    "le450_5a.col": 5,
    "le450_15b.col": 15,
    "le450_25a.col": 25,
}


if __name__ == "__main__":
    timeout = float(sys.argv[1]) if len(sys.argv) > 1 else 60.0
    base_dir = Path(__file__).resolve().parent
    for dataset_name, color_limit in DATASETS.items():
        _, result = run_variant_on_file(base_dir / dataset_name, color_limit, VARIANTS["V5"], timeout_seconds=timeout)
        print(
            f"{dataset_name} | success={result.success} | "
            f"clique_lb={result.clique_lower_bound} | "
            f"used={result.used_colors} | "
            f"nodes={result.node_expansions} | "
            f"backtracks={result.backtracks} | "
            f"time={result.runtime_seconds:.4f}s"
        )
