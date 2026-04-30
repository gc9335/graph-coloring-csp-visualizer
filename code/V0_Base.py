import os
import matplotlib.pyplot as plt

from graph_coloring_core import GraphColoringSolver, load_dimacs_graph


TIMEOUT = 60.0
CONFIG = {"name": "V0_Base", "fc": False, "mrv": False, "degree": False, "lcv": False, "symmetry": True}
DATASETS = {"le450_5a.col": 5, "le450_15b.col": 15, "le450_25a.col": 25}


if __name__ == "__main__":
    times, backtracks, overheads, labels = [], [], [], []
    base_dir = os.path.dirname(__file__)

    print(f"========== 正在运行 {CONFIG['name']} ==========")
    for filename, limit in DATASETS.items():
        adj = load_dimacs_graph(os.path.join(base_dir, filename))
        if not adj:
            print(f"未找到 {filename}，跳过。")
            continue

        solver = GraphColoringSolver(adj, limit)
        success, bt, duration, timeout_flag, overhead_ms = solver.solve(CONFIG, timeout=TIMEOUT)

        labels.append(filename.split(".")[0])
        if timeout_flag:
            print(f"[{filename}] 超时(>{TIMEOUT}s) | 回溯: {bt}+ | Overhead: 无法准确评估")
            times.append(TIMEOUT)
            backtracks.append(bt)
            overheads.append(0)
        else:
            print(f"[{filename}] 结果: {'成功' if success else '失败'} | 回溯: {bt} | 展开: {solver.node_expansions} | CliqueLB: {solver.clique_lower_bound} | 耗时: {duration:.4f}s | Overhead: {overhead_ms:.4f} ms/次回溯")
            times.append(duration)
            backtracks.append(bt)
            overheads.append(overhead_ms)

    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(15, 5))
    fig.suptitle(f"Performance of {CONFIG['name']} across Datasets", fontweight="bold")
    colors = ["#fca5a5", "#93c5fd", "#86efac"]

    ax1.bar(labels, times, color=colors, edgecolor="black")
    ax1.set_title("Execution Time (s)")
    ax1.axhline(y=TIMEOUT, color="r", linestyle="--", label="Timeout")

    ax2.bar(labels, backtracks, color=colors, edgecolor="black")
    ax2.set_yscale("log")
    ax2.set_title("Backtrack Count (Log Scale)")

    bars3 = ax3.bar(labels, overheads, color=colors, edgecolor="black")
    ax3.set_title("Overhead (ms per Backtrack)")
    for rect in bars3:
        if rect.get_height() > 0:
            ax3.text(rect.get_x() + rect.get_width() / 2.0, rect.get_height(), f"{rect.get_height():.3f}", ha="center", va="bottom")

    plt.tight_layout()
    plt.savefig(f"{CONFIG['name']}_Results.png", dpi=300)
    plt.show()
