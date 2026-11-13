"""Giao diện giải thuật SAT theo DPLL.

Mô-đun này chứa logic đệ quy chính để giải một công thức Boolean ở dạng CNF
(conjunctive normal form). Nó được tổ chức dưới dạng thư viện tái sử dụng để encoder
của game có thể chuyển quy tắc bàn cờ sang CNF và yêu cầu bộ giải tìm ra một phân
bổ thỏa mãn.
"""
from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Tuple

Clause = Iterable[int]
Assignment = Dict[int, bool]


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
    """Trả về True nếu mệnh đề không thể được thỏa mãn dưới gán hiện tại."""
    if not clause:
        return True
    for literal in clause:
        var = abs(literal)
        value = assignment.get(var)
        if value is None:
            continue
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


def unit_propagate(cnf: List[Clause], assignment: Assignment) -> Tuple[List[Clause], Assignment]:
    """Áp dụng lan truyền đơn vị cho đến khi không còn clause đơn vị nào."""
    changed = True
    while changed:
        changed = False
        next_cnf: List[Clause] = []

        for clause in cnf:
            simplified = simplify_clause(clause, assignment)
            if not simplified and clause:
                # Clause này đã được thỏa mãn bởi gán hiện tại; bỏ qua.
                if is_clause_satisfied(clause, assignment):
                    continue
                # Nếu còn clause rỗng thì đây là mâu thuẫn.
                next_cnf.append([])
                continue

            if not clause and not simplified:
                next_cnf.append([])
                continue

            if len(simplified) == 1:
                literal = simplified[0]
                var = abs(literal)
                if assignment.get(var) is None:
                    assignment[var] = literal > 0
                    changed = True

            if simplified:
                next_cnf.append(simplified)

        cnf = next_cnf

    return cnf, assignment


def select_literal(cnf: List[Clause]) -> Optional[int]:
    """Chọn literal phân nhánh bằng heuristic đơn giản."""
    scores: Dict[int, int] = {}
    for clause in cnf:
        for literal in clause:
            var = abs(literal)
            scores[var] = scores.get(var, 0) + 1

    if not scores:
        return None

    return max(scores, key=scores.get)


def dpll(cnf: List[Clause], assignment: Optional[Assignment] = None) -> Optional[Assignment]:
    """Giải công thức CNF bằng thuật toán DPLL."""
    if assignment is None:
        assignment = {}

    simplified_cnf, assignment = unit_propagate(cnf, assignment)

    if any(not clause for clause in simplified_cnf):
        return None

    if not simplified_cnf:
        return assignment

    # Loại bỏ các clause đã được thỏa mãn bởi gán hiện tại.
    simplified_cnf = [clause for clause in simplified_cnf if not is_clause_satisfied(clause, assignment)]
    if any(not clause for clause in simplified_cnf):
        return None
    if not simplified_cnf:
        return assignment

    literal = select_literal(simplified_cnf)
    if literal is None:
        return assignment

    true_assignment = dict(assignment)
    false_assignment = dict(assignment)
    true_assignment[literal] = True
    false_assignment[literal] = False

    result = dpll(simplified_cnf, true_assignment)
    if result is not None:
        return result

    return dpll(simplified_cnf, false_assignment)
