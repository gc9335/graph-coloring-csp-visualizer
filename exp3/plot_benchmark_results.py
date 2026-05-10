from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path
import re
import sys

import matplotlib.pyplot as plt
import numpy as np

if __package__ in (None, ""):
    sys.path.append(str(Path(__file__).resolve().parents[1]))


VARIANT_ORDER = [f"B{i}" for i in range(6)]
VARIANT_LABELS = {
    "B0": "B0\nBase",
    "B1": "B1\n+FC",
    "B2": "B2\n+MRV",
    "B3": "B3\n+Degree",
    "B4": "B4\n+LCV",
    "B5": "B5\n+Struct",
}
PROVIDED_MAP_ORDER = ["le450_5a.col", "le450_15b.col", "le450_25a.col"]
PROVIDED_MAP_LABELS = {
    "le450_5a.col": "le450_5a (5 colors)",
    "le450_15b.col": "le450_15b (15 colors)",
    "le450_25a.col": "le450_25a (25 colors)",
}
DEFAULT_COLORS = ["#C84C31", "#356D9E", "#5C9E6B", "#7A5EA8", "#D2872C", "#4E9A9A"]
CSV_FIELDNAMES = [
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
    "canonical_solutions_found",
    "signature_solutions_found",
    "stopped_on_target",
    "color_limit",
    "valid_coloring",
    "explanation_notes",
]
COMPAT_CSV_FIELDNAMES = [field for field in CSV_FIELDNAMES if field not in {"canonical_solutions_found", "signature_solutions_found"}]
LEGACY_CSV_FIELDNAMES = [
    field
    for field in CSV_FIELDNAMES
    if field not in {"target_density", "generator_seed", "canonical_solutions_found", "signature_solutions_found"}
]


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


def _to_bool(value: object) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


def _to_int(value: object, default: int = 0) -> int:
    text = str(value).strip()
    if not text:
        return default
    return int(float(text))


def _to_float(value: object, default: float = 0.0) -> float:
    text = str(value).strip()
    if not text:
        return default
    return float(text)


def _infer_target_density(dataset: str, row: dict[str, str]) -> float:
    explicit = row.get("target_density", "")
    if str(explicit).strip():
        return _to_float(explicit, _to_float(row.get("density", 0.0)))
    match = re.search(r"_p(?P<density>\d+(?:\.\d+)?)_s", dataset)
    if match:
        return float(match.group("density"))
    return _to_float(row.get("density", 0.0))


def _infer_generator_seed(dataset: str, row: dict[str, str]) -> int:
    explicit = row.get("generator_seed", "")
    if str(explicit).strip():
        return _to_int(explicit, 0)
    match = re.search(r"_s(?P<seed>\d+)$", dataset)
    if match:
        return int(match.group("seed"))
    return 0


