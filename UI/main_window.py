from __future__ import annotations

import random
import tkinter as tk
from dataclasses import dataclass, field
from tkinter import messagebox
from typing import Any, Optional

try:
    from Source.game_engine import GameEngine
except (ImportError, ModuleNotFoundError):
    GameEngine = None  # type: ignore[assignment]

try:
    from UI.components import BoardPanel, StatusBar, COLORS
except (ImportError, ModuleNotFoundError):
    from components import BoardPanel, StatusBar, COLORS


@dataclass
class MockClue:
    text: str
    related_cells: list[tuple[int, int]] = field(default_factory=list)


@dataclass
class MockCell:
    name: str
    profession: str
    solution: str
    clue: MockClue
    avatar_colors: tuple[str, str, str]
    hair_style: int = 0
    revealed: bool = False
    verdict: Optional[str] = None
    starter: bool = False


@dataclass
class MockState:
    board: list[list[MockCell]]
    solved: int = 0
    mistakes: int = 0


class MockGameEngine:
    """Engine mô phỏng để giao diện có thể chạy độc lập."""

    NAMES = [
        "Ada", "Bea", "Cody", "Dana",
        "Evan", "Finn", "Gus", "Hannah",
        "Ike", "Jonas", "Kobe", "Lucy",
        "Mason", "Nina", "Otis", "Paul",
        "Quilla", "Roy", "Senna", "Theo",
    ]
    PROFESSIONS = [
        "Keeper", "Driver", "Host", "Writer",
        "Driver", "Grocer", "Driver", "Writer",
        "Fitter", "Driver", "Grocer", "Host",
        "Writer", "Taster", "Keeper", "Taster",
        "Host", "Grocer", "Grocer", "Fitter",
    ]
    AVATAR_COLORS = [
        ("#A85C36", "#42231E", "#222222"),
        ("#9B654B", "#6B3D31", "#E5AD09"),
        ("#D3A172", "#C18B45", "#E9F2F1"),
        ("#B66C4A", "#5A2C24", "#E49A3A"),
        ("#C99A70", "#E4C37B", "#1F7C42"),
        ("#825437", "#B77A36", "#173F85"),
        ("#B96F50", "#A54E25", "#174A91"),
        ("#E7B792", "#251713", "#E6538B"),
    ]

    def __init__(self) -> None:
        self.starter_cell: Optional[tuple[int, int]] = None
        self.state = self._create_state()

    def _create_state(self) -> MockState:
        solutions = [
            "INNOCENT", "INNOCENT", "CRIMINAL", "INNOCENT",
            "CRIMINAL", "INNOCENT", "CRIMINAL", "INNOCENT",
            "INNOCENT", "CRIMINAL", "INNOCENT", "CRIMINAL",
            "INNOCENT", "INNOCENT", "CRIMINAL", "INNOCENT",
            "CRIMINAL", "INNOCENT", "INNOCENT", "CRIMINAL",
        ]
        board: list[list[MockCell]] = []

        for row in range(5):
            board_row: list[MockCell] = []
            for col in range(4):
                index = row * 4 + col
                related = self._adjacent_cells(row, col)
                innocent_count = sum(
                    solutions[r * 4 + c] == "INNOCENT" for r, c in related
                )
                clue_text = (
                    f"Exactly {innocent_count} adjacent "
                    f"card{'s are' if innocent_count != 1 else ' is'} innocent."
                )
                board_row.append(
                    MockCell(
                        name=self.NAMES[index],
                        profession=self.PROFESSIONS[index],
                        solution=solutions[index],
                        clue=MockClue(clue_text, related),
                        avatar_colors=self.AVATAR_COLORS[index % len(self.AVATAR_COLORS)],
                        hair_style=index % 4,
                    )
                )
            board.append(board_row)

        state = MockState(board=board)
        self._reveal_random_starter(state)
        return state

    @staticmethod
    def _adjacent_cells(row: int, col: int) -> list[tuple[int, int]]:
        result = []
        for delta_row, delta_col in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            new_row = row + delta_row
            new_col = col + delta_col
            if 0 <= new_row < 5 and 0 <= new_col < 4:
                result.append((new_row, new_col))
        return result

    def _reveal_random_starter(self, state: MockState) -> None:
        row, col = random.choice(
            [(r, c) for r in range(5) for c in range(4)]
        )
        cell = state.board[row][col]
        cell.revealed = True
        cell.verdict = cell.solution
        cell.starter = True
        state.solved = 1
        self.starter_cell = (row, col)

    def reset(self) -> None:
        self.state = self._create_state()

    def submit_verdict(self, row: int, col: int, verdict: str) -> str:
        cell = self.state.board[row][col]
        if cell.revealed:
            return "ALREADY_REVEALED"
        if cell.solution != verdict:
            self.state.mistakes += 1
            return "CONTRADICTED"

        cell.revealed = True
        cell.verdict = verdict
        self.state.solved += 1
        return "ACCEPTED"

    def hint(self) -> Optional[tuple[int, int]]:
        hidden_cells = [
            (row, col)
            for row, board_row in enumerate(self.state.board)
            for col, cell in enumerate(board_row)
            if not cell.revealed
        ]
        return random.choice(hidden_cells) if hidden_cells else None


