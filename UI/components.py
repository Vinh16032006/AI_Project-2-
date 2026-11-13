"""Các widget giao diện tái sử dụng cho ứng dụng desktop."""
from __future__ import annotations

from typing import Any, Optional

try:
    import tkinter as tk
except ImportError:  # pragma: no cover
    tk = None


class BoardPanel:
    """Canvas chịu trách nhiệm vẽ bàn cờ hiện tại và tương tác người dùng."""

    def __init__(self, parent: Any, width: int = 600, height: int = 600) -> None:
        self.parent = parent
        self.width = width
        self.height = height
        self.canvas: Optional[Any] = None

        if tk is not None:
            self.canvas = tk.Canvas(self.parent, width=self.width, height=self.height, bg="white")
            self.canvas.pack(fill="both", expand=True)

    def draw_board(self, board: Any) -> None:
        """Vẽ từng ô hoặc tile trên bàn cờ."""
        # TODO: vẽ nền lưới, quân cờ, highlight và metadata
        if self.canvas is None:
            return
        self.canvas.delete("all")

    def render(self, state: Any) -> None:
        """Render trạng thái game hiện tại lên canvas."""
        # TODO: ánh xạ state -> board objects -> draw_board(...)
        self.draw_board(getattr(state, "board", None))

    def bind_click(self, callback: Any) -> None:
        """Đăng ký callback cho sự kiện click vào board."""
        # TODO: gắn handler cho từng ô hoặc toàn bộ canvas
        if self.canvas is not None and callback is not None:
            self.canvas.bind("<Button-1>", callback)


class StatusBar:
    """Widget label đơn giản để hiển thị lượt hoặc thông báo kết quả game."""

    def __init__(self, parent: Any) -> None:
        self.parent = parent
        self.label: Optional[Any] = None

        if tk is not None:
            self.label = tk.Label(self.parent, text="Ready", anchor="w")
            self.label.pack(fill="x", padx=10, pady=(0, 10))

    def set_text(self, message: str) -> None:
        """Cập nhật văn bản hiển thị cho người dùng."""
        if self.label is not None:
            self.label.config(text=message)

    def clear(self) -> None:
        """Đặt lại nhãn trạng thái về văn bản mặc định."""
        self.set_text("Ready")
