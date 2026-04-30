import os
import time
from math import inf


def load_dimacs_graph(filepath):
    edges = []
    num_nodes = 0
    if not os.path.exists(filepath):
        return None

    with open(filepath, "r", encoding="utf-8") as handle:
        for line in handle:
            if line.startswith("p"):
                num_nodes = int(line.split()[2])
            elif line.startswith("e"):
                parts = line.split()
                edges.append((int(parts[1]) - 1, int(parts[2]) - 1))

    adjacency = [set() for _ in range(num_nodes)]
    for left, right in edges:
        adjacency[left].add(right)
        adjacency[right].add(left)
    return [list(neighbors) for neighbors in adjacency]


class GraphColoringSolver:
    def __init__(self, adj_list, num_colors):
        self.adj = [set(neighbors) for neighbors in adj_list]
        self.n = len(adj_list)
        self.m = num_colors
        self.colors = [0] * self.n
        self.domains = [set(range(1, num_colors + 1)) for _ in range(self.n)]
        self.static_order = sorted(range(self.n), key=lambda node: len(self.adj[node]), reverse=True)
        self.backtracks = 0
        self.node_expansions = 0
        self.max_used_color = 0
        self.start_time = 0.0
        self.timeout = inf
        self.timeout_flag = False
        self.selection_trace = []
        self.clique_lower_bound = 0
        self.clique_pruned = False

    def reset_state(self):
        self.colors = [0] * self.n
        self.domains = [set(range(1, self.m + 1)) for _ in range(self.n)]
        self.backtracks = 0
        self.node_expansions = 0
        self.max_used_color = 0
        self.timeout_flag = False
        self.selection_trace = []
        self.clique_pruned = False

    def greedy_clique_lower_bound(self):
        order = sorted(range(self.n), key=lambda node: len(self.adj[node]), reverse=True)
        best = 0

        for start in order:
            clique = [start]
            candidates = sorted(self.adj[start], key=lambda node: len(self.adj[node]), reverse=True)
            while candidates:
                node = candidates.pop(0)
                if all(node in self.adj[member] for member in clique):
                    clique.append(node)
                    candidates = [other for other in candidates if other in self.adj[node]]
            best = max(best, len(clique))
            if best > self.m:
                break
        return best

    def select_node(self, unassigned, config):
        if config["mrv"]:
            return min(
                unassigned,
                key=lambda node: (
                    len(self.domains[node]),
                    -len(self.adj[node]) if config["degree"] else 0,
                    self.static_order.index(node),
                ),
            )
        return unassigned[0]

    def lcv_impact(self, node, color):
        return sum(1 for neighbor in self.adj[node] if self.colors[neighbor] == 0 and color in self.domains[neighbor])

    def ordered_values_for(self, node, config):
        domain_values = set(self.domains[node])
        if not config["symmetry"]:
            values = sorted(domain_values)
        else:
            values = [color for color in range(1, self.max_used_color + 1) if color in domain_values]
            next_color = self.max_used_color + 1
            if next_color <= self.m and next_color in domain_values:
                values.append(next_color)

        if config["lcv"] and len(values) > 1:
            values.sort(key=lambda color: (self.lcv_impact(node, color), color))
        return values

    def is_consistent(self, node, color):
        return all(self.colors[neighbor] != color for neighbor in self.adj[node])

    def solve(self, config, timeout=None):
        self.reset_state()
        self.timeout = inf if timeout is None else timeout
        self.start_time = time.time()
        self.clique_lower_bound = self.greedy_clique_lower_bound()
        if self.clique_lower_bound > self.m:
            self.clique_pruned = True
            duration = time.time() - self.start_time
            overhead_ms = (duration / max(self.backtracks, 1)) * 1000
            return False, self.backtracks, duration, self.timeout_flag, overhead_ms

        unassigned = list(self.static_order)
        success = self._backtrack(unassigned, config, depth=0)
        duration = time.time() - self.start_time
        overhead_ms = (duration / max(self.backtracks, 1)) * 1000
        return success, self.backtracks, duration, self.timeout_flag, overhead_ms

    def _backtrack(self, unassigned, config, depth):
        if time.time() - self.start_time > self.timeout:
            self.timeout_flag = True
            return False
        if not unassigned:
            return True

        self.node_expansions += 1
        node = self.select_node(unassigned, config)
        remove_index = unassigned.index(node)
        unassigned.pop(remove_index)
        self.selection_trace.append((depth, node))

        for color in self.ordered_values_for(node, config):
            if not self.is_consistent(node, color):
                continue

            old_max_used = self.max_used_color
            self.colors[node] = color
            self.max_used_color = max(self.max_used_color, color)

            saved_domains = {}
            consistent = True
            if config["fc"]:
                for neighbor in self.adj[node]:
                    if self.colors[neighbor] == 0 and color in self.domains[neighbor]:
                        if neighbor not in saved_domains:
                            saved_domains[neighbor] = self.domains[neighbor].copy()
                        self.domains[neighbor].discard(color)
                        if not self.domains[neighbor]:
                            consistent = False
                            break

            if consistent and self._backtrack(unassigned, config, depth + 1):
                return True

            self.colors[node] = 0
            self.max_used_color = old_max_used
            for neighbor, domain in saved_domains.items():
                self.domains[neighbor] = domain
            self.backtracks += 1

            if self.timeout_flag:
                unassigned.insert(remove_index, node)
                return False

        unassigned.insert(remove_index, node)
        return False
