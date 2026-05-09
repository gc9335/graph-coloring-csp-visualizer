from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from random import Random
from statistics import mean
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
    symmetry_breaking: bool = False
    clique_bound: bool = False
    component_decomposition: bool = False


VARIANTS = {
    "B0": Variant("B0", "Base Backtracking", False, False, False, False),
    "B1": Variant("B1", "Backtracking + Forward Checking", True, False, False, False),
    "B2": Variant("B2", "B1 + MRV", True, True, False, False),
    "B3": Variant("B3", "B2 + Degree Tie-Break", True, True, True, False),
    "B4": Variant("B4", "B3 + LCV", True, True, True, True),
    "B5": Variant(
        "B5",
        "B4 + Structured Pruning",
        True,
        True,
        True,
        True,
        symmetry_breaking=True,
        clique_bound=True,
        component_decomposition=True,
    ),
}


@dataclass
class GraphData:
    adj_list: list[list[int]]
    metadata: dict[str, object] = field(default_factory=dict)

    @property
    def num_nodes(self) -> int:
        return len(self.adj_list)

    @property
    def num_edges(self) -> int:
        return sum(len(neighbors) for neighbors in self.adj_list) // 2

    @property
    def density(self) -> float:
        if self.num_nodes <= 1:
            return 0.0
        return (2 * self.num_edges) / (self.num_nodes * (self.num_nodes - 1))

    @property
    def degrees(self) -> list[int]:
        return [len(neighbors) for neighbors in self.adj_list]


@dataclass(frozen=True)
class CliqueInfo:
    lower_bound: int
    witness_nodes: tuple[int, ...] = ()
    from_comments: bool = False


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
    component_count: int
    largest_component: int
    first_fail_depth: int | None
    search_status: str
    explanation_notes: str


def build_graph_from_edges(
    num_nodes: int,
    edges: Iterable[tuple[int, int]],
    *,
    dataset_name: str,
    declared_classes: int | None = None,
    metadata: dict[str, object] | None = None,
) -> GraphData:
    adj = [set() for _ in range(num_nodes)]
    for u, v in edges:
        if u == v:
            continue
        adj[u].add(v)
        adj[v].add(u)

    merged_metadata: dict[str, object] = {"dataset_name": dataset_name}
    if declared_classes is not None:
        merged_metadata["declared_classes"] = declared_classes
    if metadata:
        merged_metadata.update(metadata)

    graph = GraphData(adj_list=[sorted(neighbors) for neighbors in adj], metadata=merged_metadata)
    graph.metadata.setdefault("n_edges", graph.num_edges)
    graph.metadata.setdefault("density", graph.density)
    graph.metadata.setdefault("max_degree", max(graph.degrees, default=0))
    graph.metadata.setdefault("avg_degree", mean(graph.degrees) if graph.degrees else 0.0)
    graph.metadata.setdefault("min_degree", min(graph.degrees, default=0))
    return graph


def small_validation_graph() -> GraphData:
    return build_graph_from_edges(
        4,
        [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)],
        dataset_name="validation_k4",
        declared_classes=4,
        metadata={
            "graph_family": "small_validation",
            "description": "Small K4 graph for exact four-color correctness validation.",
        },
    )


def generate_random_graph(
    num_vertices: int,
    edge_probability: float,
    seed: int,
    *,
    dataset_name: str | None = None,
) -> GraphData:
    rng = Random(seed)
    edges: list[tuple[int, int]] = []
    for u in range(num_vertices):
        for v in range(u + 1, num_vertices):
            if rng.random() <= edge_probability:
                edges.append((u, v))
    return build_graph_from_edges(
        num_vertices,
        edges,
        dataset_name=dataset_name or f"random_gnp_n{num_vertices}_p{edge_probability:.2f}_s{seed}",
        metadata={
            "graph_family": "random_graph",
            "seed": seed,
            "edge_probability": edge_probability,
        },
    )


def generate_random_k_colorable_graph(
    num_vertices: int,
    edge_probability: float,
    seed: int,
    color_limit: int,
    *,
    dataset_name: str | None = None,
) -> GraphData:
    rng = Random(seed)
    partitions = [index % color_limit for index in range(num_vertices)]
    rng.shuffle(partitions)
    edges: list[tuple[int, int]] = []
    for u in range(num_vertices):
        for v in range(u + 1, num_vertices):
            if partitions[u] == partitions[v]:
                continue
            if rng.random() <= edge_probability:
                edges.append((u, v))
    return build_graph_from_edges(
        num_vertices,
        edges,
        dataset_name=dataset_name or f"random_colorable_n{num_vertices}_p{edge_probability:.2f}_s{seed}",
        declared_classes=color_limit,
        metadata={
            "graph_family": "random_k_colorable",
            "seed": seed,
            "edge_probability": edge_probability,
            "generator_color_limit": color_limit,
        },
    )


