"""Encoder để chuyển logic game sang ràng buộc Boolean/SAT.

Thiết kế tách logic trò chơi khỏi bộ giải SAT: encoder chịu trách nhiệm gán mỗi
sự kiện/game fact thành một biến Boolean duy nhất, tạo các clause CNF cho trạng thái
hợp lệ và giải mã một assignment thỏa mãn trở lại thành mô tả board hoặc hành động dễ đọc.
"""
from __future__ import annotations

from typing import Any, Dict, List


class GameEncoder:
    """Ánh xạ đối tượng trò chơi sang biến Boolean và clause SAT."""

    def __init__(self, game_state: Any | None = None) -> None:
        self.game_state = game_state
        self.variable_map: Dict[str, int] = {}
        self.reverse_variable_map: Dict[int, str] = {}

    def reset(self, game_state: Any | None = None) -> None:
        """Đặt lại bản đồ biến bên trong của encoder."""
        self.game_state = game_state
        self.variable_map = {}
        self.reverse_variable_map = {}

    def register_variable(self, name: str, value: Any) -> int:
        """Gán một mã biến SAT nhất quán cho một sự kiện trong game."""
        if name not in self.variable_map:
            next_id = len(self.variable_map) + 1
            self.variable_map[name] = next_id
            self.reverse_variable_map[next_id] = name
        return self.variable_map[name]

    def build_variable_map(self, game_state: Any) -> None:
        """Duyệt trạng thái game và tạo ID cho tất cả các sự kiện quan trọng."""
        # TODO: liệt kê ô bàn cờ, vị trí người chơi, số lượt, trạng thái thắng/thua, ...
        self.game_state = game_state

    def encode_game_state(self, game_state: Any) -> List[List[int]]:
        """Chuyển trạng thái game thành công thức CNF.

        Các quy tắc điển hình bao gồm:
        - mỗi ô trên bàn cờ có tối đa một quân/đối tượng;
        - mỗi nước đi chỉ hợp lệ khi đúng lượt/người chơi;
        - trạng thái kết thúc phải tuân theo luật thắng/thua/hòa;
        - ràng buộc đối xứng hoặc loại trừ trong miền trò chơi.
        """
        # TODO: xây dựng biểu diễn CNF cho trạng thái board hiện tại
        return []

    def encode_move(self, move: Any, game_state: Any) -> List[List[int]]:
        """Mã hóa từng nước đi thành tập các clause SAT.

        Điều này hữu ích để kiểm tra nước đi có hợp lệ hay không hoặc để biểu diễn
        chuyển trạng thái trong một SAT-based planner.
        """
        # TODO: chuyển ngữ nghĩa của nước đi thành các clause CNF và ràng buộc hợp lệ
        return []

    def decode_model(self, model: Dict[int, bool]) -> Dict[str, bool]:
        """Dịch assignment SAT về các nhãn mang ý nghĩa của miền trò chơi."""
        decoded: Dict[str, bool] = {}
        for variable_id, value in model.items():
            key = self.reverse_variable_map.get(variable_id)
            if key is not None:
                decoded[key] = value
        return decoded


def encode_game_state(game_state: Any) -> List[List[int]]:
    """Hàm tiện ích cấp mô-đun để xây dựng ràng buộc CNF cho trạng thái game."""
    encoder = GameEncoder(game_state)
    return encoder.encode_game_state(game_state)


def encode_move(move: Any, game_state: Any) -> List[List[int]]:
    """Hàm tiện ích cấp mô-đun để mã hóa một nước đi thành clause CNF."""
    encoder = GameEncoder(game_state)
    return encoder.encode_move(move, game_state)


def decode_model(model: Dict[int, bool]) -> Dict[str, bool]:
    """Giải mã assignment thỏa mãn thành cấu trúc có ý nghĩa trong game."""
    # TODO: cho phép dùng encoder mặc định hoặc import context trạng thái nếu cần.
    return GameEncoder().decode_model(model)
