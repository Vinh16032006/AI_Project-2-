"""Tests for the DPLL solver module."""
from __future__ import annotations

import unittest
from typing import List

from Source.dpll import (
    DPLLSolver,
    check_entailment,
    check_uniqueness,
    dpll,
    is_clause_conflict,
    is_clause_satisfied,
    select_literal,
    simplify_clause,
    solve_sat,
    unit_propagate,
)


class TestDPLL(unittest.TestCase):
    """Bộ kiểm thử toàn diện cho giải thuật DPLL SAT Solver."""

    def test_dpll_satisfiable_formula(self) -> None:
        """A simple SAT formula should return a satisfying assignment."""
        cnf = [[1, 2], [-1, 3], [2, -3]]
        assignment = dpll(cnf)
        self.assertIsNotNone(assignment)
        assert assignment is not None
        self.assertIn(assignment.get(1), {True, False})
        # Verify that all clauses are truly satisfied
        for clause in cnf:
            self.assertTrue(is_clause_satisfied(clause, assignment))

    def test_dpll_unsatisfiable_formula(self) -> None:
        """A contradictory formula should fail with no assignment."""
        cnf = [[1], [-1]]
        self.assertIsNone(dpll(cnf))

    def test_dpll_empty_cnf(self) -> None:
        """Công thức CNF rỗng luôn thỏa mãn (SAT)."""
        assignment = dpll([])
        self.assertIsNotNone(assignment)
        self.assertEqual(assignment, {})

    def test_dpll_empty_clause(self) -> None:
        """CNF chứa mệnh đề rỗng luôn không thể thỏa mãn (UNSAT)."""
        cnf: List[List[int]] = [[]]
        self.assertIsNone(dpll(cnf))

    def test_complete_assignment(self) -> None:
        """Mục 4.3: Đảm bảo trả về complete assignment cho toàn bộ các biến."""
        cnf = [[1]]  # Chỉ chứa biến 1, nhưng có các biến 2, 3 tự do
        all_vars = {1, 2, 3}
        assignment = dpll(cnf, all_vars=all_vars)
        self.assertIsNotNone(assignment)
        assert assignment is not None
        self.assertEqual(assignment[1], True)
        self.assertIn(2, assignment)
        self.assertIn(3, assignment)
        self.assertEqual(set(assignment.keys()), all_vars)

    def test_unit_propagation_chain(self) -> None:
        """Kiểm tra lan truyền đơn vị theo chuỗi: [1], [-1, 2], [-2, 3]."""
        cnf = [[1], [-1, 2], [-2, 3]]
        res = solve_sat(cnf)
        self.assertTrue(res.satisfiable)
        assert res.model is not None
        self.assertEqual(res.model[1], True)
        self.assertEqual(res.model[2], True)
        self.assertEqual(res.model[3], True)
        # Lan truyền đơn vị phải ghi nhận số lần propagation >= 3
        self.assertGreaterEqual(res.propagations, 3)

    def test_conflict_detection(self) -> None:
        """Kiểm tra phát hiện mâu thuẫn trực tiếp và gián tiếp."""
        cnf = [[1, 2], [-1], [-2]]
        res = solve_sat(cnf)
        self.assertFalse(res.satisfiable)
        self.assertIsNone(res.model)

    def test_recursive_branching_and_backtracking(self) -> None:
        """Kiểm tra phân nhánh đệ quy và quay lui với bài toán Pigeonhole (3 chim, 2 chuồng)."""
        # P_ij: Chim i ở chuồng j
        # P11=1, P12=2, P21=3, P22=4, P31=5, P32=6
        cnf = [
            # Mỗi chim ở ít nhất 1 chuồng
            [1, 2],
            [3, 4],
            [5, 6],
            # Chuồng 1 tối đa 1 chim
            [-1, -3],
            [-1, -5],
            [-3, -5],
            # Chuồng 2 tối đa 1 chim
            [-2, -4],
            [-2, -6],
            [-4, -6],
        ]
        res = solve_sat(cnf)
        self.assertFalse(res.satisfiable)
        self.assertIsNone(res.model)
        # Phải có quyết định và quay lui
        self.assertGreater(res.decisions, 0)
        self.assertGreater(res.backtracks, 0)

    def test_deterministic_variable_selection(self) -> None:
        """Kiểm tra tính tất định: cùng công thức chạy nhiều lần cho kết quả giống hệt nhau."""
        cnf = [[1, 2, 3], [-1, -2], [-2, -3], [1, -3]]
        solver = DPLLSolver()

        res1 = solver.solve(cnf)
        res2 = solver.solve(cnf)

        self.assertEqual(res1.satisfiable, res2.satisfiable)
        self.assertEqual(res1.model, res2.model)
        self.assertEqual(res1.decisions, res2.decisions)
        self.assertEqual(res1.propagations, res2.propagations)
        self.assertEqual(res1.backtracks, res2.backtracks)

    def test_recording_metrics(self) -> None:
        """Mục 4.3 Yêu cầu 6: Ghi nhận decisions, propagations, backtracks, và runtime."""
        cnf = [[1, 2], [-1, 2], [-2, 3], [-3]]
        res = solve_sat(cnf)
        self.assertIsInstance(res.decisions, int)
        self.assertIsInstance(res.propagations, int)
        self.assertIsInstance(res.backtracks, int)
        self.assertIsInstance(res.runtime, float)
        self.assertGreaterEqual(res.runtime, 0.0)

    def test_assumptions_support(self) -> None:
        """Kiểm tra giải với giả định (assumptions)."""
        cnf = [[1, 2]]
        # Giả định 1 là False (-1) -> buộc 2 phải là True
        res = solve_sat(cnf, assumptions=[-1])
        self.assertTrue(res.satisfiable)
        assert res.model is not None
        self.assertEqual(res.model[1], False)
        self.assertEqual(res.model[2], True)

        # Giả định cả 1 và 2 đều False -> UNSAT
        res_unsat = solve_sat(cnf, assumptions=[-1, -2])
        self.assertFalse(res_unsat.satisfiable)

    def test_check_entailment_example_from_spec(self) -> None:
        """Kiểm tra ví dụ suy diễn logic trong Mục 3.4 của đặc tả:
        KB = (C_A or C_B) and (not C_A or C_B)
        -> KB |= C_B (B là Criminal)
        -> KB không suy dẫn C_A và không suy dẫn not C_A (A là UNKNOWN).
        """
        # A = 1, B = 2
        kb = [[1, 2], [-1, 2]]

        # KB |= B (biến 2 True)
        self.assertTrue(check_entailment(kb, literal=2))

        # KB không suy dẫn not B
        self.assertFalse(check_entailment(kb, literal=-2))

        # A không được suy dẫn (UNKNOWN)
        self.assertFalse(check_entailment(kb, literal=1))
        self.assertFalse(check_entailment(kb, literal=-1))

    def test_check_uniqueness(self) -> None:
        """Kiểm tra tính duy nhất của nghiệm (Uniqueness check)."""
        # Công thức có duy nhất 1 nghiệm: 1=True, 2=False
        cnf_unique = [[1], [-2]]
        is_unique, model = check_uniqueness(cnf_unique, primary_vars=[1, 2])
        self.assertTrue(is_unique)
        self.assertEqual(model, {1: True, 2: False})

        # Công thức có nhiều hơn 1 nghiệm: [1, 2] -> có 3 nghiệm
        cnf_multi = [[1, 2]]
        is_unique_multi, _ = check_uniqueness(cnf_multi, primary_vars=[1, 2])
        self.assertFalse(is_unique_multi)

    def test_helper_functions_compatibility(self) -> None:
        """Kiểm tra các hàm phụ trợ cũ vẫn hoạt động đúng như mong đợi."""
        self.assertTrue(is_clause_satisfied([1, -2], {1: True}))
        self.assertFalse(is_clause_satisfied([1, -2], {1: False, 2: True}))

        self.assertTrue(is_clause_conflict([1, -2], {1: False, 2: True}))
        self.assertFalse(is_clause_conflict([1, -2], {1: False}))

        self.assertEqual(simplify_clause([1, -2], {1: True}), [])
        self.assertEqual(simplify_clause([1, -2], {2: True}), [1])

        unit_cnf, assignment = unit_propagate([[1], [-1, 2]], {})
        self.assertEqual(assignment.get(1), True)
        self.assertEqual(assignment.get(2), True)

        chosen = select_literal([[1, 2], [2, 3]])
        self.assertEqual(chosen, 2)  # Biến 2 xuất hiện nhiều nhất


# Test standalone functions for pytest compatibility
def test_dpll_satisfiable_formula() -> None:
    cnf = [[1, 2], [-1, 3], [2, -3]]
    assignment = dpll(cnf)
    assert assignment is not None
    assert assignment.get(1) in {True, False}


def test_dpll_unsatisfiable_formula() -> None:
    cnf = [[1], [-1]]
    assert dpll(cnf) is None


if __name__ == "__main__":
    unittest.main()