def load_rows(csv_path: str | Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    with Path(csv_path).open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader, None)
        if header is None:
            return []
        for values in reader:
            if not values:
                continue
            if len(values) == len(CSV_FIELDNAMES):
                row = {field: values[index] for index, field in enumerate(CSV_FIELDNAMES)}
            elif len(values) == len(COMPAT_CSV_FIELDNAMES):
                compat = {field: values[index] for index, field in enumerate(COMPAT_CSV_FIELDNAMES)}
                row = {}
                for field in CSV_FIELDNAMES:
                    if field in {"canonical_solutions_found", "signature_solutions_found"}:
                        row[field] = compat.get("solutions_found", "")
                    else:
                        row[field] = compat.get(field, "")
            elif len(values) == len(LEGACY_CSV_FIELDNAMES):
                legacy = {field: values[index] for index, field in enumerate(LEGACY_CSV_FIELDNAMES)}
                row = {}
                for field in CSV_FIELDNAMES:
                    if field in {"target_density", "generator_seed"}:
                        row[field] = ""
                    elif field in {"canonical_solutions_found", "signature_solutions_found"}:
                        row[field] = legacy.get("solutions_found", "")
                    else:
                        row[field] = legacy.get(field, "")
            else:
                padded = values + [""] * max(0, len(CSV_FIELDNAMES) - len(values))
                row = {field: padded[index] if index < len(padded) else "" for index, field in enumerate(CSV_FIELDNAMES)}

            dataset = row.get("dataset", "")
            rows.append(
                {
                    "experiment_group": row.get("experiment_group", ""),
                    "graph_family": row.get("graph_family", ""),
                    "dataset": dataset,
                    "variant": row.get("variant", ""),
                    "name": row.get("name", ""),
                    "target_density": _infer_target_density(dataset, row),
                    "generator_seed": _infer_generator_seed(dataset, row),
                    "declared_classes": _to_int(row.get("declared_classes", 0)),
                    "n_vertices": _to_int(row.get("n_vertices", 0)),
                    "n_edges": _to_int(row.get("n_edges", 0)),
                    "density": _to_float(row.get("density", 0.0)),
                    "min_degree": _to_int(row.get("min_degree", 0)),
                    "avg_degree": _to_float(row.get("avg_degree", 0.0)),
                    "max_degree": _to_int(row.get("max_degree", 0)),
                    "component_count": _to_int(row.get("component_count", 0)),
                    "largest_component": _to_int(row.get("largest_component", 0)),
                    "clique_lower_bound": _to_int(row.get("clique_lower_bound", 0)),
                    "used_colors": _to_int(row.get("used_colors", 0)),
                    "success": _to_bool(row.get("success", False)),
                    "timed_out": _to_bool(row.get("timed_out", False)),
                    "pruned_by_clique": _to_bool(row.get("pruned_by_clique", False)),
                    "search_status": row.get("search_status", ""),
                    "node_expansions": _to_int(row.get("node_expansions", 0)),
                    "backtracks": _to_int(row.get("backtracks", 0)),
                    "runtime_seconds": _to_float(row.get("runtime_seconds", 0.0)),
                    "overhead_ms_per_node": _to_float(row.get("overhead_ms_per_node", 0.0)),
                    "first_fail_depth": _to_int(row.get("first_fail_depth", 0)),
                    "timeout_seconds": _to_float(row.get("timeout_seconds", 0.0)),
                    "solutions_found": _to_int(row.get("solutions_found", 0)),
                    "solution_target": _to_int(row.get("solution_target", 0)),
                    "canonical_solutions_found": _to_int(
                        row.get("canonical_solutions_found", row.get("solutions_found", 0))
                    ),
                    "signature_solutions_found": _to_int(
                        row.get(
                            "signature_solutions_found",
                            row.get("canonical_solutions_found", row.get("solutions_found", 0)),
                        )
                    ),
                    "stopped_on_target": _to_bool(row.get("stopped_on_target", False)),
                    "color_limit": _to_int(row.get("color_limit", row.get("declared_classes", 0))),
                    "valid_coloring": _to_bool(row.get("valid_coloring", False)),
                    "explanation_notes": row.get("explanation_notes", ""),
                }
            )
    return rows


def infer_timeout_seconds(rows: list[dict[str, object]]) -> float:
    values = [float(row["timeout_seconds"]) for row in rows if float(row["timeout_seconds"]) > 0]
    return max(values) if values else 0.0


def _rows_by_group(rows: list[dict[str, object]], group: str) -> list[dict[str, object]]:
    return [row for row in rows if row["experiment_group"] == group]


def _rows_by_dataset(rows: list[dict[str, object]], dataset: str) -> list[dict[str, object]]:
    return [row for row in rows if row["dataset"] == dataset]


def _variant_sorted(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    order = {variant_id: index for index, variant_id in enumerate(VARIANT_ORDER)}
    return sorted(rows, key=lambda row: order.get(str(row["variant"]), 999))


def _short_number(value: float) -> str:
    if abs(value) >= 1_000_000:
        return f"{value / 1_000_000:.2f}M"
    if abs(value) >= 1_000:
        return f"{value / 1_000:.1f}k"
    if float(value).is_integer():
        return str(int(value))
    return f"{value:.2f}"


def _annotate_bars(ax, bars, values: list[float], timed_out_flags: list[bool], metric: str) -> None:
    for bar, value, timed_out in zip(bars, values, timed_out_flags):
        text = f"{value:.2f}s" if metric == "runtime_seconds" else _short_number(value)
        if timed_out:
            bar.set_hatch("///")
            bar.set_alpha(0.82)
            text = "timeout"
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + max(0.01, ax.get_ylim()[1] * 0.01),
            text,
            ha="center",
            va="bottom",
            fontsize=8,
        )