def load_dimacs_graph(filepath: str | Path) -> GraphData:
    path = Path(filepath)
    edges: list[tuple[int, int]] = []
    num_nodes = 0
    metadata: dict[str, object] = {"dataset_name": path.name, "graph_family": "dimacs_leighton"}
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
                elif "number of edges" in lowered:
                    metadata["comment_edges"] = int(line.split(":")[-1].strip())
                elif "edge density" in lowered:
                    metadata["comment_density"] = float(line.split(":")[-1].strip())
                elif "max degree" in lowered:
                    metadata["comment_max_degree"] = int(line.split(":")[-1].strip())
                elif "avg degree" in lowered:
                    metadata["comment_avg_degree"] = float(line.split(":")[-1].strip())
                elif "min degree" in lowered:
                    metadata["comment_min_degree"] = int(line.split(":")[-1].strip())
                elif "clique vector" in lowered:
                    in_clique_vector = True
                elif in_clique_vector and any(ch.isdigit() for ch in line):
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

    if max_clique_in_comments:
        metadata["comment_clique_bound"] = max_clique_in_comments

    return build_graph_from_edges(
        num_nodes,
        edges,
        dataset_name=path.name,
        declared_classes=metadata.get("declared_classes"),
        metadata=metadata,
    )


def connected_components(adj_list: list[list[int]]) -> list[list[int]]:
    visited = [False] * len(adj_list)
    components: list[list[int]] = []
    for start in range(len(adj_list)):
        if visited[start]:
            continue
        stack = [start]
        visited[start] = True
        component: list[int] = []
        while stack:
            node = stack.pop()
            component.append(node)
            for neighbor in adj_list[node]:
                if not visited[neighbor]:
                    visited[neighbor] = True
                    stack.append(neighbor)
        components.append(sorted(component))
    return components


def induce_subgraph(adj_list: list[list[int]], component: list[int]) -> tuple[list[list[int]], dict[int, int], dict[int, int]]:
    old_to_new = {old: new for new, old in enumerate(component)}
    new_to_old = {new: old for old, new in old_to_new.items()}
    sub_adj: list[list[int]] = []
    component_set = set(component)
    for old_node in component:
        sub_adj.append(sorted(old_to_new[neighbor] for neighbor in adj_list[old_node] if neighbor in component_set))
    return sub_adj, old_to_new, new_to_old


