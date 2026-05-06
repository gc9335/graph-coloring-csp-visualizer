from __future__ import annotations

import csv
from pathlib import Path
import sys

import matplotlib.pyplot as plt
import numpy as np

if __package__ in (None, ""):
    sys.path.append(str(Path(__file__).resolve().parents[1]))


VARIANT_ORDER = ["V0", "V1", "V2", "V3", "V4", "V5"]
DATASET_ORDER = ["le450_5a.col", "le450_15b.col", "le450_25a.col"]
DATASET_LABELS = {
    "le450_5a.col": "le450_5a（5 色）",
    "le450_15b.col": "le450_15b（15 色）",
    "le450_25a.col": "le450_25a（25 色）",
}
VARIANT_LABELS = {
    "V0": "V0\nBase",
    "V1": "V1\n+FC",
    "V2": "V2\n+MRV",
    "V3": "V3\n+LCV",
    "V4": "V4\n+Degree",
    "V5": "V5\n+All",
}
DATASET_COLORS = {
    "le450_5a.col": "#D95F5F",
    "le450_15b.col": "#3E7CB1",
    "le450_25a.col": "#5AA469",
}
TIMEOUT_REFERENCE_SECONDS = 60.0


def configure_fonts() -> None:
    plt.rcParams["font.family"] = "sans-serif"
    plt.rcParams["font.sans-serif"] = [
        "Microsoft YaHei",
        "SimHei",
        "KaiTi",
        "FangSong",
        "DejaVu Sans",
    ]
    plt.rcParams["axes.unicode_minus"] = False


def short_number(value: float) -> str:
    absolute = abs(value)
    if absolute >= 1_000_000:
        return f"{value / 1_000_000:.2f}M"
    if absolute >= 1_000:
        return f"{value / 1_000:.1f}k"
    if float(value).is_integer():
        return str(int(value))
    return f"{value:.2f}"


