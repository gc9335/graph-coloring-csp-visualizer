from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


def load_core_module():
    module_path = Path("code/graph_coloring_core.py").resolve()
    spec = spec_from_file_location("graph_coloring_core", module_path)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


core = load_core_module()


def make_solver(adj, colors):
    return core.GraphColoringSolver(adj, colors)


V0 = {"name": "V0_Base", "fc": False, "mrv": False, "degree": False, "lcv": False, "symmetry": True}
V4 = {"name": "V4_Base_FC_MRV_Degree", "fc": True, "mrv": True, "degree": True, "lcv": False, "symmetry": True}
V5 = {"name": "V5_Base_FC_MRV_Degree_LCV", "fc": True, "mrv": True, "degree": True, "lcv": True, "symmetry": True}


def test_clique_lower_bound_prunes_before_search():
    k4 = [
        [1, 2, 3],
        [0, 2, 3],
        [0, 1, 3],
        [0, 1, 2],
    ]
    solver = make_solver(k4, 3)
    success, backtracks, duration, timeout_flag, overhead_ms = solver.solve(V0)
    assert success is False
    assert timeout_flag is False
    assert solver.clique_pruned is True
    assert solver.clique_lower_bound >= 4
    assert solver.node_expansions == 0
    assert backtracks == 0


def test_symmetry_keeps_values_ordered_by_used_colors_then_one_new_color():
    edge = [[1], [0]]
    solver = make_solver(edge, 3)
    assert solver.ordered_values_for(0, V0) == [1]
    solver.colors[0] = 1
    solver.max_used_color = 1
    assert solver.ordered_values_for(1, V0) == [1, 2]


def test_mrv_degree_tiebreak_prefers_highest_degree_node():
    graph = [
        [1, 2, 3],
        [0],
        [0],
        [0],
    ]
    solver = make_solver(graph, 3)
    for domain in solver.domains:
        domain.clear()
        domain.update({1, 2})
    chosen = solver.select_node([0, 1, 2, 3], V4)
    assert chosen == 0


def test_lcv_orders_by_smallest_future_domain_damage():
    graph = [
        [1, 2],
        [0],
        [0],
    ]
    solver = make_solver(graph, 3)
    solver.domains[0] = {1, 2}
    solver.domains[1] = {1}
    solver.domains[2] = {1, 2}
    solver.max_used_color = 1
    assert solver.ordered_values_for(0, V5) == [2, 1]


def test_static_degree_order_remains_stable_across_backtracking():
    triangle = [
        [1, 2],
        [0, 2],
        [0, 1],
    ]
    solver = make_solver(triangle, 2)
    success, backtracks, duration, timeout_flag, overhead_ms = solver.solve(V0)
    assert success is False
    depth_to_expected = {depth: node for depth, node in enumerate(solver.static_order)}
    for depth, node in solver.selection_trace:
        assert node == depth_to_expected[depth]


def test_none_timeout_means_no_explicit_time_limit():
    edge = [[1], [0]]
    solver = make_solver(edge, 2)
    solver.solve(V0, timeout=None)
    assert solver.timeout == float("inf")


if __name__ == "__main__":
    test_clique_lower_bound_prunes_before_search()
    test_symmetry_keeps_values_ordered_by_used_colors_then_one_new_color()
    test_mrv_degree_tiebreak_prefers_highest_degree_node()
    test_lcv_orders_by_smallest_future_domain_damage()
    test_static_degree_order_remains_stable_across_backtracking()
    test_none_timeout_means_no_explicit_time_limit()
    print("test_graph_coloring_core.py passed")
