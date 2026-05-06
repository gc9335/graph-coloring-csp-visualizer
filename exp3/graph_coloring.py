from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from time import perf_counter
from typing import Iterable


@dataclass(frozen=True)
class Variant:
    id: str
    name: str
    forward_checking: bool
    mrv: bool
    degree_tiebreak: bool
    lcv: bool
    symmetry: bool = True
    clique_bound: bool = True


VARIANTS = {
    "V0": Variant("V0", "OurBase", False, False, False, False),
    "V1": Variant("V1", "OurBase + FC", True, False, False, False),
    "V2": Variant("V2", "OurBase + FC + MRV", True, True, False, False),
    "V3": Variant("V3", "OurBase + FC + MRV + LCV", True, True, False, True),
    "V4": Variant("V4", "OurBase + FC + MRV + Degree", True, True, True, False),
    "V5": Variant("V5", "OurBase + FC + MRV + Degree + LCV", True, True, True, True),
}


@dataclass
class GraphData:
    adj_list: list[list[int]]
    metadata: dict[str, object] = field(default_factory=dict)

    @property
    def num_nodes(self) -> int:
        return len(self.adj_list)


@dataclass
class SolveResult:
    success: bool
    colors: list[int]
    node_expansions: int
    backtracks: int
    runtime_seconds: float
    timed_out: bool
    clique_lower_bound: int
    pruned_by_clique: bool
    used_colors: int
    max_depth: int
    overhead_ms_per_node: float
    solutions_found: int
    solution_target: int
    stopped_on_target: bool


def load_dimacs_graph(filepath: str | Path) -> GraphData:
    path = Path(filepath)
    edges: list[tuple[int, int]] = []
    num_nodes = 0
    metadata: dict[str, object] = {"dataset_name": path.name}
    in_clique_vector = False
    max_clique_in_comments = 0

    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith("c"):
                lowered = line.lower()
                if "number of classes" in lowered:
                    metadata["declared_classes"] = int(line.split(":")[-1].strip())
                elif "clique vector" in lowered:
                    in_clique_vector = True
                elif in_clique_vector and line.startswith("c") and any(ch.isdigit() for ch in line):
                    parts = [part for part in line[1:].split() if part.isdigit()]
                    if len(parts) >= 2:
                        max_clique_in_comments = max(max_clique_in_comments, int(parts[0]))
                elif in_clique_vector:
                    in_clique_vector = False
                continue

            in_clique_vector = False
            if line.startswith("p"):
                parts = line.split()
                num_nodes = int(parts[2])
            elif line.startswith("e"):
                _, u, v = line.split()
                edges.append((int(u) - 1, int(v) - 1))

    adj = [set() for _ in range(num_nodes)]
    for u, v in edges:
        adj[u].add(v)
        adj[v].add(u)

    if max_clique_in_comments:
        metadata["comment_clique_bound"] = max_clique_in_comments

    return GraphData(adj_list=[sorted(neighbors) for neighbors in adj], metadata=metadata)


def greedy_clique_lower_bound(adj_list: list[list[int]], candidates: Iterable[int] | None = None) -> int:
    if candidates is None:
        nodes = list(range(len(adj_list)))
    else:
        nodes = list(candidates)
    if not nodes:
        return 0

    node_set = set(nodes)
    adjacency = [set(neighbors) for neighbors in adj_list]
    ordered = sorted(nodes, key=lambda node: len(adjacency[node] & node_set), reverse=True)
    best = 0
    sample = ordered[: min(len(ordered), 96)]

    for start in sample:
        clique = [start]
        remaining = (adjacency[start] & node_set).copy()
        while remaining:
            next_node = max(remaining, key=lambda node: len(remaining & adjacency[node]))
            clique.append(next_node)
            remaining &= adjacency[next_node]
        best = max(best, len(clique))

    return best