class VerdictDialog(tk.Toplevel):
    """Hộp thoại chọn INNOCENT hoặc CRIMINAL cho một thẻ."""

    def __init__(
        self,
        parent: tk.Misc,
        cell: Any,
        coordinate: str,
        callback: Any,
    ) -> None:
        super().__init__(parent)
        self.callback = callback
        self.title("Mark card")
        self.configure(bg=COLORS["page"])
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        width, height = 360, 290
        parent.update_idletasks()
        x = parent.winfo_rootx() + parent.winfo_width() // 2 - width // 2
        y = parent.winfo_rooty() + parent.winfo_height() // 2 - height // 2
        self.geometry(f"{width}x{height}+{x}+{y}")

        tk.Label(
            self,
            text=coordinate,
            bg=COLORS["page"],
            fg=COLORS["muted"],
            font=("Segoe UI", 10, "bold"),
        ).pack(pady=(24, 4))
        tk.Label(
            self,
            text=getattr(cell, "name", "Unknown"),
            bg=COLORS["page"],
            fg=COLORS["ink"],
            font=("Segoe UI", 22, "bold"),
        ).pack()
        tk.Label(
            self,
            text=getattr(cell, "profession", "Unknown"),
            bg=COLORS["page"],
            fg=COLORS["muted"],
            font=("Consolas", 10, "bold"),
        ).pack(pady=(2, 20))
        tk.Label(
            self,
            text="What can you logically conclude?",
            bg=COLORS["page"],
            fg=COLORS["ink"],
            font=("Segoe UI", 11),
        ).pack()

        button_frame = tk.Frame(self, bg=COLORS["page"])
        button_frame.pack(fill="x", padx=28, pady=18)
        self._create_button(
            button_frame,
            "INNOCENT",
            COLORS["innocent"],
            lambda: self._choose("INNOCENT"),
        ).pack(side="left", expand=True, fill="x", padx=(0, 5))
        self._create_button(
            button_frame,
            "CRIMINAL",
            COLORS["criminal"],
            lambda: self._choose("CRIMINAL"),
        ).pack(side="left", expand=True, fill="x", padx=(5, 0))

        tk.Button(
            self,
            text="Cancel",
            command=self.destroy,
            bg=COLORS["page"],
            fg=COLORS["muted"],
            activebackground=COLORS["page"],
            relief="flat",
            cursor="hand2",
        ).pack()

    @staticmethod
    def _create_button(parent: tk.Misc, text: str, color: str, command: Any) -> tk.Button:
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=color,
            fg="white",
            activebackground=color,
            activeforeground="white",
            font=("Segoe UI", 10, "bold"),
            relief="flat",
            borderwidth=0,
            pady=11,
            cursor="hand2",
        )

    def _choose(self, verdict: str) -> None:
        self.destroy()
        self.callback(verdict)