def _plot_correctness(rows: list[dict[str, object]], output_root: Path) -> list[Path]:
    if not rows:
        return []
    rows = _variant_sorted(rows)
    labels = [VARIANT_LABELS.get(str(row["variant"]), str(row["variant"])) for row in rows]
    values = [1 if row["valid_coloring"] else 0 for row in rows]
    runtimes = [float(row["runtime_seconds"]) for row in rows]

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.6))
    axes[0].bar(labels, values, color="#5C9E6B", edgecolor="black")
    axes[0].set_title("Correctness Validation")
    axes[0].set_ylabel("Valid Coloring (1=yes)")
    axes[0].set_ylim(0, 1.2)
    axes[0].grid(axis="y", linestyle="--", alpha=0.3)

    axes[1].bar(labels, runtimes, color="#356D9E", edgecolor="black")
    axes[1].set_title("Validation Runtime")
    axes[1].set_ylabel("Seconds")
    axes[1].grid(axis="y", linestyle="--", alpha=0.3)

    fig.tight_layout()
    path = output_root / "correctness_validation.png"
    fig.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(fig)
    return [path]


def _plot_grouped_metric(rows: list[dict[str, object]], metric: str, title: str, output_path: Path) -> Path | None:
    if not rows:
        return None
    datasets = [dataset for dataset in PROVIDED_MAP_ORDER if any(row["dataset"] == dataset for row in rows)]
    if not datasets:
        return None

    fig, ax = plt.subplots(figsize=(13.5, 5.4))
    x = np.arange(len(VARIANT_ORDER))
    width = 0.8 / max(1, len(datasets))
    timeout_seconds = infer_timeout_seconds(rows)

    for dataset_index, dataset in enumerate(datasets):
        dataset_rows = {str(row["variant"]): row for row in _rows_by_dataset(rows, dataset)}
        values = [float(dataset_rows.get(variant_id, {}).get(metric, 0.0)) for variant_id in VARIANT_ORDER]
        timed_out_flags = [bool(dataset_rows.get(variant_id, {}).get("timed_out", False)) for variant_id in VARIANT_ORDER]
        bars = ax.bar(
            x + (dataset_index - (len(datasets) - 1) / 2) * width,
            values,
            width=width,
            label=PROVIDED_MAP_LABELS.get(dataset, dataset),
            color=DEFAULT_COLORS[dataset_index % len(DEFAULT_COLORS)],
            edgecolor="black",
            linewidth=0.6,
        )
        _annotate_bars(ax, bars, values, timed_out_flags, metric)

    ax.set_xticks(x)
    ax.set_xticklabels([VARIANT_LABELS.get(variant_id, variant_id) for variant_id in VARIANT_ORDER])
    ax.set_title(title)
    ax.grid(axis="y", linestyle="--", alpha=0.3)
    if metric == "runtime_seconds" and timeout_seconds > 0:
        ax.axhline(timeout_seconds, linestyle="--", color="#A63D40", linewidth=1.2, alpha=0.9)
    ax.legend(loc="upper left", fontsize=9)
    fig.tight_layout()
    fig.savefig(output_path, dpi=240, bbox_inches="tight")
    plt.close(fig)
    return output_path


