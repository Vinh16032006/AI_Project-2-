"""Thí nghiệm mục 4.5: đánh giá toàn hệ thống trên bộ puzzle 3x3, 4x4 (và 5x5).

Với MỖI puzzle và MỖI cấu hình solver, ghi lại:
  1. Số biến chính và biến phụ.
  2. Số mệnh đề CNF.
  3. Số lần gọi SAT.
  4. Decisions, propagations, backtracks.
  5. Số bước suy diễn và số đợt (wave) lật thẻ.
  6. Thời gian chạy.
Thất bại (STUCK, TIMEOUT, ERROR...) vẫn được ghi thành một dòng, không bị loại.
"""
from __future__ import annotations

import argparse
import csv
import glob
import json
import os
import statistics
import time
from typing import Any, Dict, List

from Source.agent import DeductiveAgent
from Source.dpll import SATOracle
from Source.game_engine import GameEngine

# Các cấu hình solver được so sánh (cùng một bộ puzzle cho tất cả).
CONFIGS = [
    {"name": "DPLL", "pure_literal": False},
    {"name": "DPLL+pure-literal", "pure_literal": True},
]

COLUMNS = [
    "puzzle", "size", "config", "status",
    "primary_vars", "aux_vars", "clauses",
    "sat_calls", "decisions", "propagations", "backtracks",
    "steps", "waves", "runtime_s", "unique", "expected",
]


def run_once(path: str, pure_literal: bool, timeout: float) -> Dict[str, Any]:
    """Chạy agent một lần trên một puzzle và trả về một dòng số liệu."""
    row: Dict[str, Any] = {col: "" for col in COLUMNS}
    row["puzzle"] = os.path.basename(path)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        row["size"] = data.get("size", "")
        row["expected"] = data.get("meta", {}).get("expected", "SOLVED")

        engine = GameEngine(puzzle_data=data)
        # Uniqueness kiểm tra bằng một oracle riêng để không tính vào số liệu của agent.
        row["unique"] = bool(engine.check_clue_set_uniqueness()["unique"])

        # Puzzle có thể khai báo timeout riêng (meta.timeout) để cố tình gây TIMEOUT.
        case_timeout = float(data.get("meta", {}).get("timeout", timeout))
        engine.oracle = SATOracle(enable_pure_literal=pure_literal, timeout=case_timeout)
        agent = DeductiveAgent(engine)
        start = time.perf_counter()
        status = agent.run()
        runtime = time.perf_counter() - start

        stats = engine.oracle.stats
        row.update({
            "status": status,
            "primary_vars": agent.max_stats["primary_variables"],
            "aux_vars": agent.max_stats["auxiliary_variables"],
            "clauses": agent.max_stats["clauses"],
            "sat_calls": stats.sat_calls,
            "decisions": stats.decisions,
            "propagations": stats.propagations,
            "backtracks": stats.backtracks,
            "steps": len(agent.trace),
            "waves": agent.waves,
            "runtime_s": runtime,
        })
    except Exception as exc:                      # ghi lại thay vì bỏ ca lỗi
        row["status"] = f"ERROR:{type(exc).__name__}"
        if not row["expected"]:
            row["expected"] = "ERROR"
    return row


def run_case(path: str, config: Dict[str, Any], timeout: float, repeats: int) -> Dict[str, Any]:
    """Chạy `repeats` lần; số đếm lấy từ lần đầu (tất định), runtime lấy trung vị."""
    rows = [run_once(path, config["pure_literal"], timeout) for _ in range(max(1, repeats))]
    row = rows[0]
    row["config"] = config["name"]
    runtimes = [r["runtime_s"] for r in rows if isinstance(r["runtime_s"], float)]
    if runtimes:
        row["runtime_s"] = statistics.median(runtimes)
    return row


