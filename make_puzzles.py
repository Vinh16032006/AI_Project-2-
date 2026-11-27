from __future__ import annotations

import argparse
import json
import os
import random
from typing import Any, Dict, List, Optional, Tuple

from Source.agent import DeductiveAgent
from Source.dpll import SATOracle
from Source.game_engine import GameEngine

NAMES = [
    "Abel", "Bea", "Clara", "Derek", "Eliza", "Franz", "Gina", "Hannah", "Ivan",
    "Jade", "Kobe", "Lucy", "Mason", "Nina", "Otis", "Paula", "Quinn", "Roy",
    "Senna", "Theo", "Uma", "Victor", "Wendy", "Xavier", "Yara",
]
PROFESSIONS = [
    "Astronaut", "Cook", "Guard", "Detective", "Baker", "Driver", "Writer",
    "Painter", "Tailor", "Pilot", "Nurse", "Farmer",
]


# ---------------------------------------------------------------------------
# Tiện ích tọa độ
# ---------------------------------------------------------------------------
def cell_ids(size: int) -> List[str]:
    """Danh sách mã ô theo thứ tự row-major: A1, B1, ..., A2, B2, ..."""
    return [f"{chr(ord('A') + c)}{r}" for r in range(1, size + 1) for c in range(size)]


def neighbors(cid: str, size: int) -> List[str]:
    col, row = ord(cid[0]) - ord("A"), int(cid[1:])
    out = []
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0:
                continue
            nr, nc = row + dr, col + dc
            if 1 <= nr <= size and 0 <= nc < size:
                out.append(f"{chr(ord('A') + nc)}{nr}")
    return out


def row_cells(row: int, size: int) -> List[str]:
    return [f"{chr(ord('A') + c)}{row}" for c in range(size)]


def col_cells(col: str, size: int) -> List[str]:
    return [f"{col}{r}" for r in range(1, size + 1)]


# ---------------------------------------------------------------------------
# Sinh clue ĐÚNG với đáp án
# ---------------------------------------------------------------------------
def _count(cells: List[str], solution: Dict[str, bool]) -> int:
    return sum(solution[c] for c in cells)


def _plural(n: int, singular: str, plural: str) -> str:
    return singular if n == 1 else plural


def random_clue(cid: str, size: int, solution: Dict[str, bool],
                names: Dict[str, str], rng: random.Random) -> Dict[str, Any]:
    """Sinh một clue raw (định dạng engine đọc được) và luôn đúng với `solution`."""
    kinds = ["EXACTLY_NEIGH", "EXACTLY_ROW", "EXACTLY_COL", "AT_LEAST", "AT_MOST",
             "SAME_DIFF", "FACT"]
    weights = [3.0, 2.0, 2.0, 1.0, 1.0, 1.5, 0.3]
    kind = rng.choices(kinds, weights)[0]
    ids = cell_ids(size)
    label = f"{names[cid]} ({cid})"

    if kind == "EXACTLY_NEIGH":
        region = neighbors(cid, size)
        k = _count(region, solution)
        return {"type": "EXACTLY", "count": k,
                "region": {"type": "NEIGHBORS", "params": cid},
                "text": f"Exactly {k} {_plural(k, 'neighbor', 'neighbors')} of {label} "
                        f"{_plural(k, 'is a Criminal', 'are Criminals')}."}

    if kind == "EXACTLY_ROW":
        r = rng.randint(1, size)
        k = _count(row_cells(r, size), solution)
        return {"type": "EXACTLY", "count": k,
                "region": {"type": "ROW", "params": r},
                "text": f"Exactly {k} {_plural(k, 'person', 'people')} in Row {r} "
                        f"{_plural(k, 'is a Criminal', 'are Criminals')}."}

    if kind == "EXACTLY_COL":
        col = chr(ord("A") + rng.randrange(size))
        k = _count(col_cells(col, size), solution)
        return {"type": "EXACTLY", "count": k,
                "region": {"type": "COL", "params": col},
                "text": f"Exactly {k} {_plural(k, 'person', 'people')} in Column {col} "
                        f"{_plural(k, 'is a Criminal', 'are Criminals')}."}

    if kind in ("AT_LEAST", "AT_MOST"):
        region = neighbors(cid, size)
        actual = _count(region, solution)
        if kind == "AT_LEAST":
            k = max(0, actual - rng.choice([0, 0, 1]))
            return {"type": "AT_LEAST", "count": k,
                    "region": {"type": "NEIGHBORS", "params": cid},
                    "text": f"At least {k} neighbors of {label} are Criminals."}
        k = min(len(region), actual + rng.choice([0, 0, 1]))
        return {"type": "AT_MOST", "count": k,
                "region": {"type": "NEIGHBORS", "params": cid},
                "text": f"At most {k} neighbors of {label} are Criminals."}

    if kind == "SAME_DIFF":
        other = rng.choice([c for c in ids if c != cid])
        same = solution[cid] == solution[other]
        return {"type": "SAME" if same else "DIFFERENT",
                "character1": cid, "character2": other,
                "text": f"{names[cid]} ({cid}) and {names[other]} ({other}) have "
                        f"{'the same' if same else 'different'} statuses."}

    other = rng.choice([c for c in ids if c != cid])        # FACT
    status = "CRIMINAL" if solution[other] else "INNOCENT"
    return {"type": "FACT", "character": other, "status": status,
            "text": f"{names[other]} ({other}) is {'a Criminal' if solution[other] else 'Innocent'}."}


