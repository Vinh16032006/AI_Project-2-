"""Giao diện và thuật toán giải SAT theo DPLL (Davis-Putnam-Logemann-Loveland).

Mô-đun này cung cấp:
1. Unit propagation (lan truyền đơn vị) và Conflict detection (phát hiện xung đột sớm).
2. Deterministic variable selection (chọn biến tất định, tie-breaking nhất quán).
3. Recursive branching và backtracking (phân nhánh đệ quy và quay lui).
4. Returning complete assignment hoặc UNSAT.
5. Ghi nhận số liệu: decisions, propagations, backtracks, runtime.
6. Hỗ trợ assumptions (phục vụ trực tiếp cho suy diễn logic KB |= alpha).
7. Tùy chọn Pure Literal Elimination.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

Clause = Sequence[int]
Assignment = Dict[int, bool]

class SATTimeout(Exception):
    """Ném ra khi vượt quá thời gian cho phép."""

@dataclass
class DPLLResult:
    """Kết quả trả về từ bộ giải DPLL SAT."""

    satisfiable: bool
    model: Optional[Assignment] = None
    decisions: int = 0
    propagations: int = 0
    backtracks: int = 0
    runtime: float = 0.0


def is_clause_satisfied(clause: Clause, assignment: Assignment) -> bool:
    """Kiểm tra xem một mệnh đề đã được thỏa mãn bởi gán hiện tại hay chưa."""
    for literal in clause:
        var = abs(literal)
        value = assignment.get(var)
        if value is None:
            continue
        if (literal > 0 and value is True) or (literal < 0 and value is False):
            return True
    return False


def is_clause_conflict(clause: Clause, assignment: Assignment) -> bool:
    """Trả về True nếu mệnh đề không thể được thỏa mãn dưới gán hiện tại (mọi literal đều False)."""
    if not clause:
        return True
    for literal in clause:
        var = abs(literal)
        value = assignment.get(var)
        if value is None:
            return False
        if (literal > 0 and value is True) or (literal < 0 and value is False):
            return False
    return True


def simplify_clause(clause: Clause, assignment: Assignment) -> List[int]:
    """Loại bỏ các literal đã được thỏa mãn hoặc bị vô hiệu hóa bởi gán hiện tại."""
    simplified: List[int] = []
    for literal in clause:
        var = abs(literal)
        value = assignment.get(var)
        if value is None:
            simplified.append(literal)
        elif (literal > 0 and value is True) or (literal < 0 and value is False):
            # Literal đã được thỏa mãn, nên mệnh đề này đã đúng.
            return []
    return simplified


class DPLLSolver:
    """Bộ giải SAT dựa trên thuật toán DPLL hoàn chỉnh và tất định."""
    def __init__(self, enable_pure_literal: bool = False, deadline: Optional[float] = None) -> None:
        self.enable_pure_literal = enable_pure_literal
        self.deadline = deadline
        self.decisions = 0
        self.propagations = 0
        self.backtracks = 0

    def reset_stats(self) -> None:
        """Đặt lại các bộ đếm thống kê."""
        self.decisions = 0
        self.propagations = 0
        self.backtracks = 0

    def _propagate(
        self, clauses: List[List[int]], assignment: Assignment
    ) -> Tuple[bool, Assignment]:
        """Lan truyền đơn vị (Unit Propagation) liên tục cho đến điểm bất động.

        Trả về:
            (is_conflict, new_assignment)
            is_conflict là True nếu phát hiện mâu thuẫn (mệnh đề rỗng hoặc gán xung đột).
        """
        curr_assignment = dict(assignment)

        while True:
            unit_found = False
            for clause in clauses:
                sat = False
                unassigned_lits: List[int] = []

                for lit in clause:
                    var = abs(lit)
                    val = curr_assignment.get(var)
                    if val is not None:
                        if (lit > 0 and val is True) or (lit < 0 and val is False):
                            sat = True
                            break
                    else:
                        unassigned_lits.append(lit)

                if sat:
                    continue

                # Nếu không có literal nào thỏa mãn và không còn literal unassigned -> xung đột!
                if not unassigned_lits:
                    return True, curr_assignment

                # Nếu chỉ còn đúng 1 literal unassigned -> mệnh đề đơn vị
                if len(unassigned_lits) == 1:
                    unit_lit = unassigned_lits[0]
                    unit_var = abs(unit_lit)
                    needed_val = unit_lit > 0

                    if unit_var not in curr_assignment:
                        curr_assignment[unit_var] = needed_val
                        self.propagations += 1
                        unit_found = True
                    elif curr_assignment[unit_var] != needed_val:
                        return True, curr_assignment

            if not unit_found:
                break

        return False, curr_assignment

    def _pure_literal_elimination(
        self, clauses: List[List[int]], assignment: Assignment
    ) -> Assignment:
        """Tìm và gán giá trị cho các pure literal trong các mệnh đề chưa thỏa mãn."""
        curr_assignment = dict(assignment)
        pos_vars: Set[int] = set()
        neg_vars: Set[int] = set()

        for clause in clauses:
            if is_clause_satisfied(clause, curr_assignment):
                continue
            for lit in clause:
                var = abs(lit)
                if var not in curr_assignment:
                    if lit > 0:
                        pos_vars.add(var)
                    else:
                        neg_vars.add(var)

        pure_pos = pos_vars - neg_vars
        pure_neg = neg_vars - pos_vars

        for var in pure_pos:
            curr_assignment[var] = True
            self.propagations += 1
        for var in pure_neg:
            curr_assignment[var] = False
            self.propagations += 1

        return curr_assignment

    def _select_variable(
        self, clauses: List[List[int]], assignment: Assignment
    ) -> Tuple[Optional[int], bool]:
        """Chọn biến phân nhánh tất định theo trọng số tần số xuất hiện (DLCS).

        Tie-breaking: Ưu tiên biến có ID nhỏ nhất.
        Polarity: Gán True nếu số lần xuất hiện dương >= âm, ngược lại False.
        """
        pos_counts: Dict[int, int] = {}
        neg_counts: Dict[int, int] = {}

        for clause in clauses:
            if is_clause_satisfied(clause, assignment):
                continue
            for lit in clause:
                var = abs(lit)
                if var not in assignment:
                    if lit > 0:
                        pos_counts[var] = pos_counts.get(var, 0) + 1
                    else:
                        neg_counts[var] = neg_counts.get(var, 0) + 1

        candidate_vars = set(pos_counts.keys()) | set(neg_counts.keys())
        if not candidate_vars:
            return None, True

        def score_key(v: int) -> Tuple[int, int]:
            score = pos_counts.get(v, 0) + neg_counts.get(v, 0)
            # Tần số cao nhất (-score nhỏ nhất), nếu hòa thì ID biến nhỏ nhất (v nhỏ nhất)
            return (-score, v)

        best_var = min(candidate_vars, key=score_key)
        pos = pos_counts.get(best_var, 0)
        neg = neg_counts.get(best_var, 0)
        preferred_value = pos >= neg
        return best_var, preferred_value

    def _dpll_recursive(
        self, clauses: List[List[int]], assignment: Assignment, all_vars: Set[int]
    ) -> Optional[Assignment]:
        """Hàm đệ quy chính của thuật toán DPLL với phân nhánh và quay lui."""
        if self.deadline is not None and time.perf_counter() > self.deadline:
            raise SATTimeout()

        # 1. Lan truyền đơn vị
        is_conflict, assignment = self._propagate(clauses, assignment)
        if is_conflict:
            return None

        # 2. Pure literal elimination (nếu bật)
        if self.enable_pure_literal:
            assignment = self._pure_literal_elimination(clauses, assignment)

        # 3. Kiểm tra điều kiện dừng: mọi clause đã thỏa mãn chưa?
        all_sat = True
        for clause in clauses:
            if not is_clause_satisfied(clause, assignment):
                all_sat = False
                # Nếu clause không thỏa mãn và rỗng literal unassigned -> xung đột
                if is_clause_conflict(clause, assignment):
                    return None

        if all_sat:
            return assignment

        # 4. Chọn biến phân nhánh tất định
        var, preferred_val = self._select_variable(clauses, assignment)
        if var is None:
            # Không còn biến nào trong clause, kiểm tra lại toàn bộ clauses
            if all(is_clause_satisfied(c, assignment) for c in clauses):
                return assignment
            return None

        # 5. Phân nhánh 1: Thử giá trị ưu tiên
        self.decisions += 1
        branch1_assign = dict(assignment)
        branch1_assign[var] = preferred_val
        result = self._dpll_recursive(clauses, branch1_assign, all_vars)
        if result is not None:
            return result

        # 6. Quay lui (Backtrack) và thử nhánh 2: Giá trị đối lập
        self.backtracks += 1
        branch2_assign = dict(assignment)
        branch2_assign[var] = not preferred_val
        return self._dpll_recursive(clauses, branch2_assign, all_vars)

    def solve(
        self,
        cnf: Sequence[Clause],
        all_vars: Optional[Iterable[int]] = None,
        assumptions: Optional[Sequence[int]] = None,
    ) -> DPLLResult:
        """Giải công thức CNF và trả về đối tượng DPLLResult hoàn chỉnh."""
        start_time = time.perf_counter()
        self.reset_stats()

        # Thu thập toàn bộ các biến trong công thức và assumptions
        vars_set: Set[int] = set(all_vars) if all_vars is not None else set()
        clauses: List[List[int]] = []
        for c in cnf:
            c_list = list(c)
            clauses.append(c_list)
            for lit in c_list:
                vars_set.add(abs(lit))

        if assumptions:
            for lit in assumptions:
                vars_set.add(abs(lit))

        # Kiểm tra mệnh đề rỗng ban đầu -> UNSAT
        if any(len(c) == 0 for c in clauses):
            return DPLLResult(
                satisfiable=False,
                model=None,
                decisions=0,
                propagations=0,
                backtracks=0,
                runtime=time.perf_counter() - start_time,
            )

        # Khởi tạo gán từ assumptions
        initial_assignment: Assignment = {}
        if assumptions:
            for lit in assumptions:
                var = abs(lit)
                val = lit > 0
                if var in initial_assignment and initial_assignment[var] != val:
                    # Mâu thuẫn trực tiếp ngay trong assumptions
                    return DPLLResult(
                        satisfiable=False,
                        model=None,
                        decisions=0,
                        propagations=0,
                        backtracks=0,
                        runtime=time.perf_counter() - start_time,
                    )
                initial_assignment[var] = val

        # Gọi đệ quy giải
        model = self._dpll_recursive(clauses, initial_assignment, vars_set)
        runtime = time.perf_counter() - start_time

        if model is not None:
            # Đảm bảo trả về mô hình hoàn chỉnh (Complete Assignment) theo yêu cầu Mục 4.3
            for v in sorted(vars_set):
                if v not in model:
                    model[v] = False  # Gán giá trị mặc định tất định cho biến tự do
            return DPLLResult(
                satisfiable=True,
                model=model,
                decisions=self.decisions,
                propagations=self.propagations,
                backtracks=self.backtracks,
                runtime=runtime,
            )

        return DPLLResult(
            satisfiable=False,
            model=None,
            decisions=self.decisions,
            propagations=self.propagations,
            backtracks=self.backtracks,
            runtime=runtime,
        )


def unit_propagate(cnf: List[Clause], assignment: Assignment) -> Tuple[List[Clause], Assignment]:
    """Áp dụng lan truyền đơn vị cho đến khi không còn clause đơn vị nào.

    Hàm này được duy trì để đảm bảo tương thích ngược tuyệt đối với code hiện tại.
    """
    solver = DPLLSolver()
    clauses = [list(c) for c in cnf]
    is_conflict, new_assignment = solver._propagate(clauses, assignment)

    if is_conflict:
        return [[]], new_assignment

    next_cnf: List[Clause] = []
    for clause in clauses:
        simplified = simplify_clause(clause, new_assignment)
        if not simplified:
            if is_clause_satisfied(clause, new_assignment):
                continue
            next_cnf.append([])
            continue
        next_cnf.append(simplified)

    return next_cnf, new_assignment


def select_literal(cnf: List[Clause]) -> Optional[int]:
    """Chọn biến phân nhánh bằng heuristic tất định (tần số cao nhất, tie-break ID nhỏ nhất)."""
    scores: Dict[int, int] = {}
    for clause in cnf:
        for literal in clause:
            var = abs(literal)
            scores[var] = scores.get(var, 0) + 1

    if not scores:
        return None

    return min(scores.keys(), key=lambda v: (-scores[v], v))


def dpll(
    cnf: List[Clause],
    assignment: Optional[Assignment] = None,
    all_vars: Optional[Iterable[int]] = None,
    assumptions: Optional[Sequence[int]] = None,
) -> Optional[Assignment]:
    """Giải công thức CNF bằng thuật toán DPLL.

    Trả về:
        Assignment hoàn chỉnh nếu công thức SAT, hoặc None nếu UNSAT.
    """
    solver = DPLLSolver()
    combined_assumptions: List[int] = list(assumptions or [])
    if assignment:
        for var, val in assignment.items():
            combined_assumptions.append(var if val else -var)

    result = solver.solve(cnf, all_vars=all_vars, assumptions=combined_assumptions)
    return result.model if result.satisfiable else None


def solve_sat(
    cnf: Sequence[Clause],
    all_vars: Optional[Iterable[int]] = None,
    assumptions: Optional[Sequence[int]] = None,
    enable_pure_literal: bool = False,
) -> DPLLResult:
    """Hàm tiện ích giải SAT và nhận đầy đủ số liệu metrics."""
    solver = DPLLSolver(enable_pure_literal=enable_pure_literal)
    return solver.solve(cnf, all_vars=all_vars, assumptions=assumptions)


def check_entailment(
    cnf: Sequence[Clause], literal: int, all_vars: Optional[Iterable[int]] = None
) -> bool:
    """Kiểm tra xem KB |= literal hay không (KB and not literal is UNSAT)."""
    solver = DPLLSolver()
    # Kiểm tra tính khả thỏa của KB and (-literal)
    res = solver.solve(cnf, all_vars=all_vars, assumptions=[-literal])
    return not res.satisfiable


def check_uniqueness(
    cnf: Sequence[Clause],
    primary_vars: Iterable[int],
    assumptions: Optional[Sequence[int]] = None,
) -> Tuple[bool, Optional[Assignment]]:
    """Kiểm tra xem CNF có đúng duy nhất một nghiệm trên tập biến primary_vars hay không.

    Trả về:
        (is_unique, model): is_unique là True nếu có đúng 1 mô hình thỏa mãn.
    """
    primary_list = list(primary_vars)
    solver = DPLLSolver()

    res1 = solver.solve(cnf, all_vars=primary_list, assumptions=assumptions)
    if not res1.satisfiable or res1.model is None:
        return False, None

    first_model = res1.model
    # Thêm mệnh đề chặn (blocking clause) để kiểm tra nghiệm thứ hai
    blocking_clause = [-v if first_model[v] else v for v in primary_list if v in first_model]

    extended_cnf = list(cnf) + [blocking_clause]
    res2 = solver.solve(extended_cnf, all_vars=primary_list, assumptions=assumptions)

    is_unique = not res2.satisfiable
    return is_unique, first_model

@dataclass
class SATStats:

    sat_calls: int = 0
    decisions: int = 0
    propagations: int = 0
    backtracks: int = 0
    runtime: float = 0.0


class SATOracle:
    """Bao quanh DPLLSolver, cộng dồn số liệu cho mọi lần gọi SAT."""

    def __init__(self, enable_pure_literal: bool = False, timeout: Optional[float] = None) -> None:
        self.enable_pure_literal = enable_pure_literal
        self.deadline = None if timeout is None else time.perf_counter() + timeout
        self.stats = SATStats()

    def solve(self, cnf, assumptions=None, all_vars=None) -> DPLLResult:
        solver = DPLLSolver(self.enable_pure_literal, self.deadline)
        start = time.perf_counter()
        self.stats.sat_calls += 1
        try:
            return solver.solve(cnf, all_vars=all_vars, assumptions=assumptions)
        finally:
            self.stats.decisions += solver.decisions
            self.stats.propagations += solver.propagations
            self.stats.backtracks += solver.backtracks
            self.stats.runtime += time.perf_counter() - start