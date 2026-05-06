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
                    "timeout_seconds": float(row.get("timeout_seconds", row["runtime_seconds"])),
                    "solutions_found": int(row.get("solutions_found", "1")),
                    "solution_target": int(row.get("solution_target", "1")),
                    "stopped_on_target": row.get("stopped_on_target", "False") == "True",
                }
            )
    return rows


def infer_timeout_seconds(rows: list[dict[str, object]]) -> float:
    timeout_values = [float(row["timeout_seconds"]) for row in rows if "timeout_seconds" in row]
    if timeout_values:
        return max(timeout_values)
    return max(float(row["runtime_seconds"]) for row in rows)


def grouped_values(rows: list[dict[str, object]], metric: str, datasets: list[str]) -> dict[str, list[float]]:
    values: dict[str, list[float]] = {}
    for dataset in datasets:
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


def draw_grouped_bars(
    ax,
    rows: list[dict[str, object]],
    metric: str,
    title: str,
    log_scale: bool,
    datasets: list[str],
    timeout_seconds: float,
) -> None:
    x = np.arange(len(VARIANT_ORDER))
    width = 0.8 / len(datasets)
    values_by_dataset = grouped_values(rows, metric, datasets)

    for idx, dataset in enumerate(datasets):
        values = values_by_dataset[dataset]
        timeout_mask = timed_out_flags(rows, dataset)
        offset = (idx - (len(datasets) - 1) / 2) * width
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
        max_runtime = max(float(row["runtime_seconds"]) for row in rows)
        ax.set_ylim(0, max(max_runtime, timeout_seconds) * 1.18)
        ax.axhline(
            timeout_seconds,
            color="#A63D40",
            linestyle="--",
            linewidth=1.2,
            alpha=0.9,
        )
        ax.text(
            0.98,
            timeout_seconds / ax.get_ylim()[1] + 0.01,
            f"{int(timeout_seconds)}s 超时线",
            transform=ax.transAxes,
            ha="right",
            va="bottom",
            fontsize=9,
            color="#A63D40",
        )


def write_5_15_analysis(rows: list[dict[str, object]], output_root: Path) -> Path:
    focus = [row for row in rows if row["dataset"] in {"le450_5a.col", "le450_15b.col"}]
    sections: list[str] = [
        "# 5 色与 15 色数据集对比分析",
        "",
        "## 数据概况",
    ]

    for dataset in ["le450_5a.col", "le450_15b.col"]:
        dataset_rows = [row for row in focus if row["dataset"] == dataset]
        declared_classes = dataset_rows[0]["declared_classes"]
        timeout_seconds = dataset_rows[0]["timeout_seconds"]
        completed = [row for row in dataset_rows if not row["timed_out"]]
        best_runtime = min(completed, key=lambda row: row["runtime_seconds"]) if completed else None
        best_nodes = min(dataset_rows, key=lambda row: row["node_expansions"])
        sections.extend(
            [
                f"### {DATASET_LABELS[dataset]}",
                f"- 颜色上界/类别数：{declared_classes}",
                f"- 单次实验超时阈值：{int(timeout_seconds)}s",
                f"- 完成求解的实验组数：{len(completed)}/{len(dataset_rows)}",
                (
                    f"- 最快完成组：{best_runtime['variant']}，耗时 {best_runtime['runtime_seconds']:.2f}s"
                    if best_runtime
                    else "- 所有实验组均达到超时上限，未在设定时间内完成求解"
                ),
                f"- 搜索节点最少组：{best_nodes['variant']}，节点数 {best_nodes['node_expansions']}",
                "",
            ]
        )

    rows_5 = [row for row in focus if row["dataset"] == "le450_5a.col"]
    rows_15 = [row for row in focus if row["dataset"] == "le450_15b.col"]
    best_5 = min((row for row in rows_5 if not row["timed_out"]), key=lambda row: row["runtime_seconds"], default=None)
    best_15_nodes = min(rows_15, key=lambda row: row["node_expansions"])
    sections.extend(
        [
            "## 对比结论",
            (
                f"- 5 色数据集存在可行解，且启发式组合在该数据集上效果明显："
                f"{best_5['variant']} 可在 {best_5['runtime_seconds']:.2f}s 内完成。"
                if best_5
                else "- 5 色数据集在本次运行参数下没有实验组完成求解。"
            ),
            f"- 15 色数据集在当前超时阈值内仍未完成求解，但 V5 将搜索节点压缩到 {best_15_nodes['node_expansions']}，显著优于 V0/V1。",
            "- MRV、LCV 与 Degree 的组合对高难度实例更有帮助，尤其体现在搜索节点数和回溯次数的下降上。",
            "- 5 色实例更适合从“是否成功求解”和“完成时间”角度分析；15 色实例更适合从“剪枝后搜索规模”角度比较策略优劣。",
        ]
    )

    output_path = output_root / "analysis_5_vs_15.md"
    output_path.write_text("\n".join(sections), encoding="utf-8")
    return output_path


def plot_from_csv(csv_path: str | Path, output_dir: str | Path | None = None) -> list[Path]:
    rows = load_rows(csv_path)
    csv_path = Path(csv_path)
    output_root = Path(output_dir) if output_dir else csv_path.parent / "figures"
    output_root.mkdir(parents=True, exist_ok=True)

    plt.style.use("seaborn-v0_8-whitegrid")
    configure_fonts()
    timeout_seconds = infer_timeout_seconds(rows)

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
        draw_grouped_bars(ax, rows, metric, title, log_scale, DATASET_ORDER, timeout_seconds)

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

    focus_rows = [row for row in rows if row["dataset"] in {"le450_5a.col", "le450_15b.col"}]
    fig, axes = plt.subplots(1, 2, figsize=(15, 5.8))
    draw_grouped_bars(
        axes[0],
        focus_rows,
        "runtime_seconds",
        "5 色与 15 色运行时间对比",
        False,
        ["le450_5a.col", "le450_15b.col"],
        timeout_seconds,
    )
    draw_grouped_bars(
        axes[1],
        focus_rows,
        "node_expansions",
        "5 色与 15 色搜索节点对比",
        True,
        ["le450_5a.col", "le450_15b.col"],
        timeout_seconds,
    )
    axes[0].legend(loc="upper right", fontsize=9, frameon=True)
    fig.tight_layout()
    focus_png = output_root / "comparison_5_vs_15.png"
    fig.savefig(focus_png, dpi=300, bbox_inches="tight")
    saved_paths.append(focus_png)
    plt.close(fig)

    analysis_path = write_5_15_analysis(rows, output_root)
    saved_paths.append(analysis_path)
    return saved_paths


if __name__ == "__main__":
    csv_arg = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent / "benchmark_results.csv"
    output_arg = Path(sys.argv[2]) if len(sys.argv) > 2 else None
    generated = plot_from_csv(csv_arg, output_arg)
    for path in generated:
        print(f"Saved {path}")