# ---------------------------------------------------------------------------
# Ghép dữ liệu puzzle và đánh giá
# ---------------------------------------------------------------------------
def build_data(size: int, solution: Dict[str, bool], starter: str,
               clues: Dict[str, Dict[str, Any]], names: Dict[str, str],
               professions: Dict[str, str]) -> Dict[str, Any]:
    cells = []
    for cid in cell_ids(size):
        cells.append({
            "id": cid,
            "name": names[cid],
            "profession": professions[cid],
            "status": "CRIMINAL" if solution[cid] else "INNOCENT",
            "is_revealed": cid == starter,
            "clue": clues[cid],
        })
    return {"size": size, "cells": cells}


def evaluate(data: Dict[str, Any]) -> Tuple[int, str, Dict[str, Any], List[str]]:
    """Chạy agent trên puzzle. Trả về (số thẻ đã lật, trạng thái, uniqueness, id thẻ đã lật)."""
    engine = GameEngine(puzzle_data=data)
    engine.oracle = SATOracle(timeout=5.0)
    agent = DeductiveAgent(engine)
    status = agent.run()
    revealed = [cid for cid, cell in engine.state.board.items() if cell.get("is_revealed")]
    uniq = engine.check_clue_set_uniqueness() if status == "SOLVED" else {"unique": False}
    return len(revealed), status, uniq, revealed


def generate_puzzle(size: int, seed: int, max_iters: int = 400) -> Optional[Tuple[Dict[str, Any], Dict[str, Any]]]:
    """Sinh một puzzle hợp lệ từ `seed`. Trả về (data, báo cáo) hoặc None nếu thất bại."""
    rng = random.Random(seed)
    ids = cell_ids(size)
    total = len(ids)

    while True:                                   # bảo đảm có cả CRIMINAL lẫn INNOCENT
        solution = {c: rng.random() < 0.45 for c in ids}
        if 0 < sum(solution.values()) < total:
            break

    shuffled = rng.sample(NAMES, total)
    names = {cid: shuffled[i] for i, cid in enumerate(ids)}
    professions = {cid: rng.choice(PROFESSIONS) for cid in ids}
    starter = rng.choice(ids)
    clues = {cid: random_clue(cid, size, solution, names, rng) for cid in ids}

    best = -1
    for it in range(1, max_iters + 1):
        data = build_data(size, solution, starter, clues, names, professions)
        n_revealed, status, uniq, revealed = evaluate(data)
        if status == "SOLVED" and uniq.get("unique") and uniq.get("matches_hidden_solution"):
            return data, {"seed": seed, "iterations": it, "starter": starter}
        if n_revealed >= best:                    # chấp nhận thay đổi không làm tệ đi
            best = n_revealed
            snapshot = dict(clues)
        else:                                     # tệ hơn -> hoàn tác
            clues = dict(snapshot)
        # Đổi clue của một thẻ đã lật (chỉ clue của thẻ đã lật mới giúp suy diễn tiếp)
        target = rng.choice(revealed)
        clues[target] = random_clue(target, size, solution, names, rng)
    return None