def fmt(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def fmt_avg(value: Any) -> str:
    """Định dạng số trung bình: số đếm lấy 1 chữ số thập phân, bỏ phần .0."""
    if isinstance(value, float):
        text = f"{value:.1f}"
        return text[:-2] if text.endswith(".0") else text
    return str(value)


def summarize(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Tổng hợp theo (kích thước, cấu hình). Trung bình chỉ tính trên các ca SOLVED."""
    summary = []
    keys = sorted({(r["size"], r["config"]) for r in rows}, key=lambda k: (str(k[0]), k[1]))
    for size, config in keys:
        group = [r for r in rows if r["size"] == size and r["config"] == config]
        solved = [r for r in group if r["status"] == "SOLVED"]
        entry: Dict[str, Any] = {
            "size": f"{size}x{size}" if size != "" else "?", "config": config,
            "solved": f"{len(solved)}/{len(group)}",
            "failures": ", ".join(sorted({r["status"] for r in group if r["status"] != "SOLVED"})) or "-",
        }
        for col in ("primary_vars", "aux_vars", "clauses", "sat_calls", "decisions",
                    "propagations", "backtracks", "steps", "waves", "runtime_s"):
            values = [r[col] for r in solved if isinstance(r[col], (int, float))]
            entry[col] = statistics.mean(values) if values else "n/a"
        summary.append(entry)
    return summary


def write_csv(rows: List[Dict[str, Any]], path: str) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def md_table(headers: List[str], rows: List[List[str]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    lines += ["| " + " | ".join(r) + " |" for r in rows]
    return "\n".join(lines)


def write_markdown(rows: List[Dict[str, Any]], summary: List[Dict[str, Any]],
                   path: str, timeout: float, repeats: int) -> None:
    failed = [r for r in rows if r["status"] != "SOLVED"]
    parts = [
        "# Kết quả thí nghiệm (mục 4.5)",
        f"Timeout mỗi ca: {timeout}s. Runtime là trung vị của {repeats} lần chạy. "
        f"Tổng số ca: {len(rows)}; ca không giải được: {len(failed)}.",
        "",
        "## Tổng hợp theo kích thước (trung bình trên các ca SOLVED)",
        md_table(
            ["Size", "Config", "Solved", "Lỗi/timeout", "Biến chính", "Biến phụ", "Mệnh đề",
             "Gọi SAT", "Decisions", "Propagations", "Backtracks", "Bước", "Đợt", "Runtime (s)"],
            [[s["size"], s["config"], s["solved"], s["failures"], fmt_avg(s["primary_vars"]),
              fmt_avg(s["aux_vars"]), fmt_avg(s["clauses"]), fmt_avg(s["sat_calls"]),
              fmt_avg(s["decisions"]), fmt_avg(s["propagations"]), fmt_avg(s["backtracks"]),
              fmt_avg(s["steps"]), fmt_avg(s["waves"]), fmt(s["runtime_s"])] for s in summary],
        ),
        "",
        "## Chi tiết từng ca",
        md_table(COLUMNS, [[fmt(r[c]) for c in COLUMNS] for r in rows]),
    ]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(parts) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Chạy thí nghiệm 4.5.")
    parser.add_argument("--puzzles", default="puzzles", help="Thư mục chứa puzzle *.json")
    parser.add_argument("--out", default="results", help="Tiền tố file xuất (results -> results.csv/.md)")
    parser.add_argument("--timeout", type=float, default=30.0, help="Timeout SAT mỗi ca (giây)")
    parser.add_argument("--repeats", type=int, default=1, help="Số lần chạy để lấy trung vị runtime")
    args = parser.parse_args()

    files = sorted(glob.glob(os.path.join(args.puzzles, "*.json")))
    if not files:
        raise SystemExit(f"Không tìm thấy puzzle nào trong '{args.puzzles}'. Hãy chạy make_puzzles.py trước.")

    rows: List[Dict[str, Any]] = []
    for config in CONFIGS:                         # cùng danh sách `files` cho mọi cấu hình
        for path in files:
            row = run_case(path, config, args.timeout, args.repeats)
            rows.append(row)
            print(f"{config['name']:<18} {row['puzzle']:<14} {row['status']:<10} "
                  f"sat={row['sat_calls']!s:<5} dec={row['decisions']!s:<5} "
                  f"bt={row['backtracks']!s:<4} t={fmt(row['runtime_s'])}s")

    summary = summarize(rows)
    write_csv(rows, args.out + ".csv")
    write_markdown(rows, summary, args.out + ".md", args.timeout, args.repeats)
    print(f"\nĐã ghi {args.out}.csv và {args.out}.md ({len(rows)} ca).")


if __name__ == "__main__":
    main()