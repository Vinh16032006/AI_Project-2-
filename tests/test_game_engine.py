import unittest
from Source.game_engine import (
    GameEngine, 
    STATUS_CRIMINAL, 
    STATUS_INNOCENT, 
    VERDICT_ACCEPTED, 
    VERDICT_NOT_PROVABLE,
    VERDICT_CONTRADICTED
)

class TestGameEngine(unittest.TestCase):
    def setUp(self):
        """Khởi tạo GameEngine với màn chơi 3x3 mặc định trước mỗi bài test."""
        self.engine = GameEngine()

    def test_01_initial_state(self):
        """Kiểm tra trạng thái công khai ban đầu (Public State)."""
        # Ô A1 phải được lật sẵn và có status là INNOCENT
        self.assertTrue(self.engine.state.board["A1"]["is_revealed"])
        self.assertEqual(self.engine.state.board["A1"]["status"], STATUS_INNOCENT)
        
        # Ô B1 phải bị ẩn và status công khai là UNKNOWN
        self.assertFalse(self.engine.state.board["B1"]["is_revealed"])
        self.assertEqual(self.engine.state.board["B1"]["status"], "UNKNOWN")

    def test_02_resolve_regions(self):
        """Kiểm tra bộ biên dịch tọa độ và vùng (Regions)."""
        # Kiểm tra hàm lấy hàng xóm của B2 (phải là 8 ô xung quanh)
        neighbors = self.engine.resolve_region({"type": "NEIGHBORS", "params": "B2"})
        expected_neighbors = {"A1", "B1", "C1", "A2", "C2", "A3", "B3", "C3"}
        self.assertEqual(set(neighbors), expected_neighbors)
        
        # Kiểm tra vùng ROW 1
        row1 = self.engine.resolve_region({"type": "ROW", "params": 1})
        self.assertEqual(set(row1), {"A1", "B1", "C1"})

    def test_03_logic_deduction_accept(self):
        """Kiểm tra khả năng chấp nhận phán quyết đúng logic (No-guess)."""
        # Ở bước đầu tiên, theo logic manh mối A1, ô B1 BẮT BUỘC là CRIMINAL
        result = self.engine.submit_verdict("B1", STATUS_CRIMINAL)
        
        self.assertEqual(result["result"], VERDICT_ACCEPTED)
        self.assertTrue(self.engine.state.board["B1"]["is_revealed"])
        self.assertEqual(self.engine.state.board["B1"]["status"], STATUS_CRIMINAL)

    def test_04_logic_deduction_reject_guess(self):
        """Kiểm tra khả năng TỪ CHỐI các phán quyết đoán mò (Guessing)."""
        # Ở bước đầu tiên, chưa đủ dữ kiện logic để chứng minh A2 là gì.
        # Nộp phán quyết cho A2 sẽ bị từ chối với mã NOT_PROVABLE.
        result = self.engine.submit_verdict("A2", STATUS_CRIMINAL)
        
        self.assertEqual(result["result"], VERDICT_NOT_PROVABLE)
        self.assertFalse(self.engine.state.board["A2"]["is_revealed"])

    def test_05_logic_deduction_reject_contradiction(self):
        """Kiểm tra khả năng TỪ CHỐI các phán quyết ngược logic."""
        # Logic ép buộc B1 là CRIMINAL, nếu cố tình nộp INNOCENT sẽ bị báo mâu thuẫn.
        result = self.engine.submit_verdict("B1", STATUS_INNOCENT)
        self.assertEqual(result["result"], VERDICT_CONTRADICTED)

if __name__ == '__main__':
    unittest.main()