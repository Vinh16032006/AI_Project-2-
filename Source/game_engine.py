"""Trạng thái game và khung engine cho dự án.

Engine đóng vai trò là nguồn chân lý duy nhất cho luật chơi, lượt đi và điều kiện
chiến thắng. Các agent sẽ truy vấn engine để lấy nước đi hợp lệ, còn UI sẽ render
trạng thái hiện tại của `GameState` mà không sửa trực tiếp luật chơi.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional


@dataclass
class GameState:
    """Biểu diễn toàn bộ trạng thái của trò chơi.

    Thuộc tính:
        board: Biểu diễn bàn cờ theo miền trò chơi. Có thể là 2D list, dict hoặc
            đối tượng tùy chỉnh tùy theo luật game.
        turn: Số lượt hoặc lượt người chơi hiện tại.
        winner: Tên người thắng hoặc None khi game vẫn đang diễn ra.
        moves: Lịch sử các nước đi đã được áp dụng.
    """

    board: Any = None
    turn: int = 0
    winner: Optional[str] = None
    moves: List[Any] = field(default_factory=list)


class GameEngine:
    """Engine chính điều khiển vòng đời của game.

    Trách nhiệm bao gồm:
    - tạo và đặt lại bàn cờ;
    - kiểm tra tính hợp lệ và áp dụng nước đi;
    - xác định điều kiện kết thúc trò chơi;
    - cung cấp mô hình trạng thái thống nhất cho UI và agent.
    """

    def __init__(self, initial_state: Optional[GameState] = None) -> None:
        self.state = initial_state or GameState()
        self.history: List[GameState] = []
        self._ensure_initial_board()

    def _ensure_initial_board(self) -> None:
        """Đảm bảo trạng thái có bàn cờ hợp lệ trước khi trò chơi bắt đầu."""
        if self.state.board is None:
            self.state.board = self.initialize_board()

    def initialize_board(self) -> Any:
        """Tạo cấu hình bàn cờ ban đầu.

        Phương thức này nên được triển khai theo đúng luật game của dự án (ví dụ: ma trận,
        sơ đồ quân cờ hoặc dictionary biểu diễn board).
        """
        # TODO: khởi tạo bàn cờ đầu tiên và các metadata liên quan
        return None

    def reset(self) -> None:
        """Đặt lại trò chơi về trạng thái đầu và xóa lịch sử nước đi."""
        self.state = GameState(board=self.initialize_board())
        self.history = []

    def validate_move(self, move: Any) -> bool:
        """Kiểm tra xem một nước đi có hợp lệ trong trạng thái hiện tại hay không."""
        # TODO: kiểm tra luật, giới hạn vị trí, ô đang chiếm, lượt đi, v.v.
        return False

    def get_valid_moves(self) -> List[Any]:
        """Trả về tất cả các nước đi hợp lệ có sẵn từ trạng thái hiện tại."""
        # TODO: tính toán các hành động khả dụng dựa trên bàn cờ và luật hiện hành
        return []

    def apply_move(self, move: Any) -> bool:
        """Áp dụng một nước đi và cập nhật trạng thái.

        Tham số:
            move: Đối tượng nước đi do người chơi hoặc AI gửi lên.

        Trả về:
            True khi nước đi được chấp nhận và áp dụng thành công.
        """
        if not self.validate_move(move):
            return False

        # TODO: thay đổi board, thêm vào lịch sử, cập nhật lượt, và đánh giá người thắng.
        self.state.moves.append(move)
        self.state.turn += 1
        self.state.winner = self.check_winner()
        return True

    def check_winner(self) -> Optional[str]:
        """Xác định xem ai đó đã thắng hoặc game đã hòa."""
        # TODO: kiểm tra bàn cờ hoặc các điều kiện kết thúc để xác định người thắng.
        return None

    def is_game_over(self) -> bool:
        """Trả về True nếu trò chơi đã ở trạng thái kết thúc."""
        return self.state.winner is not None or self.check_winner() is not None

    def evaluate_state(self) -> float:
        """Cung cấp giá trị đánh giá số cho tìm kiếm heuristic hoặc tính điểm.

        Giá trị dương có thể biểu thị lợi thế cho người chơi hiện tại, trong khi giá trị âm
        biểu thị bất lợi. Đây là interface tổng quát để cho phép heuristic theo từng game.
        """
        # TODO: triển khai chiến lược đánh giá heuristic hoặc reward policy.
        return 0.0

    def to_dict(self) -> dict[str, Any]:
        """Serialize trạng thái game để lưu UI hoặc debug."""
        return {
            "board": self.state.board,
            "turn": self.state.turn,
            "winner": self.state.winner,
            "moves": self.state.moves,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "GameEngine":
        """Tái tạo một phiên bản GameEngine từ dictionary đã serialize."""
        state = GameState(
            board=payload.get("board"),
            turn=payload.get("turn", 0),
            winner=payload.get("winner"),
            moves=payload.get("moves", []),
        )
        return cls(initial_state=state)
