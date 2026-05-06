from exp3.graph_coloring import GraphColoringSolver, VARIANTS, Variant


def triangle_graph():
    return [
        [1, 2],
        [0, 2],
        [0, 1],
    ]


def test_single_solution_mode_stops_after_first_solution():
    solver = GraphColoringSolver(triangle_graph(), num_colors=3)
    result = solver.solve(VARIANTS["V2"], timeout_seconds=5.0, max_solutions=1)

    assert result.success is True
    assert result.solutions_found == 1
    assert result.stopped_on_target is True
    assert result.used_colors == 3


def test_multi_solution_mode_collects_up_to_target():
    solver = GraphColoringSolver(triangle_graph(), num_colors=3)
    no_symmetry_variant = Variant(
        id="T",
        name="Test",
        forward_checking=True,
        mrv=True,
        degree_tiebreak=False,
        lcv=False,
        symmetry=False,
        clique_bound=True,
    )
    result = solver.solve(no_symmetry_variant, timeout_seconds=5.0, max_solutions=4)

    assert result.success is True
    assert result.solutions_found == 4
    assert result.stopped_on_target is True
    assert result.used_colors == 3
