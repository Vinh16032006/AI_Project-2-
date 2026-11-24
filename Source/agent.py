"""Lớp trừu tượng cho các agent AI trong trò chơi.

Mô-đun này định nghĩa các giao thức chung cho tất cả các chiến lược người chơi.
Mục tiêu là giữ cho phần còn lại của dự án không phụ thuộc vào cách triển khai
cụ thể của một chiến lược, giúp AI, UI và engine trò chơi có thể phát triển độc lập.
"""
from __future__ import annotations
import random
from abc import ABC, abstractmethod
from typing import Any, Optional, List, Dict
from .dpll import SATOracle, SATTimeout
from .encoder import CRIMINAL, INNOCENT, KnowledgeBase


class BaseAgent(ABC):
    """Lớp cơ sở trừu tượng cho tất cả agent trong dự án.

    Các lớp con được kỳ vọng phải triển khai phương thức `choose_move(state)` để trả
    về một nước đi hoặc hành động được engine trò chơi chấp nhận. Các helper bổ
    sung như `legal_moves` và `evaluate_state` có thể được ghi đè để hỗ trợ nhiều kiểu
    chiến lược khác nhau như nhập tay, chính sách ngẫu nhiên, minimax hoặc chơi theo SAT.
    """

    def __init__(self, name: str = "Agent", **kwargs: Any) -> None:
        self.name = name
        self.kwargs = kwargs

    @property
    def agent_type(self) -> str:
        """Nhãn mô tả dễ đọc cho loại agent."""
        return self.__class__.__name__

    @abstractmethod
    def choose_move(self, state: Any) -> Any:
        """Trả về nước đi tiếp theo được lựa chọn cho trạng thái trò chơi hiện tại.

        Tham số:
            state: Đối tượng trạng thái trò chơi do engine quản lý.

        Trả về:
            Một đối tượng nước đi/hành động mà engine có thể kiểm tra và áp dụng.
        """
        raise NotImplementedError("Các lớp con phải triển khai choose_move().")

    def legal_moves(self, state: Any) -> list[Any]:
        """Trả về danh sách nước đi hợp lệ cho trạng thái được cung cấp.

        Phương thức mặc định chủ ý trả về danh sách rỗng; các lớp con có thể ghi đè nếu
        cần suy luận rõ ràng về các lựa chọn khả dụng.
        """
        return []

    def evaluate_state(self, state: Any) -> float:
        """Trả về giá trị heuristic cho trạng thái được cung cấp.

        Phương thức này chủ yếu hữu ích cho các agent tìm kiếm, nhưng được giữ dưới dạng
        giao diện chung để đảm bảo đồng nhất trên các chiến lược khác nhau.
        """
        return 0.0


class HumanAgent(BaseAgent):
    """Agent được điều khiển bởi đầu vào trực tiếp của người dùng.

    Chiến lược này thường tương tác với UI hoặc console để người chơi chọn nước đi
    thủ công. Nó được thiết kế đơn giản và không tự động ra quyết định.
    """

    def __init__(self, name: str = "Human", input_handler: Optional[Any] = None, **kwargs: Any) -> None:
        super().__init__(name=name, **kwargs)
        self.input_handler = input_handler

    def legal_moves(self, state: Any) -> list[Any]:
        """Trả về danh sách nước đi hợp lệ hiện có trong trạng thái."""
        if state is None:
            return []

        for getter_name in ("get_valid_moves", "valid_moves", "legal_moves"):
            getter = getattr(state, getter_name, None)
            if callable(getter):
                result = getter()
                if isinstance(result, (list, tuple, set)):
                    return list(result)
                if result is not None:
                    return list(result)

        if isinstance(state, dict):
            for key in ("legal_moves", "valid_moves", "moves", "actions"):
                value = state.get(key)
                if value is not None:
                    return list(value)

        return []

    def choose_move(self, state: Any) -> Any:
        """Yêu cầu người dùng chọn một nước đi và trả về hành động tương ứng.

        Tham số:
            state: Trạng thái hiện tại của game, bao gồm các nước đi hợp lệ.

        Trả về:
            Một nước đi hợp lệ được người chơi lựa chọn.
        """
        moves = self.legal_moves(state)
        if not moves:
            raise ValueError("Không có nước đi hợp lệ nào cho human agent.")

        if self.input_handler is not None:
            raw_choice = self.input_handler(moves)
            if isinstance(raw_choice, int):
                if 0 <= raw_choice < len(moves):
                    return moves[raw_choice]
                raise ValueError("Vị trí nước đi người dùng chọn không hợp lệ.")
            if raw_choice in moves:
                return raw_choice
            if str(raw_choice).isdigit():
                index = int(str(raw_choice))
                if 0 <= index < len(moves):
                    return moves[index]
            raise ValueError(f"Nước đi được chọn không hợp lệ: {raw_choice!r}")

        while True:
            prompt = "Chọn một nước đi: " + ", ".join(str(move) for move in moves) + "\n> "
            response = input(prompt).strip()
            if response.isdigit():
                index = int(response)
                if 0 <= index < len(moves):
                    return moves[index]
            for move in moves:
                if str(move) == response:
                    return move
            print("Đầu vào không hợp lệ. Hãy chọn một nước đi có sẵn.")


