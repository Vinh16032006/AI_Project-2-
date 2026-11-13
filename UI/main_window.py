"""Cửa sổ chính của ứng dụng game AI."""
from __future__ import annotations

from typing import Any, Optional

try:
    import tkinter as tk
except ImportError:  # pragma: no cover
    tk = None

from Source.game_engine import GameEngine
from UI.components import BoardPanel, StatusBar


class MainWindow:
    """Cửa sổ ứng dụng cấp cao nhất.

    Trách nhiệm bao gồm:
    - tạo shell giao diện chính;
    - kết nối hành động với engine trò chơi;
    - cập nhật hiển thị board và trạng thái game.
    """

    def __init__(self, root: Optional[Any] = None, game_engine: Optional[GameEngine] = None) -> None:
        if tk is None:
            raise RuntimeError("tkinter là bắt buộc để chạy UI.")

        self.root = root or tk.Tk()
        self.root.title("AI Project 2")
        self.game_engine = game_engine or GameEngine()
        self.board_panel: Optional[BoardPanel] = None
        self.status_bar: Optional[StatusBar] = None

        self.build_ui()
        self.bind_events()

    def build_ui(self) -> None:
        """Xây dựng bố cục giao diện ứng dụng."""
        # TODO: tạo main frame, toolbar, khu vực board và phần trạng thái
        self.board_panel = BoardPanel(self.root)
        self.status_bar = StatusBar(self.root)
        self.update_status("Game ready")

    def bind_events(self) -> None:
        """Kết nối các trình xử lý tương tác người dùng."""
        # TODO: gắn nút, phím tắt bàn phím và sự kiện click vào board
        pass

    def update_status(self, message: str) -> None:
        """Hiển thị thông tin trong thanh trạng thái."""
        if self.status_bar is not None:
            self.status_bar.set_text(message)

    def start_new_game(self) -> None:
        """Đặt lại game và render trạng thái ban đầu của bàn cờ."""
        self.game_engine.reset()
        if self.board_panel is not None:
            self.board_panel.render(self.game_engine.state)

    def handle_board_click(self, event: Any) -> None:
        """Xử lý tương tác người dùng trên board."""
        # TODO: chuyển tọa độ click thành một nước đi và gửi tới engine
        pass

    def run(self) -> None:
        """Khởi động vòng lặp sự kiện Tkinter."""
        self.root.mainloop()