class GraphColoringSolver:
    def __init__(self, adj_list: list[list[int]], num_colors: int):
        self.adj = [list(neighbors) for neighbors in adj_list]
        self.adj_sets = [set(neighbors) for neighbors in adj_list]
        self.n = len(adj_list)
        self.m = num_colors
        self.static_order = sorted(range(self.n), key=lambda node: len(self.adj[node]), reverse=True)
        self.order_rank = {node: rank for rank, node in enumerate(self.static_order)}
        self.colors: list[int] = [0] * self.n
        self.domains: list[set[int]] = [set(range(1, self.m + 1)) for _ in range(self.n)]
        self.backtracks = 0
        self.node_expansions = 0
        self.max_depth = 0
        self._deadline = 0.0
        self._timed_out = False
        self._solutions_found = 0
        self._solution_target = 1
        self._stop_requested = False
        self._first_solution_colors: list[int] | None = None

    def solve(
        self,
        variant: Variant,
        timeout_seconds: float = 60.0,
        max_solutions: int = 1,
    ) -> SolveResult:
        self.colors = [0] * self.n
        self.domains = [set(range(1, self.m + 1)) for _ in range(self.n)]
        self.backtracks = 0
        self.node_expansions = 0
        self.max_depth = 0
        self._timed_out = False
        self._solutions_found = 0
        self._solution_target = max(1, max_solutions)
        self._stop_requested = False
        self._first_solution_colors = None

        started_at = perf_counter()
        self._deadline = started_at + timeout_seconds
        clique_lb = greedy_clique_lower_bound(self.adj)
        pruned_by_clique = variant.clique_bound and clique_lb > self.m
        if not pruned_by_clique:
            self._search(variant, depth=0)
        runtime_seconds = perf_counter() - started_at
        solution_colors = self._first_solution_colors[:] if self._first_solution_colors is not None else self.colors[:]
        used_colors = len({color for color in solution_colors if color != 0})
        overhead_ms = (runtime_seconds / max(1, self.node_expansions)) * 1000.0

        return SolveResult(
            success=self._solutions_found > 0,
            colors=solution_colors,
            node_expansions=self.node_expansions,
            backtracks=self.backtracks,
            runtime_seconds=runtime_seconds,
            timed_out=self._timed_out,
            clique_lower_bound=clique_lb,
            pruned_by_clique=pruned_by_clique,
            used_colors=used_colors,
            max_depth=self.max_depth,
            overhead_ms_per_node=overhead_ms,
            solutions_found=self._solutions_found,
            solution_target=self._solution_target,
            stopped_on_target=self._solutions_found >= self._solution_target,
        )

    def color_order_for_testing(self, node: int, variant: Variant) -> list[int]:
        return self._ordered_colors(node, variant)

    def _search(self, variant: Variant, depth: int) -> bool:
        if self._stop_requested:
            return True
        if perf_counter() > self._deadline:
            self._timed_out = True
            self._stop_requested = True
            return False

        node = self._choose_node(variant)
        if node is None:
            self._solutions_found += 1
            if self._first_solution_colors is None:
                self._first_solution_colors = self.colors[:]
            if self._solutions_found >= self._solution_target:
                self._stop_requested = True
                return True
            return False

        self.node_expansions += 1
        self.max_depth = max(self.max_depth, depth)

        for color in self._ordered_colors(node, variant):
            if not self._is_consistent(node, color):
                continue

            self.colors[node] = color
            previous_domains: list[tuple[int, set[int]]] = []
            ok = True

            if variant.forward_checking:
                for neighbor in self.adj[node]:
                    if self.colors[neighbor] != 0 or color not in self.domains[neighbor]:
                        continue
                    previous_domains.append((neighbor, self.domains[neighbor].copy()))
                    self.domains[neighbor].discard(color)
                    if not self.domains[neighbor]:
                        ok = False
                        break

            if ok:
                should_stop = self._search(variant, depth + 1)
                if should_stop:
                    return True

            for neighbor, domain in reversed(previous_domains):
                self.domains[neighbor] = domain
            self.colors[node] = 0
            self.backtracks += 1

            if self._timed_out or self._stop_requested:
                return False

        return False

    def _choose_node(self, variant: Variant) -> int | None:
        unassigned = [node for node in self.static_order if self.colors[node] == 0]
        if not unassigned:
            return None
        if not variant.mrv:
            return unassigned[0]

        def key(node: int) -> tuple[int, int, int]:
            domain_size = len(self._available_colors(node))
            degree_key = -len(self.adj[node]) if variant.degree_tiebreak else 0
            order_key = self.order_rank[node]
            return (domain_size, degree_key, order_key)

        return min(unassigned, key=key)

    def _ordered_colors(self, node: int, variant: Variant) -> list[int]:
        available = self._available_colors(node)
        used_colors = sorted({color for color in self.colors if color != 0})
        used_first = [color for color in used_colors if color in available]
        fresh = sorted(color for color in available if color not in used_colors)
        ordered = used_first + ([fresh[0]] if variant.symmetry and fresh else fresh)

        if not variant.lcv:
            return ordered

        return sorted(
            ordered,
            key=lambda color: (
                self._impact(node, color),
                color,
            ),
        )

    def _available_colors(self, node: int) -> list[int]:
        return [
            color
            for color in sorted(self.domains[node])
            if self._is_consistent(node, color)
        ]

    def _impact(self, node: int, color: int) -> int:
        return sum(
            1
            for neighbor in self.adj[node]
            if self.colors[neighbor] == 0 and color in self.domains[neighbor]
        )

    def _is_consistent(self, node: int, color: int) -> bool:
        return all(self.colors[neighbor] != color for neighbor in self.adj[node])


def run_variant_on_file(
    dataset_path: str | Path,
    color_limit: int,
    variant: Variant,
    timeout_seconds: float = 60.0,
    max_solutions: int = 1,
) -> tuple[GraphData, SolveResult]:
    graph = load_dimacs_graph(dataset_path)
    solver = GraphColoringSolver(graph.adj_list, color_limit)
    return graph, solver.solve(
        variant,
        timeout_seconds=timeout_seconds,
        max_solutions=max_solutions,
    )