class RandomAgent(BaseAgent):
    """Agent chọn một nước đi hợp lệ ngẫu nhiên từ trạng thái hiện tại."""

    def __init__(self, name: str = "Random", **kwargs: Any) -> None:
        super().__init__(name=name, **kwargs)

    def legal_moves(self, state: Any) -> list[Any]:
        """Trả về các nước đi hợp lệ từ trạng thái trò chơi hiện tại, nếu có."""
        if state is None:
            return []

        for getter_name in ("get_valid_moves", "valid_moves", "legal_moves"):
            getter = getattr(state, getter_name, None)
            if callable(getter):
                result = getter()
                if isinstance(result, (list, tuple, set)):
                    return list(result)
                if result is not None:
                    return list(result)

        if isinstance(state, dict):
            for key in ("legal_moves", "valid_moves", "moves", "actions"):
                value = state.get(key)
                if value is not None:
                    return list(value)

        return []

    def choose_move(self, state: Any) -> Any:
        """Chọn một nước đi hợp lệ ngẫu nhiên và trả về nó.

        Chính sách này rất hữu ích làm baseline để so sánh với các chiến lược thông minh hơn.
        """
        moves = self.legal_moves(state)
        if not moves:
            raise ValueError("Không có nước đi hợp lệ nào cho random agent.")
        return random.choice(moves)

class DeductiveAgent(BaseAgent):
    """Chỉ đọc state công khai, chỉ nộp verdict bị ép buộc."""

    def __init__(self, engine: Any, oracle: Optional[SATOracle] = None, name: str = "Deductive", **kwargs: Any) -> None:
        super().__init__(name=name, **kwargs)
        self.engine = engine
        self.oracle = oracle or engine.oracle
        self.trace: List[Dict[str, Any]] = []
        self.waves = 0
        self.terminal: Optional[str] = None
        self.max_stats = {"primary_variables": 0, "auxiliary_variables": 0, "clauses": 0}

    def analyse(self, state: Any) -> Dict[str, Any]:
        kb = KnowledgeBase(state, self.oracle)
        for key, value in kb.stats().items():
            self.max_stats[key] = max(self.max_stats.get(key, 0), value)
        forced, unknown = [], []
        for cid, cell in state.board.items():
            if cell.get("is_revealed"):
                continue
            status, queries = kb.classify(cid)
            if status in (CRIMINAL, INNOCENT):
                forced.append({"character": cid, "status": status, "queries": queries})
            else:
                unknown.append(cid)
        return {"consistent": kb.consistent, "forced": forced, "unknown": unknown}

    def choose_move(self, state: Any) -> Any:
        forced = self.analyse(state)["forced"]
        if not forced:
            raise ValueError("Không có verdict nào bị ép buộc.")
        return {"character": forced[0]["character"], "status": forced[0]["status"]}

    def hint(self) -> Optional[Dict[str, Any]]:
        state = self.engine.state
        forced = self.analyse(state)["forced"]
        if not forced:
            return None
        item = forced[0]
        return {"character": item["character"], "status": item["status"],
                "active_clue_ids": [c.get("id") for c in state.revealed_clues]}

    def run(self) -> str:
        try:
            while not self.engine.is_game_over():
                analysis = self.analyse(self.engine.state)
                if not analysis["consistent"]:
                    self.terminal = "INCONSISTENT"
                    return self.terminal
                if not analysis["forced"]:
                    self.terminal = "STUCK"
                    return self.terminal
                self.waves += 1                      # một đợt = tất cả verdict ép buộc hiện tại
                for item in analysis["forced"]:
                    active = [c.get("id") for c in self.engine.state.revealed_clues]
                    result = self.engine.submit_verdict(item["character"], item["status"])
                    if result["result"] != "ACCEPTED":
                        self.terminal = "REJECTED"
                        return self.terminal
                    clue = result.get("revealed_clue") or {}
                    self.trace.append({
                        "step": len(self.trace) + 1, "wave": self.waves,
                        "active_clue_ids": active, "sat_queries": item["queries"],
                        "character": item["character"], "verdict": item["status"],
                        "revealed_clue": clue.get("id"), "revealed_clue_text": clue.get("text"),
                    })
            self.terminal = "SOLVED"
        except SATTimeout:
            self.terminal = "TIMEOUT"
        return self.terminal

def create_agent(agent_type: str, name: Optional[str] = None) -> BaseAgent:
    """Factory để khởi tạo một đối tượng agent cụ thể.

    Tham số:
        agent_type: Chuỗi định danh như 'human', 'random' hoặc tên AI trong tương lai.
        name: Tên hiển thị tùy chọn cho đối tượng được tạo.

    Trả về:
        Một lớp con của `BaseAgent` phù hợp với chiến lược được yêu cầu.
    """
    normalized = (agent_type or "").strip().lower()

    if normalized in {"human", "player"}:
        return HumanAgent(name=name or "Human")
    if normalized in {"random", "rand"}:
        return RandomAgent(name=name or "Random")

    raise ValueError(f"Loại agent không được hỗ trợ: {agent_type!r}")
