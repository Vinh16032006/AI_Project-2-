"""Trạng thái game và khung engine cho dự án Griductive (AI - Project 2).

Engine đóng vai trò là nguồn chân lý duy nhất cho luật chơi, quản lý đáp án ẩn,
manh mối chưa lật, kiểm tra suy diễn logic không đoán mò (no-guess deduction)
và cung cấp mô hình trạng thái thống nhất cho UI, Encoder và Agent.
"""
from __future__ import annotations

import copy
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from .dpll import SATOracle, dpll, check_uniqueness
from .encoder import GameEncoder, KnowledgeBase

# =============================================================================
# HẰNG SỐ TRẠNG THÁI VÀ KẾT QUẢ PHÁN QUYẾT
# =============================================================================
STATUS_CRIMINAL = "CRIMINAL"
STATUS_INNOCENT = "INNOCENT"
STATUS_UNKNOWN = "UNKNOWN"

VERDICT_ACCEPTED = "ACCEPTED"
VERDICT_NOT_PROVABLE = "NOT_PROVABLE"
VERDICT_CONTRADICTED = "CONTRADICTED"
VERDICT_ALREADY_REVEALED = "ALREADY_REVEALED"
VERDICT_INVALID = "INVALID_MOVE"
VERDICT_INCONSISTENT = "INCONSISTENT"


@dataclass
class GameState:
    """Biểu diễn trạng thái công khai của trò chơi cho UI, Encoder và Agent.

    Thuộc tính:
        board: Dictionary ánh xạ mã ô ('A1', 'B1', ...) sang thông tin hiển thị công khai.
            (Đáp án thật và manh mối của các thẻ chưa lật đã bị ẩn đi).
        turn: Số bước suy diễn (số thẻ đã được người chơi/agent lật thêm).
        winner: 'Player' khi toàn bộ bảng đã được giải xong, ngược lại là None.
        moves: Lịch sử các nước đi hợp lệ đã được áp dụng.
        revealed_clues: Danh sách các manh mối đã lật (định dạng chuẩn cho GameEncoder).
        verdicts: Danh sách các phán quyết đã chứng minh (định dạng chuẩn cho GameEncoder).
        size: Kích thước lưới NxN (mặc định N = 3, 4 hoặc 5).
        last_action_result: Kết quả chi tiết của lần nộp phán quyết gần nhất (hỗ trợ UI/StatusBar).
    """

    board: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    turn: int = 0
    winner: Optional[str] = None
    moves: List[Dict[str, Any]] = field(default_factory=list)
    revealed_clues: List[Dict[str, Any]] = field(default_factory=list)
    verdicts: List[Dict[str, Any]] = field(default_factory=list)
    size: int = 3
    last_action_result: Optional[Dict[str, Any]] = None