class MainWindow:
    """Cửa sổ cấp cao nhất, kết nối UI với game engine."""

    def __init__(
        self,
        root: Optional[Any] = None,
        game_engine: Optional[Any] = None,
    ) -> None:
        self.root = root or tk.Tk()
        self.root.title("Griductive")
        self.root.geometry("690x900")
        self.root.minsize(590, 760)
        self.root.configure(bg=COLORS["page"])

        if game_engine is not None:
            self.game_engine = game_engine
        elif GameEngine is not None:
            try:
                self.game_engine = GameEngine()
            except Exception:
                self.game_engine = MockGameEngine()
        else:
            self.game_engine = MockGameEngine()

        self.board_panel: Optional[BoardPanel] = None
        self.status_bar: Optional[StatusBar] = None
        self.selected_cell: Optional[tuple[int, int]] = None
        self.counter_label: Optional[tk.Label] = None

        self.build_ui()
        self.bind_events()
        self.refresh()
        self.root.after(200, self._show_starter_clue)

    def build_ui(self) -> None:
        """Xây dựng bố cục giao diện."""
        header = tk.Frame(self.root, bg=COLORS["page"])
        header.pack(fill="x", padx=18, pady=(12, 4))

        tk.Label(
            header,
            text="GRIDUCTIVE",
            bg=COLORS["page"],
            fg=COLORS["ink"],
            font=("Segoe UI", 17, "bold"),
        ).pack(side="left")

        self.counter_label = tk.Label(
            header,
            text="",
            bg=COLORS["page"],
            fg=COLORS["muted"],
            font=("Segoe UI", 9, "bold"),
        )
        self.counter_label.pack(side="right")

        board_container = tk.Frame(self.root, bg=COLORS["page"])
        board_container.pack(fill="both", expand=True, padx=18, pady=4)
        self.board_panel = BoardPanel(board_container, width=650, height=750)

        controls = tk.Frame(self.root, bg=COLORS["page"])
        controls.pack(pady=(5, 8))
        self._create_control_button(controls, "✎  Mark", self.mark_selected).pack(
            side="left", padx=5
        )
        self._create_control_button(controls, "◔  Hint", self.show_hint).pack(
            side="left", padx=5
        )
        self._create_control_button(controls, "↻  Restart", self.start_new_game).pack(
            side="left", padx=5
        )

        self.status_bar = StatusBar(self.root)
        self.update_status("Game ready")

    def _create_control_button(
        self,
        parent: tk.Misc,
        text: str,
        command: Any,
    ) -> tk.Button:
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=COLORS["card"],
            fg=COLORS["ink"],
            activebackground=COLORS["selected"],
            activeforeground=COLORS["ink"],
            font=("Segoe UI", 10, "bold"),
            relief="solid",
            borderwidth=2,
            padx=20,
            pady=7,
            cursor="hand2",
        )

    def bind_events(self) -> None:
        """Kết nối callback bằng API bind_click ban đầu."""
        if self.board_panel is not None:
            self.board_panel.bind_click(self.handle_board_click)
        self.root.bind("<Control-r>", lambda _event: self.start_new_game())
        self.root.bind("<Escape>", lambda _event: self.clear_selection())

    def refresh(self) -> None:
        if self.board_panel is not None:
            self.board_panel.render(self.game_engine.state)

        board = getattr(self.game_engine.state, "board", [])
        total = sum(len(row) for row in board)
        solved = getattr(self.game_engine.state, "solved", self._count_revealed(board))
        mistakes = getattr(self.game_engine.state, "mistakes", 0)
        if self.counter_label is not None:
            self.counter_label.config(
                text=f"{solved}/{total} solved  •  {mistakes} errors"
            )

    @staticmethod
    def _count_revealed(board: Any) -> int:
        return sum(
            bool(getattr(cell, "revealed", False))
            for row in board
            for cell in row
        )

    def start_new_game(self) -> None:
        """Reset game và tự động hiển thị manh mối mở đầu ngẫu nhiên."""
        self.game_engine.reset()
        self.selected_cell = None
        if self.board_panel is not None:
            self.board_panel.selected_cell = None
            self.board_panel.highlighted_cells.clear()
        self.refresh()
        self._show_starter_clue()

    def _show_starter_clue(self) -> None:
        starter = getattr(self.game_engine, "starter_cell", None)
        if starter is None:
            starter = self._find_revealed_starter()
        if starter is None:
            self.update_status("Game started. Select a card to make a deduction.")
            return

        row, col = starter
        cell = self.game_engine.state.board[row][col]
        related = self._get_related_cells(cell)
        if self.board_panel is not None:
            self.board_panel.set_selected(row, col)
            self.board_panel.set_highlighted(related)
        self.selected_cell = (row, col)
        self.update_status(
            f"Starter clue opened at {chr(65 + col)}{row + 1}: "
            f"{self._get_clue_text(cell)}"
        )

    def _find_revealed_starter(self) -> Optional[tuple[int, int]]:
        board = getattr(self.game_engine.state, "board", [])
        for row, board_row in enumerate(board):
            for col, cell in enumerate(board_row):
                if getattr(cell, "starter", False):
                    return row, col
        for row, board_row in enumerate(board):
            for col, cell in enumerate(board_row):
                if getattr(cell, "revealed", False):
                    return row, col
        return None

    def handle_board_click(self, event: Any) -> None:
        """Nhận event từ BoardPanel.bind_click() và xử lý thẻ được chọn."""
        row = getattr(event, "board_row", None)
        col = getattr(event, "board_col", None)

        if row is None or col is None:
            if self.board_panel is None:
                return
            position = self.board_panel.get_clicked_cell(event.x, event.y)
            if position is None:
                return
            row, col = position

        self.selected_cell = (row, col)
        if self.board_panel is not None:
            self.board_panel.set_selected(row, col)

        cell = self.game_engine.state.board[row][col]
        if getattr(cell, "revealed", False):
            related = self._get_related_cells(cell)
            if self.board_panel is not None:
                self.board_panel.set_highlighted(related)
            self.update_status(self._get_clue_text(cell))
            return

        if self.board_panel is not None:
            self.board_panel.clear_highlight()
        self._open_verdict_dialog(row, col)

    def mark_selected(self) -> None:
        if self.selected_cell is None:
            self.update_status("Choose an unrevealed card first.")
            return

        row, col = self.selected_cell
        cell = self.game_engine.state.board[row][col]
        if getattr(cell, "revealed", False):
            self.update_status("This card is already open.")
            return
        self._open_verdict_dialog(row, col)

    def _open_verdict_dialog(self, row: int, col: int) -> None:
        cell = self.game_engine.state.board[row][col]
        coordinate = f"{chr(65 + col)}{row + 1}"
        VerdictDialog(
            self.root,
            cell,
            coordinate,
            lambda verdict: self._submit_verdict(row, col, verdict),
        )

    def _submit_verdict(self, row: int, col: int, verdict: str) -> None:
        result = self.game_engine.submit_verdict(row, col, verdict)
        self.refresh()

        if result == "ACCEPTED":
            cell = self.game_engine.state.board[row][col]
            related = self._get_related_cells(cell)
            if self.board_panel is not None:
                self.board_panel.set_selected(row, col)
                self.board_panel.set_highlighted(related)
            self.update_status(
                f"Correct deduction. Clue: {self._get_clue_text(cell)}"
            )
        elif result == "CONTRADICTED":
            self.update_status("CONTRADICTED: that conclusion does not follow.")
        elif result == "NOT_PROVABLE":
            self.update_status("NOT PROVABLE: more evidence is required.")
        elif result == "ALREADY_REVEALED":
            self.update_status("This card is already open.")
        else:
            self.update_status(f"Engine response: {result}")

        board = getattr(self.game_engine.state, "board", [])
        total = sum(len(board_row) for board_row in board)
        if self._count_revealed(board) == total and total > 0:
            messagebox.showinfo(
                "Griductive",
                "All cards have been resolved.",
                parent=self.root,
            )

    def show_hint(self) -> None:
        hint_method = getattr(self.game_engine, "hint", None)
        if hint_method is None:
            self.update_status("Hint is not supported by the current engine.")
            return

        hint = hint_method()
        if hint is None:
            self.update_status("All cards are already open.")
            return

        if isinstance(hint, tuple) and len(hint) >= 2:
            row, col = int(hint[0]), int(hint[1])
            self.selected_cell = (row, col)
            if self.board_panel is not None:
                self.board_panel.set_selected(row, col)
            self.update_status(
                f"Consider card {chr(65 + col)}{row + 1} and the revealed clues."
            )
        else:
            self.update_status(str(hint))

    def clear_selection(self) -> None:
        self.selected_cell = None
        if self.board_panel is not None:
            self.board_panel.set_selected(None, None)
            self.board_panel.clear_highlight()
        self.update_status("Selection cleared.")

    @staticmethod
    def _get_related_cells(cell: Any) -> list[tuple[int, int]]:
        clue = getattr(cell, "clue", None)
        related = getattr(clue, "related_cells", []) if clue is not None else []
        return [tuple(position) for position in related]

    @staticmethod
    def _get_clue_text(cell: Any) -> str:
        clue = getattr(cell, "clue", None)
        if clue is None:
            return "No clue available."
        return str(getattr(clue, "text", clue))

    def update_status(self, message: str) -> None:
        if self.status_bar is not None:
            self.status_bar.set_text(message)

    def run(self) -> None:
        self.root.mainloop()


if __name__ == "__main__":
    MainWindow().run()
