"""Cửa sổ chính của Griductive.

Lớp `GriductiveApp` chỉ làm "keo dán": nhận thao tác của người chơi, gọi API công khai
của `GameEngine`, rồi đẩy kết quả sang các component trong `components.py`.
Không có luật chơi hay suy luận nào nằm ở đây.

API của engine được sử dụng:
    engine.state.board / .revealed_clues / .moves / .turn / .size / .verdicts
    engine.submit_verdict(cell_id, status)   -> dict {valid, result, message, ...}
    engine.get_hint()                        -> dict {character, name, status} | None
    engine.get_highlighted_cells(cell_id)    -> vùng của manh mối thuộc ô đã lật
    engine.evaluate_state() / is_game_over() -> tiến độ / kết thúc
    engine.reset() / load_puzzle(data)       -> Restart / Load puzzle
    engine.oracle.stats                      -> số liệu SAT solver (DPLL)

Auto solve dùng `Source.agent.DeductiveAgent` (agent.py KHÔNG bị sửa):
    agent.analyse(state)  -> {consistent, forced[{character, status, queries}], unknown}
`DeductiveAgent.run()` giải một mạch nên không thể làm animation; vì vậy lớp
`AutoSolveSession` bên dưới lặp lại đúng logic của run() nhưng mỗi lần chỉ nộp MỘT verdict,
đồng thời ghi vào agent.trace / agent.waves / agent.terminal như run() vẫn làm.
"""
import json
import sys
from pathlib import Path


def _ensure_project_root() -> Path:
    """Tìm thư mục gốc (chứa package `Source`) và đưa vào sys.path."""
    here = Path(__file__).resolve().parent
    for candidate in (here, *here.parents):
        if (candidate / "Source").is_dir():
            root = candidate
            break
    else:
        root = here.parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    return root


PROJECT_ROOT = _ensure_project_root()

import tkinter as tk
from tkinter import filedialog, messagebox
from typing import Any, Dict, Optional

from Source.agent import DeductiveAgent
from Source.dpll import SATTimeout
from Source.game_engine import (
    GameEngine,
    STATUS_CRIMINAL,
    STATUS_INNOCENT,
    VERDICT_ACCEPTED,
    VERDICT_ALREADY_REVEALED,
    VERDICT_CONTRADICTED,
    VERDICT_INCONSISTENT,
    VERDICT_INVALID,
    VERDICT_NOT_PROVABLE,
)

try:
    from components import (
        BG, BoardPanel, CluePanel, HeaderBar, HistoryPanel, InfoPanel, Legend,
        ProgressStrip, SolverPanel, StatusBar, TabView, TracePanel, VictoryOverlay, apply_theme,
    )
except ImportError:  # chạy dạng package: python -m GUI.main_window
    from .components import (
        BG, BoardPanel, CluePanel, HeaderBar, HistoryPanel, InfoPanel, Legend,
        ProgressStrip, SolverPanel, StatusBar, TabView, TracePanel, VictoryOverlay, apply_theme,
    )


# Mã kết quả của engine -> (tiêu đề ngắn, loại thông báo của StatusBar / HistoryPanel)
RESULT_UI = {
    VERDICT_ACCEPTED: ("Ruling accepted", "success"),
    VERDICT_NOT_PROVABLE: ("Not provable yet", "warn"),
    VERDICT_CONTRADICTED: ("Contradicted", "error"),
    VERDICT_ALREADY_REVEALED: ("Already ruled", "info"),
    VERDICT_INVALID: ("Invalid move", "error"),
    VERDICT_INCONSISTENT: ("Inconsistent knowledge base", "error"),
}

ARROW_STEPS = {"Left": (-1, 0), "Right": (1, 0), "Up": (0, -1), "Down": (0, 1)}

# Thời gian dừng giữa hai bước Auto solve (ms) theo SpeedControl
AUTO_DELAY_MS = {"Slow": 1300, "Normal": 750, "Fast": 250}

# Trạng thái kết thúc của DeductiveAgent -> (loại thông báo, nội dung)
AUTO_END = {
    "SOLVED": ("success", "Auto solve finished: every suspect was ruled by logic alone."),
    "STUCK": ("warn", "Auto solve stopped: no remaining verdict is forced by the revealed clues."),
    "INCONSISTENT": ("error", "Auto solve stopped: the knowledge base is inconsistent."),
    "REJECTED": ("error", "Auto solve stopped: the engine rejected a verdict the agent believed was forced."),
    "TIMEOUT": ("error", "Auto solve stopped: the SAT solver timed out."),
}


