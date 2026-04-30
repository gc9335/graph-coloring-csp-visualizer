import time
import os
import networkx as nx
import matplotlib.pyplot as plt

from V0_Base import GraphColoringSolver, load_dimacs_graph

# 设定全局超时时间（秒）
TIMEOUT = 60.0 

# ... (保留前面相同的 load_dimacs_graph 和 GraphColoringSolver 类的代码) ...

def run_all_benchmarks():
    datasets = {'le450_5a.col': 5, 'le450_15b.col': 15, 'le450_25c.col': 25}
    
    configs = [
        {'name': 'Baseline', 'fc': False, 'mrv': False, 'degree': False, 'lcv': False, 'symmetry': False},
        {'name': 'V1 (+FC)', 'fc': True, 'mrv': False, 'degree': False, 'lcv': False, 'symmetry': True},
        {'name': 'V2 (+MRV)', 'fc': True, 'mrv': True, 'degree': False, 'lcv': False, 'symmetry': True},
        {'name': 'V3 (+LCV)', 'fc': True, 'mrv': True, 'degree': False, 'lcv': True, 'symmetry': True},
        {'name': 'V4 (+Degree)', 'fc': True, 'mrv': True, 'degree': True, 'lcv': False, 'symmetry': True},
        {'name': 'V5 (Ultimate)', 'fc': True, 'mrv': True, 'degree': True, 'lcv': True, 'symmetry': True}
    ]
    
    algo_names = [cfg['name'] for cfg in configs]
    colors = ['#cbd5e1', '#93c5fd', '#60a5fa', '#3b82f6', '#1d4ed8', '#1e3a8a']

    for filename, limit in datasets.items():
        print(f"\n========== 开始测试集: {filename} (颜色上限: {limit}) ==========")
        adj = load_dimacs_graph(filename)
        if not adj:
            print(f"找不到 {filename}，跳过。")
            continue
            
        times = []
        backtracks = []
            
        for cfg in configs:
            solver = GraphColoringSolver(adj, limit)
            succ, bt, duration, is_timeout = solver.solve(cfg)
            
            if is_timeout:
                print(f"[{cfg['name']:15s}] 结果: 超时 (>{TIMEOUT}s) | 回溯: {bt}+")
                times.append(TIMEOUT)
                backtracks.append(bt)
            else:
                print(f"[{cfg['name']:15s}] 结果: 成功 | 耗时: {duration:.4f}s | 回溯: {bt}")
                times.append(max(duration, 0.001))
                backtracks.append(max(bt, 1))

        # === 为当前数据集单独绘制一张图 ===
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
        fig.suptitle(f'Algorithm Performance on {filename} (Max Colors: {limit})', fontsize=16, fontweight='bold')
        
        # 图 1：耗时对比
        bars1 = ax1.bar(algo_names, times, color=colors, edgecolor='black')
        ax1.set_ylabel('Execution Time (seconds) - Log Scale')
        ax1.set_yscale('log')
        ax1.set_xticklabels(algo_names, rotation=30, ha='right')
        ax1.axhline(y=TIMEOUT, color='red', linestyle='--', label=f'Timeout ({TIMEOUT}s)')
        ax1.legend()
        ax1.grid(axis='y', linestyle='--', alpha=0.7)
        
        # 图 2：回溯次数对比
        bars2 = ax2.bar(algo_names, backtracks, color=colors, edgecolor='black')
        ax2.set_ylabel('Backtrack Count - Log Scale')
        ax2.set_yscale('log')
        ax2.set_xticklabels(algo_names, rotation=30, ha='right')
        ax2.grid(axis='y', linestyle='--', alpha=0.7)
        
        # 在柱子上标注具体数值 (针对非超时情况)
        for i, rect in enumerate(bars2):
            height = rect.get_height()
            if times[i] < TIMEOUT:
                ax2.text(rect.get_x() + rect.get_width()/2., height * 1.2,
                         f'{int(height)}', ha='center', va='bottom', fontsize=9, rotation=0)

        plt.tight_layout()
        # 将图片保存到本地文件夹，方便你直接插入 Word
        plt.savefig(f'Result_{filename.split(".")[0]}.png', dpi=300)
        plt.show() # 显示完当前图后，关闭窗口才会继续跑下一个数据集

if __name__ == '__main__':
    run_all_benchmarks()