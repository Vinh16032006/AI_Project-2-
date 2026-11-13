"""Tests for the DPLL solver."""

from Source.dpll import dpll


def test_dpll_satisfiable_formula() -> None:
    """A simple SAT formula should return a satisfying assignment."""
    cnf = [[1, 2], [-1, 3], [2, -3]]
    assignment = dpll(cnf)
    assert assignment is not None
    assert assignment.get(1) in {True, False}


def test_dpll_unsatisfiable_formula() -> None:
    """A contradictory formula should fail with no assignment."""
    cnf = [[1], [-1]]
    assert dpll(cnf) is None