class AutoSolveSession:
    """Chạy vòng lặp của `DeductiveAgent.run()` từng verdict một.

    - Dùng lại `agent.analyse()` (phân loại bằng SAT) và `engine.submit_verdict()`.
    - Một "đợt" (wave) = tất cả verdict ép buộc tại thời điểm phân tích; các verdict trong
      đợt được nộp lần lượt, hết đợt mới phân tích lại, y hệt run().
    - Bản ghi trace có cùng khoá với run(): step, wave, active_clue_ids, sat_queries,
      character, verdict, revealed_clue, revealed_clue_text.
    """

    def __init__(self, engine: GameEngine):
        self.engine = engine
        self.agent = DeductiveAgent(engine)
        self._queue: list = []

    def step(self) -> Optional[Dict[str, Any]]:
        """Nộp đúng một verdict. Trả về bản ghi trace, hoặc None khi dừng (xem agent.terminal)."""
        agent = self.agent
        if agent.terminal is not None:
            return None
        try:
            if not self._queue:
                if self.engine.is_game_over():
                    agent.terminal = "SOLVED"
                    return None
                analysis = agent.analyse(self.engine.state)
                if not analysis["consistent"]:
                    agent.terminal = "INCONSISTENT"
                    return None
                if not analysis["forced"]:
                    agent.terminal = "STUCK"
                    return None
                agent.waves += 1
                self._queue = list(analysis["forced"])

            item = self._queue.pop(0)
            active = [c.get("id") for c in self.engine.state.revealed_clues]
            result = self.engine.submit_verdict(item["character"], item["status"])
            if result["result"] != "ACCEPTED":
                self._queue.clear()
                agent.terminal = "REJECTED"
                return None
            clue = result.get("revealed_clue") or {}
            entry = {
                "step": len(agent.trace) + 1, "wave": agent.waves,
                "active_clue_ids": active, "sat_queries": item["queries"],
                "character": item["character"], "verdict": item["status"],
                "revealed_clue": clue.get("id"), "revealed_clue_text": clue.get("text"),
            }
            agent.trace.append(entry)
            return entry
        except SATTimeout:
            self._queue.clear()
            agent.terminal = "TIMEOUT"
            return None