def _plot_horizontal_by_dataset(rows: list[dict[str, object]], metric: str, title: str, output_path: Path) -> Path | None:
    if not rows:
        return None
    datasets = [dataset for dataset in PROVIDED_MAP_ORDER if any(row["dataset"] == dataset for row in rows)]
    if not datasets:
        return None

    fig, axes = plt.subplots(1, len(datasets), figsize=(5.4 * len(datasets), 5.1), squeeze=False, sharey=True)
    for dataset_index, dataset in enumerate(datasets):
        ax = axes[0, dataset_index]
        dataset_rows = {str(row["variant"]): row for row in _rows_by_dataset(rows, dataset)}
        values = [float(dataset_rows.get(variant_id, {}).get(metric, 0.0)) for variant_id in VARIANT_ORDER]
        timed_out_flags = [bool(dataset_rows.get(variant_id, {}).get("timed_out", False)) for variant_id in VARIANT_ORDER]
        bars = ax.bar(
            [VARIANT_LABELS.get(variant_id, variant_id) for variant_id in VARIANT_ORDER],
            values,
            color=DEFAULT_COLORS[: len(VARIANT_ORDER)],
            edgecolor="black",
            linewidth=0.6,
        )
        _annotate_bars(ax, bars, values, timed_out_flags, metric)
        ax.set_title(PROVIDED_MAP_LABELS.get(dataset, dataset))
        ax.grid(axis="y", linestyle="--", alpha=0.3)
        ax.tick_params(axis="x", labelrotation=0)
        if metric == "runtime_seconds":
            timeout_seconds = max((float(row["timeout_seconds"]) for row in dataset_rows.values()), default=0.0)
            if timeout_seconds > 0:
                ax.axhline(timeout_seconds, linestyle="--", color="#A63D40", linewidth=1.1, alpha=0.85)
        if dataset_index == 0:
            ax.set_ylabel("Seconds" if metric == "runtime_seconds" else "Node Expansions")
    fig.suptitle(title, fontsize=14, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(output_path, dpi=240, bbox_inches="tight")
    plt.close(fig)
    return output_path


def _plot_scaling(rows: list[dict[str, object]], output_root: Path) -> list[Path]:
    if not rows:
        return []
    saved: list[Path] = []
    rows_by_density: dict[float, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        rows_by_density[round(float(row.get("target_density", row["density"])), 4)].append(row)

    for metric, filename, ylabel in [
        ("runtime_seconds", "scaling_runtime.png", "Runtime (s)"),
        ("node_expansions", "scaling_node_expansions.png", "Node Expansions"),
    ]:
        density_levels = sorted(rows_by_density)
        fig, axes = plt.subplots(
            1,
            len(density_levels),
            figsize=(6.2 * len(density_levels), 5.2),
            squeeze=False,
            sharey=True,
        )
        for density_index, density in enumerate(density_levels):
            ax = axes[0, density_index]
            density_rows = rows_by_density[density]
            for variant_id in VARIANT_ORDER:
                variant_rows = [row for row in density_rows if row["variant"] == variant_id]
                if not variant_rows:
                    continue
                points: dict[int, list[float]] = defaultdict(list)
                for row in variant_rows:
                    points[int(row["n_vertices"])].append(float(row[metric]))
                xs = sorted(points)
                ys = [sum(points[x]) / len(points[x]) for x in xs]
                ax.plot(
                    xs,
                    ys,
                    marker="o",
                    linewidth=1.8,
                    label=variant_id,
                    color=DEFAULT_COLORS[VARIANT_ORDER.index(variant_id) % len(DEFAULT_COLORS)],
                    alpha=0.9,
                )
            ax.set_title(f"Target density = {density:.2f}")
            ax.set_xlabel("Number of Vertices")
            if density_index == 0:
                ax.set_ylabel(ylabel)
            ax.grid(True, linestyle="--", alpha=0.3)
            if metric == "node_expansions":
                ax.ticklabel_format(axis="y", style="sci", scilimits=(0, 0))
            ax.legend(fontsize=8, ncol=2)
        fig.suptitle(f"Scaling Study: {ylabel}", fontsize=14, fontweight="bold")
        fig.tight_layout(rect=(0, 0, 1, 0.95))
        path = output_root / filename
        fig.savefig(path, dpi=240, bbox_inches="tight")
        saved.append(path)
        plt.close(fig)
    return saved


def _plot_multi_solution(rows: list[dict[str, object]], output_root: Path) -> list[Path]:
    if not rows:
        return []
    saved: list[Path] = []
    grouped: dict[str, dict[int, dict[str, object]]] = defaultdict(dict)
    for row in rows:
        grouped[str(row["variant"])][int(row["solution_target"])] = row

    for metric, filename, ylabel in [
        ("runtime_seconds", "multi_solution_runtime.png", "Runtime (s)"),
        ("node_expansions", "multi_solution_node_expansions.png", "Node Expansions"),
    ]:
        fig, ax = plt.subplots(figsize=(10.5, 5.4))
        for variant_index, variant_id in enumerate(VARIANT_ORDER):
            variant_rows = grouped.get(variant_id, {})
            if not variant_rows:
                continue
            xs = sorted(variant_rows)
            ys = [float(variant_rows[target][metric]) for target in xs]
            ax.plot(
                xs,
                ys,
                marker="o",
                linewidth=1.9,
                label=variant_id,
                color=DEFAULT_COLORS[variant_index % len(DEFAULT_COLORS)],
            )
        ax.set_title(f"25-color Multi-solution Study: {ylabel}")
        ax.set_xlabel("Requested Solution Count")
        ax.set_ylabel(ylabel)
        ax.set_xscale("log")
        if metric == "node_expansions":
            ax.ticklabel_format(axis="y", style="sci", scilimits=(0, 0))
        ax.grid(True, linestyle="--", alpha=0.3)
        ax.legend(ncol=3, fontsize=9)
        fig.tight_layout()
        path = output_root / filename
        fig.savefig(path, dpi=240, bbox_inches="tight")
        saved.append(path)
        plt.close(fig)

    rows_1000 = [row for row in rows if int(row["solution_target"]) == 1000]
    if rows_1000:
        fig, axes = plt.subplots(1, 2, figsize=(12, 4.8))
        rows_1000 = _variant_sorted(rows_1000)
        labels = [VARIANT_LABELS.get(str(row["variant"]), str(row["variant"])) for row in rows_1000]
        runtime_values = [float(row["runtime_seconds"]) for row in rows_1000]
        node_values = [float(row["node_expansions"]) for row in rows_1000]
        axes[0].bar(labels, runtime_values, color=DEFAULT_COLORS[: len(labels)], edgecolor="black", linewidth=0.6)
        axes[0].set_title("1000 Solutions Runtime")
        axes[0].set_ylabel("Seconds")
        axes[0].grid(axis="y", linestyle="--", alpha=0.3)
        axes[1].bar(labels, node_values, color=DEFAULT_COLORS[: len(labels)], edgecolor="black", linewidth=0.6)
        axes[1].set_title("1000 Solutions Node Expansions")
        axes[1].ticklabel_format(axis="y", style="sci", scilimits=(0, 0))
        axes[1].grid(axis="y", linestyle="--", alpha=0.3)
        fig.tight_layout()
        compare_path = output_root / "multi_solution_1000_compare.png"
        fig.savefig(compare_path, dpi=240, bbox_inches="tight")
        saved.append(compare_path)
        plt.close(fig)

        fig, ax = plt.subplots(figsize=(12, 5.0))
        x_positions = np.arange(len(rows_1000))
        width = 0.24
        raw_values = [float(row["solutions_found"]) for row in rows_1000]
        canonical_values = [float(row["canonical_solutions_found"]) for row in rows_1000]
        signature_values = [float(row["signature_solutions_found"]) for row in rows_1000]
        ax.bar(x_positions - width, raw_values, width=width, label="Raw", color="#C84C31", edgecolor="black", linewidth=0.6)
        ax.bar(
            x_positions,
            canonical_values,
            width=width,
            label="Canonical Colors",
            color="#5C9E6B",
            edgecolor="black",
            linewidth=0.6,
        )
        ax.bar(
            x_positions + width,
            signature_values,
            width=width,
            label="Canonical + Signature",
            color="#356D9E",
            edgecolor="black",
            linewidth=0.6,
        )
        ax.set_xticks(x_positions, labels)
        ax.set_title("1000 Solutions: Raw vs Deduplicated Counts")
        ax.set_ylabel("Solutions Count")
        ax.grid(axis="y", linestyle="--", alpha=0.3)
        ax.legend()
        fig.tight_layout()
        unique_compare_path = output_root / "multi_solution_1000_uniques_compare.png"
        fig.savefig(unique_compare_path, dpi=240, bbox_inches="tight")
        saved.append(unique_compare_path)
        plt.close(fig)
    return saved


def _explanation_line(dataset_rows: list[dict[str, object]]) -> str:
    sample = dataset_rows[0]
    dataset = str(sample["dataset"])
    classes = int(sample["declared_classes"])
    clique = max(int(row["clique_lower_bound"]) for row in dataset_rows)
    density = float(sample["density"])
    max_degree = int(sample["max_degree"])
    avg_degree = float(sample["avg_degree"])
    best_row = min(dataset_rows, key=lambda row: float(row["runtime_seconds"]) if not row["timed_out"] else float("inf"))
    best_status = (
        f"best variant {best_row['variant']} solved in {best_row['runtime_seconds']:.2f}s"
        if not best_row["timed_out"]
        else "all variants hit the timeout limit"
    )
    return (
        f"- `{dataset}` needs more than four colors because its target class count is {classes} "
        f"and the observed clique lower bound reaches {clique}. "
        f"The graph is also structurally dense enough to be difficult: density={density:.4f}, "
        f"avg_degree={avg_degree:.2f}, max_degree={max_degree}. In this run, {best_status}."
    )


def write_provided_maps_analysis(rows: list[dict[str, object]], output_root: Path) -> Path:
    sections = [
        "# 附件地图数据超过四色的结构性解释",
        "",
        "这些实例并不是普通的小型平面地图，而是带有较强团结构和较高局部连接度的图。",
        "",
    ]
    for dataset in PROVIDED_MAP_ORDER:
        dataset_rows = [row for row in rows if row["dataset"] == dataset]
        if not dataset_rows:
            continue
        sections.append(_explanation_line(dataset_rows))
    path = output_root / "provided_maps_analysis.md"
    path.write_text("\n".join(sections), encoding="utf-8")
    return path


def write_horizontal_comparison_analysis(rows: list[dict[str, object]], output_root: Path) -> Path:
    sections = [
        "# 三组附件地图的横向算法对比",
        "",
        "以下比较均是在同一颜色上限下，对 B0-B5 六种回溯增强算法做横向对比。",
        "",
    ]
    for dataset in PROVIDED_MAP_ORDER:
        dataset_rows = _variant_sorted(_rows_by_dataset(rows, dataset))
        if not dataset_rows:
            continue
        best_runtime_row = min(
            (row for row in dataset_rows if not row["timed_out"]),
            key=lambda row: float(row["runtime_seconds"]),
            default=None,
        )
        best_nodes_row = min(dataset_rows, key=lambda row: float(row["node_expansions"]))
        sections.append(f"## {PROVIDED_MAP_LABELS.get(dataset, dataset)}")
        if best_runtime_row is None:
            sections.append("- 在当前超时阈值内没有算法完成求解，因此更适合比较剪枝后的搜索规模。")
        else:
            sections.append(
                f"- 最快完成算法是 `{best_runtime_row['variant']}`，耗时 {best_runtime_row['runtime_seconds']:.2f}s。"
            )
        sections.append(
            f"- 搜索节点最少的算法是 `{best_nodes_row['variant']}`，节点扩展数为 {int(best_nodes_row['node_expansions'])}。"
        )
        if dataset == "le450_5a.col":
            sections.append("- 5 色实例已经接近可行性边界，LCV 带来的搜索收缩最明显。")
        elif dataset == "le450_15b.col":
            sections.append("- 15 色实例在超时下更适合看节点扩展与回溯下降，MRV + Degree + LCV 的组合优势最明显。")
        elif dataset == "le450_25a.col":
            sections.append("- 25 色实例可行解很多，算法差异主要体现在找到可行解的额外调度开销，而不是是否能解出。")
        sections.append("")
    path = output_root / "provided_maps_horizontal_analysis.md"
    path.write_text("\n".join(sections), encoding="utf-8")
    return path


def write_multi_solution_analysis(rows: list[dict[str, object]], output_root: Path) -> Path:
    sections = [
        "# 25 色实例多解效率分析",
        "",
        "该模块在 `le450_25a.col` 上请求多个可行解，观察目标解个数增长时的时间与搜索规模变化。",
        "",
    ]
    by_target: dict[int, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        by_target[int(row["solution_target"])].append(row)

    for target in sorted(by_target):
        target_rows = _variant_sorted(by_target[target])
        fastest = min(target_rows, key=lambda row: float(row["runtime_seconds"]))
        least_nodes = min(target_rows, key=lambda row: float(row["node_expansions"]))
        sections.append(f"## 目标解个数 = {target}")
        sections.append(f"- 最快算法：`{fastest['variant']}`，耗时 {fastest['runtime_seconds']:.2f}s。")
        sections.append(f"- 搜索节点最少算法：`{least_nodes['variant']}`，节点扩展数 {int(least_nodes['node_expansions'])}。")
        sections.append(
            f"- `{fastest['variant']}` 在该目标下的解计数对比："
            f"Raw={int(fastest['solutions_found'])}，"
            f"Canonical={int(fastest['canonical_solutions_found'])}，"
            f"Signature={int(fastest['signature_solutions_found'])}。"
        )
        sections.append("")

    rows_1000 = _variant_sorted([row for row in rows if int(row["solution_target"]) == 1000])
    if rows_1000:
        best_1000 = min(rows_1000, key=lambda row: float(row["runtime_seconds"]))
        sections.append("## 1000 解横向比较")
        sections.append(
            f"- 在 `1000` 个解的目标下，整体最优时间表现来自 `{best_1000['variant']}`，"
            f"耗时 {best_1000['runtime_seconds']:.2f}s，找到 {int(best_1000['solutions_found'])} 个解。"
        )
        sections.append(
            f"- 对同一批结果做去重后，`{best_1000['variant']}` 仅剩 "
            f"{int(best_1000['canonical_solutions_found'])} 个 canonical 唯一解，"
            f"{int(best_1000['signature_solutions_found'])} 个 signature 唯一解。"
        )
    path = output_root / "multi_solution_analysis.md"
    path.write_text("\n".join(sections), encoding="utf-8")
    return path


def plot_from_csv(csv_path: str | Path, output_dir: str | Path | None = None) -> list[Path]:
    rows = load_rows(csv_path)
    csv_path = Path(csv_path)
    output_root = Path(output_dir) if output_dir else csv_path.parent / "figures"
    output_root.mkdir(parents=True, exist_ok=True)

    plt.style.use("seaborn-v0_8-whitegrid")
    configure_fonts()
    saved_paths: list[Path] = []

    correctness_rows = _rows_by_group(rows, "correctness")
    provided_rows = _rows_by_group(rows, "provided_maps")
    pruning_rows = _rows_by_group(rows, "pruning_ablation")
    scaling_rows = _rows_by_group(rows, "scaling_random_graphs")
    multi_solution_rows = _rows_by_group(rows, "multi_solution_25")

    saved_paths.extend(_plot_correctness(correctness_rows, output_root))

    for metric, title, filename in [
        ("runtime_seconds", "Provided Maps Runtime Comparison", "provided_maps_runtime.png"),
        ("node_expansions", "Provided Maps Node Expansions", "provided_maps_node_expansions.png"),
        ("backtracks", "Provided Maps Backtracks", "provided_maps_backtracks.png"),
    ]:
        path = _plot_grouped_metric(provided_rows, metric, title, output_root / filename)
        if path is not None:
            saved_paths.append(path)

    for metric, title, filename in [
        ("runtime_seconds", "Horizontal Comparison Within Each Color Setting: Runtime", "provided_maps_horizontal_runtime.png"),
        ("node_expansions", "Horizontal Comparison Within Each Color Setting: Node Expansions", "provided_maps_horizontal_nodes.png"),
    ]:
        path = _plot_horizontal_by_dataset(provided_rows, metric, title, output_root / filename)
        if path is not None:
            saved_paths.append(path)

    path = _plot_grouped_metric(
        pruning_rows,
        "node_expansions",
        "Pruning Ablation: Node Expansions",
        output_root / "pruning_ablation.png",
    )
    if path is not None:
        saved_paths.append(path)

    saved_paths.extend(_plot_scaling(scaling_rows, output_root))
    saved_paths.extend(_plot_multi_solution(multi_solution_rows, output_root))

    if provided_rows:
        saved_paths.append(write_provided_maps_analysis(provided_rows, output_root))
        saved_paths.append(write_horizontal_comparison_analysis(provided_rows, output_root))
    if multi_solution_rows:
        saved_paths.append(write_multi_solution_analysis(multi_solution_rows, output_root))

    return saved_paths


if __name__ == "__main__":
    csv_arg = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent / "benchmark_results.csv"
    output_arg = Path(sys.argv[2]) if len(sys.argv) > 2 else None
    for artifact_path in plot_from_csv(csv_arg, output_arg):
        print(f"Saved {artifact_path}")
