# Kết quả thí nghiệm (mục 4.5)
Timeout mỗi ca: 30.0s. Runtime là trung vị của 1 lần chạy. Tổng số ca: 22; ca không giải được: 6.

## Tổng hợp theo kích thước (trung bình trên các ca SOLVED)
| Size | Config | Solved | Lỗi/timeout | Biến chính | Biến phụ | Mệnh đề | Gọi SAT | Decisions | Propagations | Backtracks | Bước | Đợt | Runtime (s) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 3x3 | DPLL | 3/5 | ERROR:ValueError, STUCK | 9 | 0 | 75.3 | 62.7 | 0 | 319.7 | 0 | 8 | 3.3 | 0.0033 |
| 3x3 | DPLL+pure-literal | 3/5 | ERROR:ValueError, STUCK | 9 | 0 | 75.3 | 62.7 | 0 | 319.7 | 0 | 8 | 3.3 | 0.0037 |
| 4x4 | DPLL | 4/5 | TIMEOUT | 16 | 0 | 225.5 | 169 | 66.2 | 1229 | 2 | 15 | 6 | 0.0207 |
| 4x4 | DPLL+pure-literal | 4/5 | TIMEOUT | 16 | 0 | 225.5 | 169 | 54.2 | 1254.5 | 2 | 15 | 6 | 0.0200 |
| 5x5 | DPLL | 1/1 | - | 25 | 0 | 293 | 217 | 258 | 2899 | 0 | 24 | 5 | 0.0486 |
| 5x5 | DPLL+pure-literal | 1/1 | - | 25 | 0 | 293 | 217 | 258 | 2899 | 0 | 24 | 5 | 0.0371 |

## Chi tiết từng ca
| puzzle | size | config | status | primary_vars | aux_vars | clauses | sat_calls | decisions | propagations | backtracks | steps | waves | runtime_s | unique | expected |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 3x3_01.json | 3 | DPLL | SOLVED | 9 | 0 | 63 | 77 | 0 | 343 | 0 | 8 | 5 | 0.0030 | True | SOLVED |
| 3x3_02.json | 3 | DPLL | SOLVED | 9 | 0 | 32 | 59 | 0 | 310 | 0 | 8 | 3 | 0.0022 | True | SOLVED |
| 3x3_03.json | 3 | DPLL | SOLVED | 9 | 0 | 131 | 52 | 0 | 306 | 0 | 8 | 2 | 0.0046 | True | SOLVED |
| 3x3_04.json | 3 | DPLL | STUCK | 9 | 0 | 1 | 17 | 0 | 17 | 0 | 0 | 0 | 0.0001 | False | STUCK |
| 3x3_05.json | 3 | DPLL | ERROR:ValueError |  |  |  |  |  |  |  |  |  |  |  | ERROR |
| 4x4_01.json | 4 | DPLL | SOLVED | 16 | 0 | 373 | 138 | 168 | 1292 | 8 | 15 | 5 | 0.0307 | True | SOLVED |
| 4x4_02.json | 4 | DPLL | SOLVED | 16 | 0 | 236 | 175 | 33 | 1194 | 0 | 15 | 6 | 0.0247 | True | SOLVED |
| 4x4_03.json | 4 | DPLL | SOLVED | 16 | 0 | 212 | 148 | 64 | 1080 | 0 | 15 | 5 | 0.0184 | True | SOLVED |
| 4x4_04.json | 4 | DPLL | SOLVED | 16 | 0 | 81 | 215 | 0 | 1350 | 0 | 15 | 8 | 0.0089 | True | SOLVED |
| 4x4_05.json | 4 | DPLL | TIMEOUT | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0.0000 | True | TIMEOUT |
| 5x5_01.json | 5 | DPLL | SOLVED | 25 | 0 | 293 | 217 | 258 | 2899 | 0 | 24 | 5 | 0.0486 | True | SOLVED |
| 3x3_01.json | 3 | DPLL+pure-literal | SOLVED | 9 | 0 | 63 | 77 | 0 | 343 | 0 | 8 | 5 | 0.0034 | True | SOLVED |
| 3x3_02.json | 3 | DPLL+pure-literal | SOLVED | 9 | 0 | 32 | 59 | 0 | 310 | 0 | 8 | 3 | 0.0022 | True | SOLVED |
| 3x3_03.json | 3 | DPLL+pure-literal | SOLVED | 9 | 0 | 131 | 52 | 0 | 306 | 0 | 8 | 2 | 0.0055 | True | SOLVED |
| 3x3_04.json | 3 | DPLL+pure-literal | STUCK | 9 | 0 | 1 | 17 | 0 | 17 | 0 | 0 | 0 | 0.0001 | False | STUCK |
| 3x3_05.json | 3 | DPLL+pure-literal | ERROR:ValueError |  |  |  |  |  |  |  |  |  |  |  | ERROR |
| 4x4_01.json | 4 | DPLL+pure-literal | SOLVED | 16 | 0 | 373 | 138 | 168 | 1296 | 8 | 15 | 5 | 0.0378 | True | SOLVED |
| 4x4_02.json | 4 | DPLL+pure-literal | SOLVED | 16 | 0 | 236 | 175 | 31 | 1198 | 0 | 15 | 6 | 0.0194 | True | SOLVED |
| 4x4_03.json | 4 | DPLL+pure-literal | SOLVED | 16 | 0 | 212 | 148 | 18 | 1174 | 0 | 15 | 5 | 0.0154 | True | SOLVED |
| 4x4_04.json | 4 | DPLL+pure-literal | SOLVED | 16 | 0 | 81 | 215 | 0 | 1350 | 0 | 15 | 8 | 0.0073 | True | SOLVED |
| 4x4_05.json | 4 | DPLL+pure-literal | TIMEOUT | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0.0000 | True | TIMEOUT |
| 5x5_01.json | 5 | DPLL+pure-literal | SOLVED | 25 | 0 | 293 | 217 | 258 | 2899 | 0 | 24 | 5 | 0.0371 | True | SOLVED |