class GriductiveApp(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title("Griductive")
        self._place_window(1360, 860)
        self.minsize(1120, 720)
        apply_theme(self)

        self.engine = GameEngine()
        self.selected = None          # mã ô đang chọn, vd "B1"
        self.hint_cell = None         # mã ô đang được gợi ý
        self._victory_job = None

        self.session: Optional[AutoSolveSession] = None   # phiên Auto solve gần nhất
        self.auto_running = False
        self._auto_job = None
        self.agent_stats: Optional[Dict[str, int]] = None  # agent.max_stats của phiên gần nhất

        self._build_layout()
        self._bind_keys()
        self.refresh_ui()
        self.status.set("Pick a suspect to read their file. Rule only when the clues prove it.", "info")

    # ------------------------------------------------------------------ layout
    def _place_window(self, width: int, height: int) -> None:
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        width, height = min(width, sw - 80), min(height, sh - 120)
        self.geometry(f"{width}x{height}+{(sw - width) // 2}+{max((sh - height) // 3, 0)}")

    def _build_layout(self) -> None:
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.header = HeaderBar(
            self, on_load=self.load_puzzle, on_restart=self.restart,
            on_hint=self.show_hint, on_auto=self.toggle_auto_solve)
        self.header.grid(row=0, column=0, sticky="ew")

        body = tk.Frame(self, bg=BG)
        body.grid(row=1, column=0, sticky="nsew")
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(0, weight=1)

        # --- cột trái: tiến độ, bàn cờ, chú giải ---
        left = tk.Frame(body, bg=BG)
        left.grid(row=0, column=0, sticky="nsew", padx=(24, 12), pady=(16, 14))
        left.grid_rowconfigure(1, weight=1)
        left.grid_columnconfigure(0, weight=1)

        self.progress = ProgressStrip(left)
        self.progress.grid(row=0, column=0, sticky="ew")
        self.board = BoardPanel(left, self.engine, self.select_cell)
        self.board.grid(row=1, column=0, sticky="nsew")
        self.legend = Legend(left)
        self.legend.grid(row=2, column=0, pady=(6, 0))
        self.victory = VictoryOverlay(left, on_restart=self.restart)

        # --- cột phải: hồ sơ nhân vật + tab Clues / Trace / History / Solver ---
        right = tk.Frame(body, bg=BG, width=400)
        right.grid(row=0, column=1, sticky="ns", padx=(12, 24), pady=(16, 14))
        right.pack_propagate(False)

        self.info_panel = InfoPanel(right, on_verdict=self.submit)
        self.info_panel.pack(fill="x")

        self.tabs = TabView(right)
        self.tabs.pack(fill="both", expand=True, pady=(12, 0))
        self.clue_panel = CluePanel(self.tabs.add("Clues"), on_select=self.select_cell)
        self.clue_panel.pack(fill="both", expand=True)
        self.trace_panel = TracePanel(self.tabs.add("Trace"), on_select=self.select_cell,
                                      on_export=self.export_trace)
        self.trace_panel.pack(fill="both", expand=True)
        self.history = HistoryPanel(self.tabs.add("History"))
        self.history.pack(fill="both", expand=True)
        self.solver = SolverPanel(self.tabs.add("Solver"))
        self.solver.pack(fill="both", expand=True)

        self.status = StatusBar(self)
        self.status.grid(row=2, column=0, sticky="ew")

    def _bind_keys(self) -> None:
        self.bind("<Key>", self._on_key)
        self.bind("<Control-o>", lambda _e: self.load_puzzle())

    # ------------------------------------------------------------ đồng bộ UI
    def refresh_ui(self, animate=None) -> None:
        """Vẽ lại mọi thứ từ trạng thái công khai của engine."""
        state = self.engine.state
        board = state.board
        total = len(board)
        solved = sum(1 for cell in board.values() if cell.get("is_revealed"))

        self.progress.update_progress(solved, total, state.turn, self.engine.evaluate_state())
        self.board.refresh(animate=animate)

        newest = state.moves[-1]["character"] if state.moves else None
        self.clue_panel.update_clues(state.revealed_clues, board, newest_owner=newest)
        self.tabs.set_badge("Clues", len(state.revealed_clues))
        self.tabs.set_badge("Trace", self.trace_panel.count)
        self.tabs.set_badge("History", self.history.count)

        stats = getattr(self.engine.oracle, "stats", None)
        data = {key: getattr(stats, key, 0)
                for key in ("sat_calls", "decisions", "propagations", "backtracks", "runtime")}
        data.update(clues=len(state.revealed_clues), verdicts=len(state.verdicts), hidden=total - solved)
        peak = self.agent_stats or {}
        for key in ("primary_variables", "auxiliary_variables", "clauses"):
            data[key] = peak.get(key)          # None -> "-" cho tới khi chạy Auto solve
        self.solver.update_stats(data)

        self._update_controls()
        self._sync_view()

    def _update_controls(self) -> None:
        over = self.engine.is_game_over()
        self.header.set_hint_enabled(not over and not self.auto_running)
        self.header.set_auto_state(self.auto_running, enabled=self.auto_running or not over)

    def _sync_view(self) -> None:
        """Đồng bộ ô đang chọn: hồ sơ, vùng highlight của manh mối, danh sách clue."""
        cid = self.selected
        cell = self.engine.state.board.get(cid) if cid else None
        highlighted = []
        if cell is not None and cell.get("is_revealed"):
            try:
                highlighted = self.engine.get_highlighted_cells(cid)
            except KeyError:
                highlighted = []
        locked = self.engine.is_game_over() or self.auto_running
        self.info_panel.show_cell(cell, locked=locked)
        self.board.set_view(selected=cid if cell else None, highlighted=highlighted, hint=self.hint_cell)
        self.clue_panel.set_active(cid if cell is not None and cell.get("is_revealed") else None)

    # --------------------------------------------------------------- thao tác
    def select_cell(self, cid: str) -> None:
        if cid not in self.engine.state.board:
            return
        self.selected = cid
        self._sync_view()

    def submit(self, verdict: str) -> None:
        """Nộp phán quyết CRIMINAL / INNOCENT cho ô đang chọn."""
        if self.auto_running:
            self.status.set("Auto solve is running. Stop it to rule manually.", "warn")
            return
        if self.engine.is_game_over():
            return
        if self.selected is None:
            self.status.set("Select a suspect on the board first.", "warn")
            return

        cid = self.selected
        result = self.engine.submit_verdict(cid, verdict)
        code = result.get("result")
        title, kind = RESULT_UI.get(code, ("Result", "info"))
        message = result.get("message", "")

        self.status.set(message, kind)
        accepted = bool(result.get("valid"))
        turn = self.engine.state.turn
        self.history.add(kind, title, message, step=f"Move {turn}" if accepted else "")

        if accepted:
            self.hint_cell = None
            self.refresh_ui(animate=cid)
            if self.engine.is_game_over():
                self._schedule_victory()
        else:
            self.refresh_ui()
            self.board.shake(cid)

    def show_hint(self) -> None:
        if self.auto_running:
            return
        if self.engine.is_game_over():
            self.status.set("The puzzle is already solved.", "info")
            return
        hint = self.engine.get_hint()
        if hint is None:
            message = "The revealed clues don't prove anyone yet."
            self.status.set(message, "warn")
            self.history.add("warn", "No hint available", message)
            self.refresh_ui()
            return

        cid = hint["character"]
        message = f"Hint: {hint['name']} ({cid}) is provably {hint['status'].lower()}."
        self.selected = cid
        self.hint_cell = cid
        self.status.set(message, "hint")
        self.history.add("hint", "Hint", message)
        self.refresh_ui()

    def restart(self) -> None:
        self._stop_auto(announce=False)
        if self.engine.state.turn > 0 and not self.engine.is_game_over():
            if not messagebox.askyesno(
                    "Restart", "Discard your progress and start this puzzle again?", parent=self):
                return
        self.engine.reset()
        self._reset_session("Puzzle restarted.")

    def load_puzzle(self) -> None:
        self._stop_auto(announce=False)
        path = filedialog.askopenfilename(
            parent=self, title="Load puzzle", initialdir=str(PROJECT_ROOT),
            filetypes=[("Puzzle JSON", "*.json"), ("All files", "*.*")])
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            GameEngine(puzzle_data=data)      # dựng thử để bắt lỗi dữ liệu trước khi đụng vào game hiện tại
        except Exception as exc:
            messagebox.showerror(
                "Could not load puzzle",
                f"{Path(path).name}\n\n{exc}\n\nYour current game was not changed.", parent=self)
            return
        self.engine.load_puzzle(data)
        self._reset_session(f"Loaded {Path(path).name}.")

    def _reset_session(self, message: str) -> None:
        if self._victory_job is not None:
            self.after_cancel(self._victory_job)
            self._victory_job = None
        self._cancel_auto()
        self.session = None
        self.agent_stats = None
        self.victory.hide()
        self.selected = None
        self.hint_cell = None
        self.history.clear()
        self.trace_panel.clear()
        self.board.rebuild()
        self.refresh_ui()
        self.status.set(message, "info")

    # --------------------------------------------------------------- Auto solve
    def toggle_auto_solve(self) -> None:
        if self.auto_running:
            self._stop_auto()
        else:
            self.start_auto_solve()

    def start_auto_solve(self) -> None:
        """Chạy DeductiveAgent từng bước: mỗi bước chỉ nộp verdict mà các clue đã lật ép buộc."""
        if self.engine.is_game_over():
            self.status.set("The puzzle is already solved.", "info")
            return
        self.session = AutoSolveSession(self.engine)
        self.agent_stats = None
        self.hint_cell = None
        self.auto_running = True
        self.trace_panel.clear()
        self.trace_panel.set_state("RUNNING", "Submitting only verdicts that the revealed clues force.")
        self.tabs.select("Trace")
        self.status.set("Auto solve started. Only logically forced verdicts are submitted.", "info")
        self.refresh_ui()
        self._auto_job = self.after(350, self._auto_step)

    def _auto_step(self) -> None:
        self._auto_job = None
        if not self.auto_running or self.session is None:
            return
        try:
            entry = self.session.step()
        except Exception as exc:       # lỗi bất ngờ: dừng hẳn thay vì để chuỗi after chết âm thầm
            self._finish_auto(error=exc)
            return
        if entry is None:
            self._finish_auto()
            return

        cid, verdict = entry["character"], entry["verdict"]
        name = self.engine.state.board.get(cid, {}).get("name", cid)
        text = f"{name} ({cid}) is {verdict.lower()}."
        self.selected = cid
        self.status.set(f"Step {entry['step']}: {text} Forced by the revealed clues.", "success")
        self.history.add("success", "Auto solve", text, step=f"Move {self.engine.state.turn}")
        self.trace_panel.add_step(entry, name)
        self.refresh_ui(animate=cid)

        delay = 450 if self.engine.is_game_over() else AUTO_DELAY_MS.get(self.header.speed.get(), 750)
        self._auto_job = self.after(delay, self._auto_step)

    def _finish_auto(self, error: Optional[Exception] = None) -> None:
        self._auto_job = None
        self.auto_running = False
        session = self.session
        board = self.engine.state.board
        hidden = sum(1 for cell in board.values() if not cell.get("is_revealed"))

        if session is not None:
            self.agent_stats = dict(session.agent.max_stats)
            steps, waves = len(session.agent.trace), session.agent.waves
        else:
            steps = waves = 0

        if error is not None:
            kind, text, key = "error", f"Auto solve failed: {error}", "ERROR"
            summary = str(error)
        else:
            terminal = session.agent.terminal if session is not None else None
            key = terminal or "STOPPED"
            kind, text = AUTO_END.get(terminal, ("info", "Auto solve stopped."))
            summary = f"{steps} steps in {waves} waves."
            if terminal != "SOLVED":
                summary += f" {hidden} suspects still hidden."

        self.trace_panel.set_state(key, summary)
        self.status.set(text, kind)
        self.history.add(kind, "Auto solve", summary)
        self.refresh_ui()
        if key == "SOLVED" and self.engine.is_game_over():
            self._schedule_victory()

    def _cancel_auto(self) -> None:
        if self._auto_job is not None:
            self.after_cancel(self._auto_job)
            self._auto_job = None
        self.auto_running = False

    def _stop_auto(self, announce: bool = True) -> None:
        """Người dùng dừng Auto solve (nút Stop, Restart, Load). Không làm gì nếu đang không chạy."""
        if not self.auto_running:
            return
        self._cancel_auto()
        steps = waves = 0
        if self.session is not None:
            self.agent_stats = dict(self.session.agent.max_stats)
            steps, waves = len(self.session.agent.trace), self.session.agent.waves
        self.trace_panel.set_state("STOPPED", f"Stopped after {steps} steps in {waves} waves.")
        if announce:
            self.status.set("Auto solve stopped.", "info")
        self.refresh_ui()

    def export_trace(self) -> None:
        """Lưu deduction trace (và số liệu solver) ra JSON để đưa vào báo cáo."""
        agent = self.session.agent if self.session is not None else None
        if agent is None or not agent.trace:
            self.status.set("Run Auto solve first to record a deduction trace.", "warn")
            return
        path = filedialog.asksaveasfilename(
            parent=self, title="Export deduction trace", defaultextension=".json",
            initialfile="deduction_trace.json", filetypes=[("JSON", "*.json")])
        if not path:
            return
        stats = getattr(self.engine.oracle, "stats", None)
        payload = {
            "grid_size": self.engine.state.size,
            "terminal": agent.terminal or "STOPPED",
            "steps": len(agent.trace),
            "waves": agent.waves,
            "cnf_peak": dict(agent.max_stats),
            "sat": {key: getattr(stats, key, 0)
                    for key in ("sat_calls", "decisions", "propagations", "backtracks", "runtime")},
            "trace": agent.trace,
        }
        try:
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, ensure_ascii=False, indent=2)
        except OSError as exc:
            messagebox.showerror("Could not export trace", str(exc), parent=self)
            return
        self.status.set(f"Trace exported to {Path(path).name}.", "success")

    # --------------------------------------------------------------- chiến thắng
    def _schedule_victory(self) -> None:
        if self._victory_job is not None:
            self.after_cancel(self._victory_job)
        self._victory_job = self.after(560, self._show_victory)   # chờ hiệu ứng lật thẻ xong

    def _show_victory(self) -> None:
        self._victory_job = None
        self.victory.show(total=len(self.engine.state.board), turns=self.engine.state.turn)
        self.status.set("Case closed. Every suspect was ruled by logic alone.", "success")

    # ------------------------------------------------------------------ phím tắt
    def _on_key(self, event) -> None:
        if event.state & 0x4:            # bỏ qua tổ hợp Ctrl+phím (vd Ctrl+C)
            return
        key = event.keysym
        if key in ARROW_STEPS:
            self._move_selection(*ARROW_STEPS[key])
            return
        low = key.lower()
        if low == "c":
            self.submit(STATUS_CRIMINAL)
        elif low == "i":
            self.submit(STATUS_INNOCENT)
        elif low == "h":
            self.show_hint()
        elif low == "a":
            self.toggle_auto_solve()
        elif low == "r":
            self.restart()
        elif key == "Escape" and self.selected is not None:
            self.selected = None
            self._sync_view()

    def _move_selection(self, dc: int, dr: int) -> None:
        board = self.engine.state.board
        if not board:
            return
        if self.selected not in board:
            self.select_cell(next(iter(board)))
            return
        cell = board[self.selected]
        size = self.engine.state.size
        col = min(max(ord(cell["col"]) - ord("A") + dc, 0), size - 1)
        row = min(max(int(cell["row"]) - 1 + dr, 0), size - 1)
        target = f"{chr(ord('A') + col)}{row + 1}"
        if target in board:
            self.select_cell(target)


if __name__ == "__main__":
    GriductiveApp().mainloop()