def load_rows(csv_path: str | Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    with Path(csv_path).open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            rows.append(
                {
                    "dataset": row["dataset"],
                    "variant": row["variant"],
                    "name": row["name"],
                    "success": row["success"] == "True",
                    "timed_out": row["timed_out"] == "True",
                    "pruned_by_clique": row["pruned_by_clique"] == "True",
                    "declared_classes": int(row["declared_classes"]),
                    "clique_lower_bound": int(row["clique_lower_bound"]),
                    "used_colors": int(row["used_colors"]),
                    "node_expansions": int(row["node_expansions"]),
                    "backtracks": int(row["backtracks"]),
                    "runtime_seconds": float(row["runtime_seconds"]),
                    "overhead_ms_per_node": float(row["overhead_ms_per_node"]),
                }
            )
    return rows


def grouped_values(rows: list[dict[str, object]], metric: str) -> dict[str, list[float]]:
    values: dict[str, list[float]] = {}
    for dataset in DATASET_ORDER:
        dataset_rows = [row for row in rows if row["dataset"] == dataset]
        by_variant = {row["variant"]: row for row in dataset_rows}
        values[dataset] = [float(by_variant[variant][metric]) for variant in VARIANT_ORDER]
    return values


def timed_out_flags(rows: list[dict[str, object]], dataset: str) -> list[bool]:
    return [
        next(
            row["timed_out"]
            for row in rows
            if row["dataset"] == dataset and row["variant"] == variant
        )
        for variant in VARIANT_ORDER
    ]


def annotate_bars(ax, bars, values: list[float], timed_out: list[bool], metric: str, log_scale: bool) -> None:
    for bar, value, is_timeout in zip(bars, values, timed_out):
        height = bar.get_height()
        if log_scale and height <= 0:
            continue

        if metric == "runtime_seconds":
            label = "超时" if is_timeout else f"{value:.2f}s"
        elif metric == "overhead_ms_per_node":
            label = f"{value:.2f}"
        else:
            label = short_number(value)

        bar.set_alpha(0.95 if not is_timeout else 0.82)
        if is_timeout:
            bar.set_hatch("///")
            bar.set_edgecolor("#7A1F1F")
            bar.set_linewidth(1.0)

        if log_scale:
            y = height * 1.12
        else:
            upper = ax.get_ylim()[1]
            y = height + upper * 0.012

        ax.text(
            bar.get_x() + bar.get_width() / 2,
            y if height > 0 else 0.05,
            label,
            ha="center",
            va="bottom",
            fontsize=8,
        )


def draw_grouped_bars(ax, rows: list[dict[str, object]], metric: str, title: str, log_scale: bool) -> None:
    x = np.arange(len(VARIANT_ORDER))
    width = 0.24
    values_by_dataset = grouped_values(rows, metric)

    for idx, dataset in enumerate(DATASET_ORDER):
        values = values_by_dataset[dataset]
        timeout_mask = timed_out_flags(rows, dataset)
        offset = (idx - 1) * width
        bars = ax.bar(
            x + offset,
            values,
            width=width,
            color=DATASET_COLORS[dataset],
            edgecolor="black",
            linewidth=0.6,
            label=DATASET_LABELS[dataset],
        )
        annotate_bars(ax, bars, values, timeout_mask, metric, log_scale)

    ax.set_title(title, fontsize=12, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels([VARIANT_LABELS[item] for item in VARIANT_ORDER])
    ax.set_xlabel("实验组")

    if log_scale:
        ax.set_yscale("log")
        ax.text(
            0.98,
            0.96,
            "对数坐标",
            transform=ax.transAxes,
            ha="right",
            va="top",
            fontsize=9,
            color="#555555",
        )

    ax.grid(axis="y", linestyle="--", alpha=0.35)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)

    if metric == "runtime_seconds":
        max_runtime = max(row["runtime_seconds"] for row in rows)
        ax.set_ylim(0, max_runtime * 1.18)
        ax.axhline(
            TIMEOUT_REFERENCE_SECONDS,
            color="#A63D40",
            linestyle="--",
            linewidth=1.2,
            alpha=0.9,
        )
        ax.text(
            0.98,
            TIMEOUT_REFERENCE_SECONDS / ax.get_ylim()[1] + 0.01,
            "60s 超时线",
            transform=ax.transAxes,
            ha="right",
            va="bottom",
            fontsize=9,
            color="#A63D40",
        )


def plot_from_csv(csv_path: str | Path, output_dir: str | Path | None = None) -> list[Path]:
    rows = load_rows(csv_path)
    csv_path = Path(csv_path)
    output_root = Path(output_dir) if output_dir else csv_path.parent / "figures"
    output_root.mkdir(parents=True, exist_ok=True)

    plt.style.use("seaborn-v0_8-whitegrid")
    configure_fonts()

    metric_specs = [
        ("runtime_seconds", "运行时间 / s", False),
        ("node_expansions", "搜索节点数", True),
        ("backtracks", "回溯次数", True),
        ("overhead_ms_per_node", "单节点平均开销 / ms", False),
    ]
    saved_paths: list[Path] = []

    fig, axes = plt.subplots(2, 2, figsize=(16, 10.8))
    fig.suptitle("地图着色回溯算法实验对比", fontsize=18, fontweight="bold", y=0.98)

    for ax, (metric, title, log_scale) in zip(axes.flat, metric_specs):
        draw_grouped_bars(ax, rows, metric, title, log_scale)

    axes[0, 0].legend(loc="upper left", fontsize=9, frameon=True)
    fig.text(
        0.5,
        0.015,
        "说明：斜线柱表示该实验组在对应数据集上达到时间上限仍未完成搜索。",
        ha="center",
        fontsize=10,
        color="#444444",
    )
    fig.tight_layout(rect=(0.02, 0.04, 1, 0.95))

    summary_png = output_root / "benchmark_report_bars.png"
    summary_svg = output_root / "benchmark_report_bars.svg"
    fig.savefig(summary_png, dpi=300, bbox_inches="tight")
    fig.savefig(summary_svg, bbox_inches="tight")
    saved_paths.extend([summary_png, summary_svg])
    plt.close(fig)

    for metric, title, log_scale in metric_specs[:3]:
        fig, ax = plt.subplots(figsize=(12, 6))
        draw_grouped_bars(ax, rows, metric, f"{title}对比", log_scale)
        ax.legend(loc="upper right", fontsize=9, frameon=True)
        fig.tight_layout()

        output_path = output_root / f"{metric}_bars.png"
        fig.savefig(output_path, dpi=300, bbox_inches="tight")
        saved_paths.append(output_path)
        plt.close(fig)

    return saved_paths


if __name__ == "__main__":
    csv_arg = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent / "benchmark_results.csv"
    output_arg = Path(sys.argv[2]) if len(sys.argv) > 2 else None
    generated = plot_from_csv(csv_arg, output_arg)
    for path in generated:
        print(f"Saved {path}")