def greedy_clique_info(
    adj_list: list[list[int]],
    candidates: Iterable[int] | None = None,
    comment_bound: int | None = None,
) -> CliqueInfo:
    if candidates is None:
        nodes = list(range(len(adj_list)))
    else:
        nodes = list(candidates)
    if not nodes:
        return CliqueInfo(lower_bound=0)

    if comment_bound is not None and comment_bound > 0:
        return CliqueInfo(lower_bound=comment_bound, from_comments=True)

    node_set = set(nodes)
    adjacency = [set(neighbors) for neighbors in adj_list]
    ordered = sorted(nodes, key=lambda node: len(adjacency[node] & node_set), reverse=True)
    best_clique: tuple[int, ...] = ()
    sample = ordered[: min(len(ordered), 96)]

    for start in sample:
        clique = [start]
        remaining = (adjacency[start] & node_set).copy()
        while remaining:
            next_node = max(remaining, key=lambda node: len(remaining & adjacency[node]))
            clique.append(next_node)
            remaining &= adjacency[next_node]
        if len(clique) > len(best_clique):
            best_clique = tuple(clique)

    return CliqueInfo(lower_bound=len(best_clique), witness_nodes=best_clique)


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
        self._first_fail_depth: int | None = None

    def solve(
        self,
        variant: Variant,
        timeout_seconds: float = 60.0,
        max_solutions: int = 1,
        *,
        graph_metadata: dict[str, object] | None = None,
    ) -> SolveResult:
        metadata = graph_metadata or {}
        components = connected_components(self.adj)
        largest_component = max((len(component) for component in components), default=0)
        clique_info = greedy_clique_info(
            self.adj,
            comment_bound=int(metadata["comment_clique_bound"]) if "comment_clique_bound" in metadata else None,
        )

        started_at = perf_counter()
        deadline = started_at + timeout_seconds
        explanation_notes = [
            f"clique_lower_bound={clique_info.lower_bound}",
            f"component_count={len(components)}",
            f"largest_component={largest_component}",
            f"density={float(metadata.get('density', 0.0)):.4f}",
            f"max_degree={int(metadata.get('max_degree', 0))}",
            f"avg_degree={float(metadata.get('avg_degree', 0.0)):.2f}",
        ]

        if variant.clique_bound and clique_info.lower_bound > self.m:
            runtime_seconds = perf_counter() - started_at
            return SolveResult(
                success=False,
                colors=[0] * self.n,
                node_expansions=0,
                backtracks=0,
                runtime_seconds=runtime_seconds,
                timed_out=False,
                clique_lower_bound=clique_info.lower_bound,
                pruned_by_clique=True,
                used_colors=0,
                max_depth=0,
                overhead_ms_per_node=0.0,
                solutions_found=0,
                solution_target=max(1, max_solutions),
                stopped_on_target=False,
                component_count=len(components),
                largest_component=largest_component,
                first_fail_depth=0,
                search_status="pruned",
                explanation_notes="; ".join(explanation_notes + ["pruned_by=clique_bound"]),
            )

        if variant.component_decomposition and len(components) > 1:
            reduced_variant = Variant(
                id=variant.id,
                name=variant.name,
                forward_checking=variant.forward_checking,
                mrv=variant.mrv,
                degree_tiebreak=variant.degree_tiebreak,
                lcv=variant.lcv,
                symmetry_breaking=variant.symmetry_breaking,
                clique_bound=variant.clique_bound,
                component_decomposition=False,
            )
            aggregate_colors = [0] * self.n
            total_nodes = 0
            total_backtracks = 0
            total_solutions = 0
            timed_out = False
            max_depth = 0
            first_fail_depths: list[int] = []
            for component in components:
                remaining = max(0.001, deadline - perf_counter())
                sub_adj, _, new_to_old = induce_subgraph(self.adj, component)
                sub_solver = GraphColoringSolver(sub_adj, self.m)
                sub_result = sub_solver.solve(
                    reduced_variant,
                    timeout_seconds=remaining,
                    max_solutions=max_solutions,
                    graph_metadata={
                        "density": _density(sub_adj),
                        "max_degree": max((len(neighbors) for neighbors in sub_adj), default=0),
                        "avg_degree": mean(len(neighbors) for neighbors in sub_adj) if sub_adj else 0.0,
                    },
                )
                total_nodes += sub_result.node_expansions
                total_backtracks += sub_result.backtracks
                total_solutions += sub_result.solutions_found
                max_depth = max(max_depth, sub_result.max_depth)
                if sub_result.first_fail_depth is not None:
                    first_fail_depths.append(sub_result.first_fail_depth)
                for new_index, color in enumerate(sub_result.colors):
                    aggregate_colors[new_to_old[new_index]] = color
                if not sub_result.success:
                    timed_out = timed_out or sub_result.timed_out
                    runtime_seconds = perf_counter() - started_at
                    status = "timeout" if timed_out else sub_result.search_status
                    overhead_ms = (runtime_seconds / max(1, total_nodes)) * 1000.0
                    return SolveResult(
                        success=False,
                        colors=aggregate_colors,
                        node_expansions=total_nodes,
                        backtracks=total_backtracks,
                        runtime_seconds=runtime_seconds,
                        timed_out=timed_out,
                        clique_lower_bound=clique_info.lower_bound,
                        pruned_by_clique=False,
                        used_colors=len({color for color in aggregate_colors if color != 0}),
                        max_depth=max_depth,
                        overhead_ms_per_node=overhead_ms,
                        solutions_found=total_solutions,
                        solution_target=max(1, max_solutions),
                        stopped_on_target=False,
                        component_count=len(components),
                        largest_component=largest_component,
                        first_fail_depth=min(first_fail_depths) if first_fail_depths else None,
                        search_status=status,
                        explanation_notes="; ".join(explanation_notes + ["component_strategy=decompose"]),
                    )

            runtime_seconds = perf_counter() - started_at
            overhead_ms = (runtime_seconds / max(1, total_nodes)) * 1000.0
            return SolveResult(
                success=True,
                colors=aggregate_colors,
                node_expansions=total_nodes,
                backtracks=total_backtracks,
                runtime_seconds=runtime_seconds,
                timed_out=False,
                clique_lower_bound=clique_info.lower_bound,
                pruned_by_clique=False,
                used_colors=len({color for color in aggregate_colors if color != 0}),
                max_depth=max_depth,
                overhead_ms_per_node=overhead_ms,
                solutions_found=max(1, total_solutions),
                solution_target=max(1, max_solutions),
                stopped_on_target=True,
                component_count=len(components),
                largest_component=largest_component,
                first_fail_depth=min(first_fail_depths) if first_fail_depths else None,
                search_status="success",
                explanation_notes="; ".join(explanation_notes + ["component_strategy=decompose"]),
            )

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
        self._first_fail_depth = None
        self._deadline = deadline

        self._search(variant, depth=0)
        runtime_seconds = perf_counter() - started_at
        solution_colors = self._first_solution_colors[:] if self._first_solution_colors is not None else self.colors[:]
        used_colors = len({color for color in solution_colors if color != 0})
        overhead_ms = (runtime_seconds / max(1, self.node_expansions)) * 1000.0
        search_status = "success" if self._solutions_found > 0 else ("timeout" if self._timed_out else "exhausted")

        return SolveResult(
            success=self._solutions_found > 0,
            colors=solution_colors,
            node_expansions=self.node_expansions,
            backtracks=self.backtracks,
            runtime_seconds=runtime_seconds,
            timed_out=self._timed_out,
            clique_lower_bound=clique_info.lower_bound,
            pruned_by_clique=False,
            used_colors=used_colors,
            max_depth=self.max_depth,
            overhead_ms_per_node=overhead_ms,
            solutions_found=self._solutions_found,
            solution_target=self._solution_target,
            stopped_on_target=self._solutions_found >= self._solution_target,
            component_count=len(components),
            largest_component=largest_component,
            first_fail_depth=self._first_fail_depth,
            search_status=search_status,
            explanation_notes="; ".join(
                explanation_notes
                + [f"component_strategy={'decompose' if variant.component_decomposition else 'single-search'}"]
            ),
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

        available_colors = self._ordered_colors(node, variant)
        if not available_colors:
            self._record_fail_depth(depth)
            self.backtracks += 1
            return False

        self.node_expansions += 1
        self.max_depth = max(self.max_depth, depth)

        for color in available_colors:
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
                        self._record_fail_depth(depth + 1)
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

        self._record_fail_depth(depth)
        return False

    def _record_fail_depth(self, depth: int) -> None:
        if self._first_fail_depth is None or depth < self._first_fail_depth:
            self._first_fail_depth = depth

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
        if not available:
            return []

        used_colors = sorted({color for color in self.colors if color != 0})
        used_first = [color for color in used_colors if color in available]
        fresh = sorted(color for color in available if color not in used_colors)
        if variant.symmetry_breaking:
            ordered = used_first + ([fresh[0]] if fresh else [])
        else:
            ordered = used_first + fresh

        if not variant.lcv:
            return ordered

        return sorted(ordered, key=lambda color: (self._impact(node, color), color))

    def _available_colors(self, node: int) -> list[int]:
        return [color for color in sorted(self.domains[node]) if self._is_consistent(node, color)]

    def _impact(self, node: int, color: int) -> int:
        return sum(
            1
            for neighbor in self.adj[node]
            if self.colors[neighbor] == 0 and color in self.domains[neighbor]
        )

    def _is_consistent(self, node: int, color: int) -> bool:
        return all(self.colors[neighbor] != color for neighbor in self.adj[node])


def _density(adj_list: list[list[int]]) -> float:
    n = len(adj_list)
    if n <= 1:
        return 0.0
    edges = sum(len(neighbors) for neighbors in adj_list) // 2
    return (2 * edges) / (n * (n - 1))


def validate_coloring(adj_list: list[list[int]], colors: list[int]) -> bool:
    if len(adj_list) != len(colors):
        return False
    for node, neighbors in enumerate(adj_list):
        color = colors[node]
        if color == 0:
            return False
        if any(colors[neighbor] == color for neighbor in neighbors):
            return False
    return True


def run_variant_on_graph(
    graph: GraphData,
    color_limit: int,
    variant: Variant,
    timeout_seconds: float = 60.0,
    max_solutions: int = 1,
) -> SolveResult:
    solver = GraphColoringSolver(graph.adj_list, color_limit)
    return solver.solve(
        variant,
        timeout_seconds=timeout_seconds,
        max_solutions=max_solutions,
        graph_metadata={
            **graph.metadata,
            "density": graph.density,
            "max_degree": max(graph.degrees, default=0),
            "avg_degree": mean(graph.degrees) if graph.degrees else 0.0,
        },
    )


def run_variant_on_file(
    dataset_path: str | Path,
    color_limit: int,
    variant: Variant,
    timeout_seconds: float = 60.0,
    max_solutions: int = 1,
) -> tuple[GraphData, SolveResult]:
    graph = load_dimacs_graph(dataset_path)
    return graph, run_variant_on_graph(
        graph,
        color_limit,
        variant,
        timeout_seconds=timeout_seconds,
        max_solutions=max_solutions,
    )