class GameEngine:
    """Engine chính điều khiển vòng đời của game Griductive.

    Trách nhiệm:
    - Quản lý bàn cờ NxN, giữ bí mật đáp án ẩn và manh mối chưa lật;
    - Chuyển đổi các vùng (ROW, COL, NEIGHBORS, EXPLICIT, CORNERS, BOUNDARY, BETWEEN, COMMON_NEIGHBORS)
      thành danh sách nhân vật cụ thể cho `encoder.py`;
    - Xác thực nước đi theo nguyên tắc không suy đoán (no-guess) bằng DPLL SAT solver;
    - Cung cấp các hàm hỗ trợ GUI: Load, Restart, Highlight vùng của clue, Hint.
    """

    def __init__(
        self,
        initial_state: Optional[GameState] = None,
        puzzle_data: Optional[Dict[str, Any]] = None,
        enforce_logic: bool = True,
    ) -> None:
        self.enforce_logic: bool = enforce_logic
        self.oracle: SATOracle = SATOracle()
        self._raw_puzzle_data: Dict[str, Any] = copy.deepcopy(
            puzzle_data if puzzle_data is not None else self._get_default_puzzle()
        )
        # Lưu trữ dữ liệu ẩn của từng ô (true_status và raw_clue) tách biệt hoàn toàn với self.state
        self._secret_cells: Dict[str, Dict[str, Any]] = {}
        self._name_to_id: Dict[str, str] = {}

        self.state: GameState = initial_state or GameState()
        self.history: List[GameState] = []
        self._ensure_initial_board()

    # =========================================================================
    # 1. KHỞI TẠO, LOAD PUZZLE & RESET
    # =========================================================================

    def _ensure_initial_board(self) -> None:
        """Đảm bảo trạng thái có bàn cờ hợp lệ trước khi trò chơi bắt đầu."""
        if not self.state.board:
            self.state.board = self.initialize_board()
        else:
            # Nếu khởi tạo từ initial_state có sẵn (vd: qua from_dict), đồng bộ lại kho dữ liệu ẩn
            self._sync_secret_from_existing_board(self.state.board)

    def initialize_board(self) -> Dict[str, Dict[str, Any]]:
        """Tạo cấu hình bàn cờ ban đầu từ dữ liệu câu đố và thiết lập trạng thái công khai."""
        puzzle = self._raw_puzzle_data
        size = int(puzzle.get("size", 3))
        self.state.size = size
        self.state.turn = 0
        self.state.winner = None
        self.state.moves.clear()
        self.state.revealed_clues.clear()
        self.state.verdicts.clear()
        self.state.last_action_result = None

        self._secret_cells.clear()
        self._name_to_id.clear()

        # Bước 1: Đọc toàn bộ các ô vào bộ nhớ ẩn (_secret_cells) để phục vụ việc giải quyết vùng (regions)
        raw_cells = puzzle.get("cells", [])
        for cell in raw_cells:
            cid = str(cell.get("id") or cell.get("cell_id")).strip().upper()
            col_char = cid[0]
            row_num = int(cid[1:])
            name = str(cell.get("name", cid)).strip()
            profession = str(cell.get("profession", "")).strip()
            true_status = self._normalize_status(cell.get("status") or cell.get("true_status"))
            is_revealed = bool(cell.get("is_revealed") or cell.get("revealed", False))
            raw_clue = copy.deepcopy(cell.get("clue"))

            self._secret_cells[cid] = {
                "id": cid,
                "row": row_num,
                "col": col_char,
                "name": name,
                "profession": profession,
                "true_status": true_status,
                "raw_clue": raw_clue,
                "is_revealed": is_revealed,
            }
            self._name_to_id[name.lower()] = cid
            self._name_to_id[cid.lower()] = cid

        # Bước 2: Chuẩn hóa toàn bộ manh mối sang định dạng tương thích với encoder.py
        for cid, secret in self._secret_cells.items():
            if secret["raw_clue"] is not None:
                secret["compiled_clue"] = self._compile_clue(secret["raw_clue"], owner_id=cid)
            else:
                secret["compiled_clue"] = None

        # Bước 3: Xây dựng bảng công khai (public board) và nạp các ô đã lật sẵn vào KB_0
        public_board: Dict[str, Dict[str, Any]] = {}
        for cid in self.get_row_major_ids():
            secret = self._secret_cells[cid]
            revealed = secret["is_revealed"]
            public_board[cid] = self._build_public_cell_view(cid)

            if revealed:
                self.state.verdicts.append({
                    "character": cid,
                    "status": secret["true_status"],
                })
                if secret["compiled_clue"] is not None:
                    self.state.revealed_clues.append(copy.deepcopy(secret["compiled_clue"]))

        self.state.winner = self.check_winner(public_board)
        return public_board

    def _sync_secret_from_existing_board(self, board: Dict[str, Any]) -> None:
        """Đồng bộ hóa dữ liệu khi tái tạo GameEngine thông qua from_dict."""
        self._secret_cells.clear()
        self._name_to_id.clear()
        for cid, cell in board.items():
            if not isinstance(cell, dict):
                continue
            cid_upper = str(cell.get("id", cid)).strip().upper()
            name = str(cell.get("name", cid_upper)).strip()
            status = cell.get("true_status") or cell.get("status")
            norm_status = self._normalize_status(status) if status not in (None, STATUS_UNKNOWN) else STATUS_INNOCENT
            raw_clue = cell.get("raw_clue") or cell.get("clue")
            self._secret_cells[cid_upper] = {
                "id": cid_upper,
                "row": int(cid_upper[1:]) if len(cid_upper) > 1 and cid_upper[1:].isdigit() else 1,
                "col": cid_upper[0],
                "name": name,
                "profession": str(cell.get("profession", "")),
                "true_status": norm_status,
                "raw_clue": copy.deepcopy(raw_clue),
                "compiled_clue": copy.deepcopy(raw_clue),
                "is_revealed": bool(cell.get("is_revealed", False)),
            }
            self._name_to_id[name.lower()] = cid_upper
            self._name_to_id[cid_upper.lower()] = cid_upper

    def _build_public_cell_view(self, cid: str) -> Dict[str, Any]:
        """Tạo view công khai cho 1 ô (che giấu đáp án và manh mối nếu thẻ chưa lật)."""
        secret = self._secret_cells[cid]
        if secret["is_revealed"]:
            return {
                "id": secret["id"],
                "row": secret["row"],
                "col": secret["col"],
                "name": secret["name"],
                "profession": secret["profession"],
                "is_revealed": True,
                "status": secret["true_status"],
                "clue": copy.deepcopy(secret["compiled_clue"]),
            }
        return {
            "id": secret["id"],
            "row": secret["row"],
            "col": secret["col"],
            "name": secret["name"],
            "profession": secret["profession"],
            "is_revealed": False,
            "status": STATUS_UNKNOWN,
            "clue": None,
        }

    def load_puzzle(self, puzzle_data: Dict[str, Any]) -> None:
        """Nạp một câu đố mới từ dictionary và khởi tạo lại toàn bộ trạng thái game."""
        self._raw_puzzle_data = copy.deepcopy(puzzle_data)
        self.reset()

    def load_puzzle_from_file(self, filepath: str) -> None:
        """Đọc câu đố từ file JSON (phục vụ nút Load trên GUI)."""
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.load_puzzle(data)

    def reset(self) -> None:
        """Đặt lại trò chơi về trạng thái ban đầu và xóa lịch sử nước đi (nút Restart)."""
        self.history.clear()
        self.state = GameState(size=int(self._raw_puzzle_data.get("size", 3)))
        self.state.board = self.initialize_board()

    # =========================================================================
    # 2. XỬ LÝ TỌA ĐỘ, VÙNG (REGIONS) & CHUẨN HÓA CLUE CHO ENCODER
    # =========================================================================

    def resolve_identifier(self, identifier: Any) -> str:
        """Chuyển đổi tên nhân vật ('Abel') hoặc mã ô ('A1') thành mã ô chuẩn xác ('A1')."""
        if identifier is None:
            raise ValueError("Định danh nhân vật/ô không được là None.")
        key = str(identifier).strip().lower()
        if key in self._name_to_id:
            return self._name_to_id[key]
        raise KeyError(f"Không tìm thấy nhân vật hoặc ô '{identifier}' trên bàn cờ.")

    def get_row_major_ids(self) -> List[str]:
        """Trả về danh sách các mã ô theo thứ tự row-major (A1, B1, C1, A2, B2, ...)."""
        size = self.state.size
        cols = [chr(ord("A") + c) for c in range(size)]
        rows = range(1, size + 1)
        result = [f"{c}{r}" for r in rows for c in cols if f"{c}{r}" in self._secret_cells]
        if result:
            return result
        return list(self._secret_cells.keys())

    def get_neighbors(self, cell_or_name: str) -> List[str]:
        """Trả về danh sách các ô lân cận (ngang, dọc, chéo - tối đa 8 ô, trừ chính nó)."""
        cid = self.resolve_identifier(cell_or_name)
        col_idx = ord(cid[0]) - ord("A")
        row_idx = int(cid[1:])
        size = self.state.size

        neighbors: List[str] = []
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                nr, nc = row_idx + dr, col_idx + dc
                if 1 <= nr <= size and 0 <= nc < size:
                    nid = f"{chr(ord('A') + nc)}{nr}"
                    if nid in self._secret_cells:
                        neighbors.append(nid)
        return neighbors

    def resolve_region(self, region_spec: Any) -> List[str]:
        """Biên dịch một biểu thức vùng (Region) thành danh sách các mã ô cụ thể."""
        if isinstance(region_spec, (list, tuple)):
            resolved: List[str] = []
            for item in region_spec:
                cid = self.resolve_identifier(item)
                if cid not in resolved:
                    resolved.append(cid)
            return resolved

        if not isinstance(region_spec, dict):
            raise ValueError(f"Định dạng region không hợp lệ: {region_spec!r}")

        rtype = str(region_spec.get("type") or region_spec.get("region_type", "")).strip().upper()
        params = region_spec.get("params", region_spec.get("value", region_spec.get("target")))
        size = self.state.size

        if rtype == "ROW":
            row_num = int(params)
            return [cid for cid in self.get_row_major_ids() if self._secret_cells[cid]["row"] == row_num]

        if rtype in {"COL", "COLUMN"}:
            col_char = str(params).strip().upper()
            return [cid for cid in self.get_row_major_ids() if self._secret_cells[cid]["col"] == col_char]

        if rtype == "NEIGHBORS":
            return self.get_neighbors(str(params))

        if rtype == "EXPLICIT":
            if not isinstance(params, (list, tuple)):
                raise ValueError("EXPLICIT region yêu cầu danh sách các ô.")
            return self.resolve_region(params)

        # --- Các biểu thức vùng mở rộng (Extensions - Mục 3.2) ---
        if rtype == "COMMON_NEIGHBORS":
            t1, t2 = self.resolve_identifier(params[0]), self.resolve_identifier(params[1])
            n1, n2 = set(self.get_neighbors(t1)), set(self.get_neighbors(t2))
            return [cid for cid in self.get_row_major_ids() if cid in (n1 & n2)]

        if rtype == "CORNERS":
            last_col = chr(ord("A") + size - 1)
            corners = ["A1", f"{last_col}1", f"A{size}", f"{last_col}{size}"]
            return [c for c in corners if c in self._secret_cells]

        if rtype == "BOUNDARY":
            last_col = chr(ord("A") + size - 1)
            return [
                cid for cid in self.get_row_major_ids()
                if self._secret_cells[cid]["row"] in (1, size)
                or self._secret_cells[cid]["col"] in ("A", last_col)
            ]

        if rtype == "BETWEEN":
            c1 = self._secret_cells[self.resolve_identifier(params[0])]
            c2 = self._secret_cells[self.resolve_identifier(params[1])]
            if c1["row"] == c2["row"]:
                c_min, c_max = min(ord(c1["col"]), ord(c2["col"])), max(ord(c1["col"]), ord(c2["col"]))
                return [f"{chr(c)}{c1['row']}" for c in range(c_min + 1, c_max)]
            if c1["col"] == c2["col"]:
                r_min, r_max = min(c1["row"], c2["row"]), max(c1["row"], c2["row"])
                return [f"{c1['col']}{r}" for r in range(r_min + 1, r_max)]
            raise ValueError("Hai nhân vật trong vùng BETWEEN phải nằm cùng hàng hoặc cùng cột.")

        raise ValueError(f"Loại vùng không được hỗ trợ: {rtype}")

    def _compile_clue(self, raw_clue: Dict[str, Any], owner_id: str) -> Dict[str, Any]:
        """Chuẩn hóa Clue sang đúng định dạng dictionary mà `Source/encoder.py` yêu cầu."""
        ctype = str(raw_clue.get("type") or raw_clue.get("clue_type", "")).strip().upper()
        text = str(raw_clue.get("text", "")).strip()

        # Hỗ trợ từ khóa NO -> EXACTLY(0, region) theo Mục 3.2 của đề bài
        if ctype == "NO":
            ctype = "EXACTLY"
            count_val = 0
        else:
            count_val = raw_clue.get("count")

        compiled: Dict[str, Any] = {
            "id": raw_clue.get("id") or raw_clue.get("clue_id") or f"CLUE_{owner_id}",
            "owner": owner_id,
            "type": ctype,
            "text": text,
        }

        if ctype == "FACT":
            target = raw_clue.get("character")
            if target is None and raw_clue.get("targets"):
                target = raw_clue["targets"][0]
            cid = self.resolve_identifier(target)
            status = self._normalize_status(raw_clue.get("status") or raw_clue.get("fact_status"))
            compiled["character"] = cid
            compiled["status"] = status
            compiled["highlighted_cells"] = [cid]
            return compiled

        if ctype in {"SAME", "DIFFERENT"}:
            c1 = raw_clue.get("character1")
            c2 = raw_clue.get("character2")
            if (c1 is None or c2 is None) and isinstance(raw_clue.get("targets"), (list, tuple)):
                c1, c2 = raw_clue["targets"][0], raw_clue["targets"][1]
            id1, id2 = self.resolve_identifier(c1), self.resolve_identifier(c2)
            compiled["character1"] = id1
            compiled["character2"] = id2
            compiled["highlighted_cells"] = [id1, id2]
            return compiled

        if ctype in {"EXACTLY", "AT_LEAST", "AT_MOST"}:
            if "characters" in raw_clue and raw_clue["characters"] is not None:
                chars = self.resolve_region(raw_clue["characters"])
            elif "region" in raw_clue and raw_clue["region"] is not None:
                chars = self.resolve_region(raw_clue["region"])
            else:
                raise ValueError(f"Manh mối {ctype} tại {owner_id} thiếu 'characters' hoặc 'region'.")

            if count_val is None:
                raise ValueError(f"Manh mối {ctype} tại {owner_id} thiếu 'count'.")
            k = int(count_val)

            # Nếu manh mối đếm số INNOCENT (vd: "Exactly 2 of the 4 innocents..."),
            # tự động quy đổi sang số CRIMINAL để tương thích với encoder.py
            target_status = str(raw_clue.get("target_status", STATUS_CRIMINAL)).strip().upper()
            if target_status in {"INNOCENT", "NOT GUILTY"}:
                if ctype == "EXACTLY":
                    k = len(chars) - k
                elif ctype == "AT_LEAST":
                    ctype = "AT_MOST"
                    k = len(chars) - k
                elif ctype == "AT_MOST":
                    ctype = "AT_LEAST"
                    k = len(chars) - k

            compiled["type"] = ctype
            compiled["characters"] = chars
            compiled["count"] = k
            compiled["highlighted_cells"] = list(chars)
            if "region" in raw_clue:
                compiled["region"] = copy.deepcopy(raw_clue["region"])
            return compiled

        # Cho phép lưu giữ các loại clue mở rộng khác nếu nhóm bổ sung sau
        compiled.update(copy.deepcopy(raw_clue))
        compiled["type"] = ctype
        return compiled

    @staticmethod
    def _normalize_status(status: Any) -> str:
        """Chuẩn hóa nhãn trạng thái về 'CRIMINAL' hoặc 'INNOCENT'."""
        if isinstance(status, bool):
            return STATUS_CRIMINAL if status else STATUS_INNOCENT
        if isinstance(status, str):
            s = status.strip().lower()
            if s in {"criminal", "guilty", "true", "c"}:
                return STATUS_CRIMINAL
            if s in {"innocent", "not guilty", "false", "i"}:
                return STATUS_INNOCENT
        raise ValueError(f"Trạng thái không hợp lệ: {status!r}")

    @staticmethod
    def _parse_move(move: Any) -> Tuple[str, str]:
        """Trích xuất (character, status) từ đối tượng move do UI hoặc Agent gửi lên."""
        if isinstance(move, dict):
            char = move.get("character") or move.get("id") or move.get("cell_id")
            status = move.get("status") or move.get("verdict")
        else:
            char = getattr(move, "character", getattr(move, "id", None))
            status = getattr(move, "status", getattr(move, "verdict", None))

        if not char or status is None:
            raise ValueError("Nước đi phải chứa thông tin 'character' và 'status'.")
        return str(char).strip(), GameEngine._normalize_status(status)

    # =========================================================================
    # 3. KIỂM TRA SUY DIỄN LOGIC (ENTAILMENT) & ÁP DỤNG NƯỚC ĐI
    # =========================================================================

    def classify_character(self, cell_or_name: str) -> str:
        """Phân loại một nhân vật dựa trên cơ sở tri thức công khai hiện tại (KB_t).

        Áp dụng định lý Mục 3.4:
        - KB_t |= C_i   <=> KB_t ^ ~C_i là UNSAT  -> trả về 'CRIMINAL'
        - KB_t |= ~C_i  <=> KB_t ^ C_i  là UNSAT  -> trả về 'INNOCENT'
        - Cả hai đều SAT                          -> trả về 'UNKNOWN'
        - Bản thân KB_t là UNSAT                  -> trả về 'INCONSISTENT'
        """
        cid = self.resolve_identifier(cell_or_name)
        secret = self._secret_cells[cid]
        if secret["is_revealed"]:
            return secret["true_status"]

        return KnowledgeBase(self.state, self.oracle).classify(cid)[0]

    def inspect_move(self, move: Any) -> Dict[str, Any]:
        """Đánh giá chi tiết một phán quyết và phân biệt rõ NOT_PROVABLE với CONTRADICTED."""
        try:
            raw_target, submitted_status = self._parse_move(move)
            cid = self.resolve_identifier(raw_target)
        except (ValueError, KeyError) as exc:
            return {
                "valid": False,
                "result": VERDICT_INVALID,
                "cell_id": None,
                "submitted_status": None,
                "entailed_status": None,
                "message": str(exc),
            }

        secret = self._secret_cells[cid]
        if secret["is_revealed"]:
            return {
                "valid": False,
                "result": VERDICT_ALREADY_REVEALED,
                "cell_id": cid,
                "submitted_status": submitted_status,
                "entailed_status": secret["true_status"],
                "message": f"Thẻ {secret['name']} ({cid}) đã được lật từ trước.",
            }

        if self.enforce_logic:
            entailed = self.classify_character(cid)
            if entailed == VERDICT_INCONSISTENT:
                return {
                    "valid": False,
                    "result": VERDICT_INCONSISTENT,
                    "cell_id": cid,
                    "submitted_status": submitted_status,
                    "entailed_status": entailed,
                    "message": "Cơ sở tri thức hiện tại bị mâu thuẫn (INCONSISTENT).",
                }
            if entailed == STATUS_UNKNOWN:
                return {
                    "valid": False,
                    "result": VERDICT_NOT_PROVABLE,
                    "cell_id": cid,
                    "submitted_status": submitted_status,
                    "entailed_status": STATUS_UNKNOWN,
                    "message": f"NOT_PROVABLE: Chưa đủ dữ kiện logic để kết luận về {secret['name']} ({cid}).",
                }
            if entailed != submitted_status:
                return {
                    "valid": False,
                    "result": VERDICT_CONTRADICTED,
                    "cell_id": cid,
                    "submitted_status": submitted_status,
                    "entailed_status": entailed,
                    "message": f"CONTRADICTED: Dữ kiện hiện tại chứng minh kết quả ngược lại cho {secret['name']} ({cid}).",
                }

        # Đối chiếu với đáp án thật của câu đố
        if submitted_status != secret["true_status"]:
            return {
                "valid": False,
                "result": VERDICT_CONTRADICTED,
                "cell_id": cid,
                "submitted_status": submitted_status,
                "entailed_status": secret["true_status"],
                "message": f"CONTRADICTED: Phán quyết trái với trạng thái thực của {secret['name']} ({cid}).",
            }

        return {
            "valid": True,
            "result": VERDICT_ACCEPTED,
            "cell_id": cid,
            "submitted_status": submitted_status,
            "entailed_status": secret["true_status"],
            "message": f"ACCEPTED: Đã xác nhận {secret['name']} ({cid}) là {submitted_status}.",
        }

    def validate_move(self, move: Any) -> bool:
        """Kiểm tra xem một nước đi có hợp lệ và được chứng minh logic trong trạng thái hiện tại hay không."""
        return bool(self.inspect_move(move)["valid"])

    def get_valid_moves(self) -> List[Dict[str, str]]:
        """Trả về tất cả các nước đi hợp lệ (được ép buộc bởi logic KB_t) theo thứ tự row-major."""
        forced_moves: List[Dict[str, str]] = []
        for cid in self.get_row_major_ids():
            if self._secret_cells[cid]["is_revealed"]:
                continue
            if self.enforce_logic:
                entailed = self.classify_character(cid)
                if entailed in {STATUS_CRIMINAL, STATUS_INNOCENT}:
                    forced_moves.append({"character": cid, "status": entailed})
            else:
                forced_moves.append({"character": cid, "status": self._secret_cells[cid]["true_status"]})
        return forced_moves

    def apply_move(self, move: Any) -> bool:
        """Áp dụng một nước đi hợp lệ, lật thẻ và cập nhật KB_{t+1}."""
        inspection = self.inspect_move(move)
        self.state.last_action_result = inspection

        if not inspection["valid"]:
            return False

        # Lưu bản sao trạng thái trước khi cập nhật vào lịch sử
        self.history.append(copy.deepcopy(self.state))

        cid = inspection["cell_id"]
        verdict_status = inspection["submitted_status"]
        secret = self._secret_cells[cid]

        # 1. Mở khóa ô trong dữ liệu ẩn và cập nhật view công khai trên board
        secret["is_revealed"] = True
        self.state.board[cid] = self._build_public_cell_view(cid)

        # 2. Cập nhật verdicts và revealed_clues cho GameEncoder (KB_{t+1})
        verdict_entry = {"character": cid, "status": verdict_status}
        self.state.verdicts.append(verdict_entry)

        revealed_clue = secret.get("compiled_clue")
        if revealed_clue is not None:
            self.state.revealed_clues.append(copy.deepcopy(revealed_clue))

        # 3. Ghi nhận lịch sử lượt đi và kiểm tra chiến thắng
        move_record = {
            "step": self.state.turn + 1,
            "character": cid,
            "name": secret["name"],
            "status": verdict_status,
            "revealed_clue": copy.deepcopy(revealed_clue),
        }
        self.state.moves.append(move_record)
        self.state.turn += 1
        self.state.winner = self.check_winner()

        inspection["revealed_clue"] = copy.deepcopy(revealed_clue)
        return True

    def submit_verdict(self, character: str, status: str) -> Dict[str, Any]:
        """API tiện ích cho UI/Agent: nộp phán quyết và nhận trực tiếp dictionary kết quả chi tiết."""
        self.apply_move({"character": character, "status": status})
        return copy.deepcopy(self.state.last_action_result)

    # =========================================================================
    # 4. CÁC HÀM HỖ TRỢ GUI (HIGHLIGHT, HINT) & KIỂM TRA KẾT THÚC
    # =========================================================================

    def get_highlighted_cells(self, cell_or_clue_owner: str) -> List[str]:
        """Trả về danh sách các mã ô được tham chiếu bởi manh mối của một thẻ đã lật (Mục 4.1)."""
        cid = self.resolve_identifier(cell_or_clue_owner)
        secret = self._secret_cells[cid]
        if not secret["is_revealed"] or secret.get("compiled_clue") is None:
            return []
        return list(secret["compiled_clue"].get("highlighted_cells", []))

    def get_hint(self) -> Optional[Dict[str, Any]]:
        """Tìm một nhân vật có thể chứng minh được ở bước tiếp theo mà KHÔNG đọc đáp án ẩn (Mục 4.1 & 4.4)."""
        for cid in self.get_row_major_ids():
            if self._secret_cells[cid]["is_revealed"]:
                continue
            entailed = self.classify_character(cid)
            if entailed in {STATUS_CRIMINAL, STATUS_INNOCENT}:
                return {
                    "character": cid,
                    "name": self._secret_cells[cid]["name"],
                    "status": entailed,
                    "active_clue_ids": [c.get("id") for c in self.state.revealed_clues],
                }
        return None
    def check_clue_set_uniqueness(self, include_starting_verdicts: bool = True) -> Dict[str, Any]:
        encoder = GameEncoder(self.state)
        encoder.build_variable_map(self.state)
        clauses: List[List[int]] = []
        for secret in self._secret_cells.values():
            clue = secret.get("compiled_clue")
            if clue is not None:
                clauses.extend(encoder.encode_clue(clue))
        assumptions: List[int] = []
        if include_starting_verdicts:
            for v in self.state.verdicts:
                var = encoder.variable_map[v["character"]]
                assumptions.append(var if v["status"] == STATUS_CRIMINAL else -var)
        primary = sorted(encoder.variable_map.values())
        unique, model = check_uniqueness(clauses, primary, assumptions)
        matches = None
        if model is not None:
            matches = all(
                model[encoder.variable_map[cid]] == (s["true_status"] == STATUS_CRIMINAL)
                for cid, s in self._secret_cells.items()
        )
        return {"unique": unique, "matches_hidden_solution": matches, "clauses": len(clauses)}

    def check_winner(self, board: Optional[Dict[str, Dict[str, Any]]] = None) -> Optional[str]:
        """Xác định xem toàn bộ các ô trên bàn cờ đã được giải quyết hết chưa."""
        target_board = board if board is not None else self.state.board
        if not target_board:
            return None
        if all(cell.get("is_revealed", False) for cell in target_board.values()):
            return "Player"
        return None

    def is_game_over(self) -> bool:
        """Trả về True nếu trò chơi đã ở trạng thái kết thúc."""
        return self.state.winner is not None or self.check_winner() is not None

    def evaluate_state(self) -> float:
        """Trả về tỷ lệ phần trăm số ô đã mở khóa trên bàn cờ (từ 0.0 đến 1.0)."""
        if not self.state.board:
            return 0.0
        revealed_count = sum(1 for c in self.state.board.values() if c.get("is_revealed", False))
        return revealed_count / len(self.state.board)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize trạng thái công khai của game để lưu UI hoặc debug."""
        return {
            "size": self.state.size,
            "board": copy.deepcopy(self.state.board),
            "turn": self.state.turn,
            "winner": self.state.winner,
            "moves": copy.deepcopy(self.state.moves),
            "revealed_clues": copy.deepcopy(self.state.revealed_clues),
            "verdicts": copy.deepcopy(self.state.verdicts),
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "GameEngine":
        """Tái tạo một phiên bản GameEngine từ dictionary đã serialize."""
        state = GameState(
            board=copy.deepcopy(payload.get("board", {})),
            turn=int(payload.get("turn", 0)),
            winner=payload.get("winner"),
            moves=copy.deepcopy(payload.get("moves", [])),
            revealed_clues=copy.deepcopy(payload.get("revealed_clues", [])),
            verdicts=copy.deepcopy(payload.get("verdicts", [])),
            size=int(payload.get("size", 3)),
        )
        return cls(initial_state=state)

    # =========================================================================
    # 5. MÀN CHƠI MẶC ĐỊNH (3x3 SOLVABLE NO-GUESS PUZZLE)
    # =========================================================================

    @staticmethod
    def _get_default_puzzle() -> Dict[str, Any]:
        """Màn chơi 3x3 mặc định, có nghiệm duy nhất và giải được hoàn toàn bằng suy diễn từng bước.

        Chuỗi suy diễn không đoán mò:
        1. Ban đầu A1 (Abel) đã lật (INNOCENT), manh mối: Hàng 1 có đúng 2 CRIMINAL -> B1 và C1 là CRIMINAL.
        2. Lật B1 (Bea): Cột B có đúng 1 CRIMINAL -> Vì B1 đã là CRIMINAL nên B2, B3 là INNOCENT.
        3. Lật C1 (Clara): C1 và C2 khác trạng thái -> C2 là INNOCENT.
        4. Lật B2 (Eliza): A2 và B1 cùng trạng thái -> A2 là CRIMINAL.
        5. Lật B3 (Hannah): Hàng 3 có đúng 1 CRIMINAL, mà B3 là INNOCENT; kết hợp manh mối của C2
           (C3 có cùng trạng thái với B2 là INNOCENT) -> C3 là INNOCENT và A3 là CRIMINAL.
        """
        return {
            "size": 3,
            "cells": [
                {
                    "id": "A1",
                    "name": "Abel",
                    "profession": "Astronaut",
                    "status": STATUS_INNOCENT,
                    "is_revealed": True,
                    "clue": {
                        "type": "EXACTLY",
                        "text": "Exactly 2 people in Row 1 are Criminals.",
                        "region": {"type": "ROW", "params": 1},
                        "count": 2,
                    },
                },
                {
                    "id": "B1",
                    "name": "Bea",
                    "profession": "Cook",
                    "status": STATUS_CRIMINAL,
                    "is_revealed": False,
                    "clue": {
                        "type": "EXACTLY",
                        "text": "Exactly 1 person in Column B is a Criminal.",
                        "region": {"type": "COL", "params": "B"},
                        "count": 1,
                    },
                },
                {
                    "id": "C1",
                    "name": "Clara",
                    "profession": "Guard",
                    "status": STATUS_CRIMINAL,
                    "is_revealed": False,
                    "clue": {
                        "type": "DIFFERENT",
                        "text": "Clara and Franz (C2) have different statuses.",
                        "character1": "C1",
                        "character2": "C2",
                    },
                },
                {
                    "id": "A2",
                    "name": "Derek",
                    "profession": "Cook",
                    "status": STATUS_CRIMINAL,
                    "is_revealed": False,
                    "clue": {
                        "type": "AT_LEAST",
                        "text": "At least 2 neighbors of Eliza (B2) are Criminals.",
                        "region": {"type": "NEIGHBORS", "params": "B2"},
                        "count": 2,
                    },
                },
                {
                    "id": "B2",
                    "name": "Eliza",
                    "profession": "Detective",
                    "status": STATUS_INNOCENT,
                    "is_revealed": False,
                    "clue": {
                        "type": "SAME",
                        "text": "Derek (A2) and Bea (B1) have the same status.",
                        "character1": "A2",
                        "character2": "B1",
                    },
                },
                {
                    "id": "C2",
                    "name": "Franz",
                    "profession": "Detective",
                    "status": STATUS_INNOCENT,
                    "is_revealed": False,
                    "clue": {
                        "type": "SAME",
                        "text": "Ivy (C3) and Eliza (B2) have the same status.",
                        "character1": "C3",
                        "character2": "B2",
                    },
                },
                {
                    "id": "A3",
                    "name": "Grant",
                    "profession": "Clerk",
                    "status": STATUS_CRIMINAL,
                    "is_revealed": False,
                    "clue": {
                        "type": "FACT",
                        "text": "Grant (A3) is a Criminal.",
                        "character": "A3",
                        "status": STATUS_CRIMINAL,
                    },
                },
                {
                    "id": "B3",
                    "name": "Hannah",
                    "profession": "Guard",
                    "status": STATUS_INNOCENT,
                    "is_revealed": False,
                    "clue": {
                        "type": "EXACTLY",
                        "text": "Exactly 1 person in Row 3 is a Criminal.",
                        "region": {"type": "ROW", "params": 3},
                        "count": 1,
                    },
                },
                {
                    "id": "C3",
                    "name": "Ivy",
                    "profession": "Clerk",
                    "status": STATUS_INNOCENT,
                    "is_revealed": False,
                    "clue": {
                        "type": "AT_MOST",
                        "text": "At most 2 people in Column C are Criminals.",
                        "region": {"type": "COL", "params": "C"},
                        "count": 2,
                    },
                },
            ],
        }