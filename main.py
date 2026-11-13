"""Điểm vào ứng dụng cho AI-Project 2."""
from __future__ import annotations

from Source.game_engine import GameEngine
from UI.main_window import MainWindow


def main() -> None:
    """Khởi tạo engine trò chơi và bắt đầu giao diện desktop."""
    game_engine = GameEngine()
    window = MainWindow(game_engine=game_engine)
    window.start_new_game()
    window.run()


if __name__ == "__main__":
    main()