def make_set(size: int, count: int, base_seed: int, out_dir: str,
             failures: bool = True) -> List[Dict[str, Any]]:
    reports = []
    seed = base_seed
    made = 0
    attempts = 0
    while made < count and attempts < 200:
        attempts += 1
        seed += 1
        result = generate_puzzle(size, seed)
        if result is None:
            continue
        data, report = result
        made += 1
        data["meta"] = {"seed": seed, "size": size}
        fault = FAULTS.get((size, made)) if failures else None
        if fault:
            inject_failure(data, fault)
        path = os.path.join(out_dir, f"{size}x{size}_{made:02d}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        report.update({"file": path, "attempt_count": attempts})
        reports.append(report)
        print(f"  [OK] {path}  seed={seed}  iterations={report['iterations']}")
    if made < count:
        print(f"  [CẢNH BÁO] Chỉ tạo được {made}/{count} puzzle {size}x{size}. "
              f"Hãy tăng max_iters hoặc đổi --seed.")
    return reports


# Vị trí (size, thứ tự) trong bộ puzzle sẽ bị cố tình làm hỏng -> thành ca thất bại.
FAULTS = {(3, 4): "STUCK", (3, 5): "ERROR", (4, 5): "TIMEOUT"}


def inject_failure(data: Dict[str, Any], kind: str) -> None:
    """Biến một puzzle hợp lệ thành ca thất bại; ghi `meta.expected` để đối chiếu."""
    if kind == "STUCK":                        # mọi clue vô nghĩa -> agent kẹt
        for c in data["cells"]:
            c["clue"] = {"type": "AT_LEAST", "count": 0,
                         "region": {"type": "NEIGHBORS", "params": c["id"]},
                         "text": f"At least 0 neighbors of {c['name']} ({c['id']}) are Criminals."}
    elif kind == "ERROR":                      # loại clue không tồn tại -> exception
        for c in data["cells"]:
            if c["is_revealed"]:
                c["clue"] = {"type": "BOGUS", "text": "This clue type does not exist."}
    elif kind == "TIMEOUT":                    # timeout SAT cực nhỏ (experiments.py đọc meta.timeout)
        data["meta"]["timeout"] = 1e-6
    data["meta"]["expected"] = kind


def main() -> None:
    parser = argparse.ArgumentParser(description="Sinh bộ puzzle Griductive.")
    parser.add_argument("--out", default="puzzles", help="Thư mục xuất file JSON")
    parser.add_argument("--seed", type=int, default=2026, help="Seed gốc")
    parser.add_argument("--counts", nargs="*", default=["3:5", "4:5", "5:1"],
                        help="Danh sách kích thước:số_lượng, ví dụ 3:5 4:5 5:1")
    parser.add_argument("--no-failures", action="store_true",
                        help="Không cài các ca thất bại (STUCK/ERROR/TIMEOUT) vào bộ puzzle")
    args = parser.parse_args()

    os.makedirs(args.out, exist_ok=True)
    for item in args.counts:
        size_str, count_str = item.split(":")
        size, count = int(size_str), int(count_str)
        print(f"Sinh {count} puzzle {size}x{size} ...")
        make_set(size, count, args.seed + size * 1000, args.out, not args.no_failures)


if __name__ == "__main__":
    main()