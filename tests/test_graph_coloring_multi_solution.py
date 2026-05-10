from __future__ import annotations

import pytest

from exp3.graph_coloring import (
    GraphColoringSolver,
    VARIANTS,
    generate_random_graph,
    load_dimacs_graph,
    small_validation_graph,
    validate_coloring,
)


def disconnected_graph() -> list[list[int]]:
    return [
        [1, 2, 3],
        [0, 2, 3],
        [0, 1, 3],
        [0, 1, 2],
        [5],
        [4],
    ]


@pytest.mark.parametrize("variant_id", [f"B{i}" for i in range(6)])
def test_small_four_color_graph_solves_correctly(variant_id: str) -> None:
    graph = small_validation_graph()
    solver = GraphColoringSolver(graph.adj_list, num_colors=4)
    result = solver.solve(VARIANTS[variant_id], timeout_seconds=5.0, max_solutions=1, graph_metadata=graph.metadata)

    assert result.success is True
    assert result.solutions_found == 1
    assert result.used_colors == 4
    assert result.component_count == 1
    assert result.largest_component == 4
    assert validate_coloring(graph.adj_list, result.colors)


def test_clique_prune_triggers_for_structured_variant() -> None:
    graph = small_validation_graph()
    solver = GraphColoringSolver(graph.adj_list, num_colors=3)
    result = solver.solve(VARIANTS["B5"], timeout_seconds=5.0, max_solutions=1, graph_metadata=graph.metadata)

    assert result.success is False
    assert result.pruned_by_clique is True
    assert result.search_status == "pruned"
    assert result.clique_lower_bound >= 4
    assert "clique_lower_bound" in result.explanation_notes


def test_component_decomposition_reports_metrics_on_disconnected_graph() -> None:
    graph = disconnected_graph()
    solver = GraphColoringSolver(graph, num_colors=4)
    result = solver.solve(VARIANTS["B5"], timeout_seconds=5.0, max_solutions=1)

    assert result.success is True
    assert result.component_count == 2
    assert result.largest_component == 4
    assert result.search_status == "success"
    assert validate_coloring(graph, result.colors)


def test_multi_solution_tracks_raw_and_canonical_counts() -> None:
    graph = [
        [],
        [],
    ]
    solver = GraphColoringSolver(graph, num_colors=2)
    result = solver.solve(VARIANTS["B0"], timeout_seconds=5.0, max_solutions=4)

    assert result.success is True
    assert result.solutions_found == 4
    assert result.canonical_solutions_found == 2
    assert result.signature_solutions_found == 2


def test_random_graph_generation_is_deterministic_with_fixed_seed() -> None:
    graph_a = generate_random_graph(12, 0.25, 1234)
    graph_b = generate_random_graph(12, 0.25, 1234)
    graph_c = generate_random_graph(12, 0.25, 4321)

    assert graph_a.adj_list == graph_b.adj_list
    assert graph_a.adj_list != graph_c.adj_list


def test_le450_15b_graph_metadata_sets_fourth_node_as_preferred_start() -> None:
    graph = load_dimacs_graph("exp3/le450_15b.col")

    assert graph.metadata["preferred_start_node"] == 3


@pytest.mark.parametrize("variant_id", [f"B{i}" for i in range(6)])
def test_preferred_start_node_is_first_choice_for_all_variants(variant_id: str) -> None:
    graph = [
        [1, 2, 3],
        [0],
        [0],
        [0],
    ]
    solver = GraphColoringSolver(graph, num_colors=3, preferred_start_node=2)

    assert solver._choose_node(VARIANTS[variant_id]) == 2
