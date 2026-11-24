from __future__ import annotations

from typing import Any, Iterable, Optional

try:
    import tkinter as tk
except ImportError:  # pragma: no cover
    tk = None


COLORS = {
    "page": "#F3EDE2",
    "card": "#FBF8F1",
    "ink": "#302A27",
    "muted": "#776E66",
    "line": "#302A27",
    "shadow": "#C7BDB0",
    "selected": "#E7D8BD",
    "highlight": "#FFF1B8",
    "highlight_line": "#D49A00",
    "innocent": "#2F8A57",
    "innocent_fill": "#CDEBD8",
    "criminal": "#E21D1D",
    "criminal_fill": "#F5B5B2",
}


class BoardPanel:
    """Canvas chịu trách nhiệm vẽ bàn cờ và tương tác người dùng.

    Lớp này không kế thừa ``tk.Frame`` để giữ đúng cấu trúc ban đầu.
    Thuộc tính widget công khai vẫn là ``canvas``.
    """

    def __init__(self, parent: Any, width: int = 600, height: int = 600) -> None:
        self.parent = parent
        self.width = width
        self.height = height
        self.canvas: Optional[Any] = None

        self.state: Any = None
        self.board: Any = None
        self.selected_cell: Optional[tuple[int, int]] = None
        self.highlighted_cells: set[tuple[int, int]] = set()
        self._external_click_callback: Any = None
        self._layout: dict[str, float] = {}

        if tk is not None:
            self.canvas = tk.Canvas(
                self.parent,
                width=self.width,
                height=self.height,
                bg=COLORS["page"],
                highlightthickness=0,
                cursor="hand2",
            )
            self.canvas.pack(fill="both", expand=True)
            self.canvas.bind("<Configure>", self._handle_resize)

    def draw_board(self, board: Any) -> None:
        """Vẽ lưới thẻ nhân vật theo phong cách giao diện tham khảo."""
        if self.canvas is None:
            return

        self.board = board
        self.canvas.delete("all")

        if not board or not isinstance(board, (list, tuple)):
            self._draw_empty_state()
            return

        rows = len(board)
        cols = len(board[0]) if rows else 0
        if cols == 0:
            self._draw_empty_state()
            return

        canvas_width = max(self.canvas.winfo_width(), self.width)
        canvas_height = max(self.canvas.winfo_height(), self.height)
        gap = 8.0
        margin = 10.0

        card_width = min(
            145.0,
            (canvas_width - 2 * margin - gap * (cols - 1)) / cols,
        )
        card_height = min(
            150.0,
            (canvas_height - 2 * margin - gap * (rows - 1)) / rows,
        )
        card_width = max(card_width, 105.0)
        card_height = max(card_height, 118.0)

        total_width = cols * card_width + (cols - 1) * gap
        total_height = rows * card_height + (rows - 1) * gap
        start_x = max(margin, (canvas_width - total_width) / 2)
        start_y = max(margin, (canvas_height - total_height) / 2)

        self._layout = {
            "start_x": start_x,
            "start_y": start_y,
            "card_width": card_width,
            "card_height": card_height,
            "gap": gap,
            "rows": float(rows),
            "cols": float(cols),
        }

        for row_index, row in enumerate(board):
            for col_index, cell in enumerate(row):
                self._draw_card(cell, row_index, col_index)

    def render(self, state: Any) -> None:
        """Render trạng thái game hiện tại lên canvas."""
        self.state = state
        board = getattr(state, "board", None) if state is not None else None
        self.draw_board(board)

    def bind_click(self, callback: Any) -> None:
        """Đăng ký callback cho sự kiện click vào board.

        Callback cũ nhận nguyên ``event`` như bộ khung ban đầu. Trước khi gọi
        callback, BoardPanel gắn thêm ``event.board_row`` và
        ``event.board_col`` nếu vị trí click nằm trong một thẻ.
        """
        self._external_click_callback = callback
        if self.canvas is not None:
            self.canvas.bind("<Button-1>", self._dispatch_click)

    def set_selected(self, row: Optional[int], col: Optional[int]) -> None:
        """Chọn một thẻ; đây là API bổ sung và không ảnh hưởng API ban đầu."""
        if row is None or col is None:
            self.selected_cell = None
        else:
            self.selected_cell = (row, col)
        self.draw_board(self.board)

    def set_highlighted(self, cells: Iterable[tuple[int, int]]) -> None:
        """Highlight các thẻ được một manh mối tham chiếu."""
        self.highlighted_cells = set(cells)
        self.draw_board(self.board)

    def clear_highlight(self) -> None:
        self.highlighted_cells.clear()
        self.draw_board(self.board)

    def get_clicked_cell(self, x: float, y: float) -> Optional[tuple[int, int]]:
        """Chuyển tọa độ canvas thành ``(row, col)`` của thẻ được click."""
        if not self._layout:
            return None

        start_x = self._layout["start_x"]
        start_y = self._layout["start_y"]
        card_width = self._layout["card_width"]
        card_height = self._layout["card_height"]
        gap = self._layout["gap"]
        rows = int(self._layout["rows"])
        cols = int(self._layout["cols"])

        col = int((x - start_x) // (card_width + gap))
        row = int((y - start_y) // (card_height + gap))
        if not (0 <= row < rows and 0 <= col < cols):
            return None

        card_x = start_x + col * (card_width + gap)
        card_y = start_y + row * (card_height + gap)
        if card_x <= x <= card_x + card_width and card_y <= y <= card_y + card_height:
            return row, col
        return None

    def _dispatch_click(self, event: Any) -> None:
        position = self.get_clicked_cell(event.x, event.y)
        if position is not None:
            event.board_row, event.board_col = position
        else:
            event.board_row, event.board_col = None, None

        if self._external_click_callback is not None:
            self._external_click_callback(event)

    def _handle_resize(self, _event: Any) -> None:
        if self.board is not None:
            self.draw_board(self.board)

    def _draw_card(self, cell: Any, row: int, col: int) -> None:
        if self.canvas is None:
            return

        layout = self._layout
        card_width = layout["card_width"]
        card_height = layout["card_height"]
        gap = layout["gap"]
        x1 = layout["start_x"] + col * (card_width + gap)
        y1 = layout["start_y"] + row * (card_height + gap)
        x2 = x1 + card_width
        y2 = y1 + card_height
        tag = f"cell:{row}:{col}"

        revealed = bool(getattr(cell, "revealed", False))
        verdict = getattr(cell, "verdict", None)
        selected = self.selected_cell == (row, col)
        highlighted = (row, col) in self.highlighted_cells

        fill = COLORS["card"]
        outline = COLORS["line"]
        outline_width = 2

        if revealed and verdict == "CRIMINAL":
            fill, outline = COLORS["criminal_fill"], COLORS["criminal"]
        elif revealed and verdict == "INNOCENT":
            fill, outline = COLORS["innocent_fill"], COLORS["innocent"]
        elif highlighted:
            fill, outline = COLORS["highlight"], COLORS["highlight_line"]
        elif selected:
            fill, outline = COLORS["selected"], COLORS["ink"]
            outline_width = 3

        self._rounded_rectangle(
            x1 + 2, y1 + 3, x2 + 2, y2 + 4,
            radius=12,
            fill=COLORS["shadow"],
            outline="",
            tags=(tag, "card"),
        )
        self._rounded_rectangle(
            x1, y1, x2, y2,
            radius=12,
            fill=fill,
            outline=outline,
            width=outline_width,
            tags=(tag, "card"),
        )

        coordinate = f"{chr(65 + col)}{row + 1}"
        self.canvas.create_text(
            x1 + 7, y1 + 7,
            text=coordinate,
            anchor="nw",
            fill=COLORS["muted"],
            font=("Segoe UI", 8, "bold"),
            tags=(tag,),
        )

        if revealed:
            marker = "!" if verdict == "CRIMINAL" else "✓"
            self.canvas.create_text(
                x2 - 8, y1 + 7,
                text=marker,
                anchor="ne",
                fill=outline,
                font=("Segoe UI", 10, "bold"),
                tags=(tag,),
            )

        clue = getattr(cell, "clue", None)
        if revealed and clue is not None:
            self._draw_avatar(x1 + 23, y1 + 29, cell, tag, scale=0.45)
            self.canvas.create_text(
                x1 + 43, y1 + 15,
                text=getattr(cell, "name", "Unknown"),
                anchor="nw",
                fill=COLORS["ink"],
                font=("Segoe UI", 10, "bold"),
                width=card_width - 50,
                tags=(tag,),
            )
            self.canvas.create_text(
                x1 + 43, y1 + 32,
                text=getattr(cell, "profession", "Unknown"),
                anchor="nw",
                fill=COLORS["muted"],
                font=("Consolas", 7, "bold"),
                tags=(tag,),
            )
            clue_text = getattr(clue, "text", str(clue))
            self.canvas.create_text(
                (x1 + x2) / 2, y1 + 57,
                text=clue_text,
                anchor="n",
                justify="center",
                fill=COLORS["ink"],
                font=("Segoe UI", 9),
                width=card_width - 16,
                tags=(tag,),
            )
        else:
            self._draw_avatar((x1 + x2) / 2, y1 + 55, cell, tag, scale=0.75)
            self.canvas.create_text(
                (x1 + x2) / 2, y1 + min(98, card_height - 45),
                text=getattr(cell, "name", "Unknown"),
                fill=COLORS["ink"],
                font=("Segoe UI", 12, "bold"),
                tags=(tag,),
            )
            self.canvas.create_text(
                (x1 + x2) / 2, y1 + min(121, card_height - 22),
                text=getattr(cell, "profession", "Unknown"),
                fill=COLORS["muted"],
                font=("Consolas", 8, "bold"),
                tags=(tag,),
            )

    def _draw_avatar(self, cx: float, cy: float, cell: Any, tag: str, scale: float) -> None:
        if self.canvas is None:
            return

        palette = getattr(cell, "avatar_colors", ("#D7965F", "#3A241D", "#E49A3A"))
        skin, hair, shirt = palette
        style = int(getattr(cell, "hair_style", 0)) % 4

        self.canvas.create_oval(
            cx - 24 * scale, cy + 25 * scale,
            cx + 24 * scale, cy + 46 * scale,
            fill=shirt, outline="", tags=(tag,),
        )
        self.canvas.create_oval(
            cx - 18 * scale, cy - 12 * scale,
            cx + 18 * scale, cy + 29 * scale,
            fill=skin, outline="", tags=(tag,),
        )

        if style == 0:
            self.canvas.create_arc(
                cx - 20 * scale, cy - 20 * scale,
                cx + 20 * scale, cy + 17 * scale,
                start=0, extent=180, fill=hair, outline=hair, tags=(tag,),
            )
        elif style == 1:
            self.canvas.create_oval(
                cx - 21 * scale, cy - 23 * scale,
                cx + 21 * scale, cy + 6 * scale,
                fill=hair, outline="", tags=(tag,),
            )
            self.canvas.create_oval(
                cx - 8 * scale, cy - 35 * scale,
                cx + 10 * scale, cy - 16 * scale,
                fill=hair, outline="", tags=(tag,),
            )
        elif style == 2:
            for dx in (-17, -8, 1, 10):
                self.canvas.create_polygon(
                    cx + dx * scale, cy - 4 * scale,
                    cx + (dx + 6) * scale, cy - 27 * scale,
                    cx + (dx + 12) * scale, cy - 3 * scale,
                    fill=hair, outline="", tags=(tag,),
                )
        else:
            self.canvas.create_arc(
                cx - 23 * scale, cy - 23 * scale,
                cx + 22 * scale, cy + 20 * scale,
                start=0, extent=185, fill=hair, outline=hair, tags=(tag,),
            )

        self.canvas.create_oval(
            cx - 8 * scale, cy + 5 * scale,
            cx - 5 * scale, cy + 8 * scale,
            fill=COLORS["ink"], outline="", tags=(tag,),
        )
        self.canvas.create_oval(
            cx + 5 * scale, cy + 5 * scale,
            cx + 8 * scale, cy + 8 * scale,
            fill=COLORS["ink"], outline="", tags=(tag,),
        )
        self.canvas.create_arc(
            cx - 6 * scale, cy + 8 * scale,
            cx + 6 * scale, cy + 19 * scale,
            start=200, extent=140, style="arc",
            outline=COLORS["ink"], width=1, tags=(tag,),
        )

    def _rounded_rectangle(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        radius: float,
        **kwargs: Any,
    ) -> Any:
        if self.canvas is None:
            return None
        points = [
            x1 + radius, y1,
            x2 - radius, y1,
            x2, y1,
            x2, y1 + radius,
            x2, y2 - radius,
            x2, y2,
            x2 - radius, y2,
            x1 + radius, y2,
            x1, y2,
            x1, y2 - radius,
            x1, y1 + radius,
            x1, y1,
        ]
        return self.canvas.create_polygon(
            points,
            smooth=True,
            splinesteps=24,
            **kwargs,
        )

    def _draw_empty_state(self) -> None:
        if self.canvas is None:
            return
        width = max(self.canvas.winfo_width(), self.width)
        height = max(self.canvas.winfo_height(), self.height)
        self.canvas.create_text(
            width / 2,
            height / 2 - 12,
            text="GRIDUCTIVE",
            fill=COLORS["ink"],
            font=("Segoe UI", 22, "bold"),
        )
        self.canvas.create_text(
            width / 2,
            height / 2 + 20,
            text="Chưa có dữ liệu bàn cờ",
            fill=COLORS["muted"],
            font=("Segoe UI", 10),
        )


class StatusBar:
    """Widget label đơn giản để hiển thị lượt hoặc thông báo kết quả game."""

    def __init__(self, parent: Any) -> None:
        self.parent = parent
        self.label: Optional[Any] = None
        if tk is not None:
            self.label = tk.Label(
                self.parent,
                text="Ready",
                anchor="w",
                bg=COLORS["page"],
                fg=COLORS["muted"],
                font=("Segoe UI", 9),
            )
            self.label.pack(fill="x", padx=10, pady=(0, 10))

    def set_text(self, message: str) -> None:
        """Cập nhật văn bản hiển thị cho người dùng."""
        if self.label is not None:
            self.label.config(text=message)

    def clear(self) -> None:
        """Đặt lại nhãn trạng thái về văn bản mặc định."""
        self.set_text("Ready")
