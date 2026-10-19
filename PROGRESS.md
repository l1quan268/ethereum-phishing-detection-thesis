# Tiến Độ Dự Án Khóa Luận Tốt Nghiệp

> **Đề tài:** Learning Unified Graph Representations for Ethereum Phishing Detection under Incomplete Labels and Temporal Shifts  
> **Cập nhật ngày:** 2026-10-16  
> **Trạng thái tổng thể:** Đã hoàn thành Pilot 10 Positive + 10 Unlabeled (PU-Learning), Lọc Point-in-Time Cutoff 7 ngày, Xuất tập dữ liệu 20 địa chỉ & Bộ kiểm thử toàn vẹn tự động (6/6 PASSED).

---

## 1. Trạng thái các cột mốc (Milestones)

| STT | Nhiệm vụ / Hạng mục | Trạng thái | Ghi chú & Kết quả |
| :---: | :--- | :---: | :--- |
| **1** | **Khảo sát & Kiểm toán dữ liệu SIGMETRICS 2025** | ✅ Hoàn thành | Đã phân tích `data/raw/phishing_contracts.log` (37.654 địa chỉ), `phishing_transactions.log` (211.319 tx hashes), `suspicious_keywords.log` (35 từ khóa). Xuất báo cáo `reports/audit/dataset_audit.md`. |
| **2** | **Đặc tả Schema nhãn & 3 Views đặc trưng** | ✅ Hoàn thành | Thiết kế `configs/label_schema.csv` và `docs/three_views_spec.md` (View 1: Tabular/Statistical, View 2: Temporal Sequences, View 3: Multi-relational Ego-Graph). |
| **3** | **Kế hoạch thu thập dữ liệu On-Chain** | ✅ Hoàn thành | Soạn thảo `docs/data_collection_plan.md`, phân tích chi phí, rate limit Etherscan Free vs Alchemy. |
| **4** | **Pipeline Etherscan API V2 (Pilot 10 địa chỉ)** | ✅ Hoàn thành | Viết `src/collect_etherscan.py` có rate limit 2 req/s, exponential backoff retry, raw JSON cache, resume, không log API key. |
| **5** | **Thực thi thử nghiệm 10 địa chỉ Positive** | ✅ Hoàn thành | Chạy thành công 10/10 địa chỉ (100%), tìm được 100% creation block & timestamp, thu thập 16 giao dịch thực tế (normal, internal, erc20). |
| **6** | **Đối chiếu Ground Truth SIGMETRICS** | ✅ Hoàn thành | 6/10 địa chỉ có giao dịch trùng khớp chính xác trong `phishing_transactions.log`, các giao dịch có signature `claim(address,uint256)` trùng khớp `suspicious_keywords.log`. |
| **7** | **Tạo các báo cáo bắt buộc** | ✅ Hoàn thành | Xuất `pilot_addresses.csv`, `pilot_timestamp_report.csv`, `pilot_transactions.parquet`, `api_collection_log.csv`, `bao_cao_pilot_vi.md`, `README_PILOT_VI.md`. |
| **8** | **Chuẩn hóa cấu trúc dự án & Tổ chức workspace ML** | ✅ Hoàn thành | Tái cấu trúc workspace phân tầng: `data/raw`, `data/cache`, `data/pilot/positive`, `data/pilot/unlabeled`, `data/pilot/combined`, `data/processed/view1..3`, `src/`, `configs/`, `reports/`, `docs/`, `experiments/`, `tests/`. Di chuyển an toàn 14 file với xác thực SHA-256 100% qua `reports/migration_manifest.json`. Thiết lập `.gitignore`. |
| **9** | **Thu thập 10 Unlabeled & Lọc Point-in-Time 20 Địa Chỉ** | ✅ Hoàn thành | Thực hiện Matched Block Sampling trong phạm vi $\pm 14$ blocks từ Creation Block của 10 Positive. Lọc bỏ 100% địa chỉ phishing. Thu thập 5.209 giao dịch Unlabeled. Áp dụng $T_{\text{cutoff}} = T_{\text{creation}} + 7\text{ ngày}$. Loại bỏ 2.260 giao dịch tương lai, giữ lại 2.965 giao dịch sạch không rò rỉ thời gian. Xuất `pilot_20_quality_report.md`. |
| **10** | **Trích xuất View 1 (Statistical Features - Pilot 20)** | ✅ Hoàn thành | Đã xây dựng `src/build_view1.py`, trích xuất 32 đặc trưng thống kê cho 20 hợp đồng, phân tách metadata và bảng kiểm toán 4 giao dịch tiền triển khai. Đạt 9/9 unit tests (`tests/test_view1.py`). Xuất `docs/view1_feature_spec.md` và `reports/pilot/view1_data_quality.md`. |
| **11** | **Mở rộng quy mô lên 400 địa chỉ & Xây dựng mô hình GNN** | ⏸️ Chờ phê duyệt | Sẵn sàng mở rộng sau khi nghiệm thu kết quả pilot View 1 và phương pháp luận. |

---

## 2. Cấu Trúc Workspace & Vị Trí Các Tệp Hiện Tại

```text
ethereum-phishing-detection-thesis/
├── .env                                  # Chứa ETHERSCAN_API_KEY (Bảo mật, KHÔNG commit)
├── .env.example                          # Template biến môi trường mẫu
├── .gitignore                            # Quy tắc loại trừ .env, .venv, data/cache/
├── .venv/                                # Môi trường ảo Python (Python 3.11+)
├── PROGRESS.md                           # Bảng theo dõi tiến độ tổng thể các cột mốc
├── README.md                             # Tài liệu tổng quan dự án và hướng dẫn chạy
├── requirements.txt                      # Danh sách Python dependencies của dự án
│
├── configs/                              # Cấu hình pipeline & đặc tả schema
│   └── label_schema.csv                  # Schema 6 cột chuẩn hóa cho quản lý nhãn
│
├── data/                                 # Quản lý dữ liệu phân tầng chặt chẽ
│   ├── raw/                              # Dữ liệu gốc từ paper SIGMETRICS 2025
│   │   ├── phishing_contracts.log        # 37,654 địa chỉ hợp đồng lừa đảo
│   │   ├── phishing_transactions.log     # 211,319 mã băm giao dịch lừa đảo
│   │   └── suspicious_keywords.log       # 35 từ khóa hàm lừa đảo phổ biến
│   ├── cache/                            # Bộ đệm JSON thô từ Etherscan API V2
│   │   ├── blocks/                       # Cache JSON các khối đã truy vấn
│   │   ├── receipts/                     # Cache JSON các transaction receipts
│   │   └── <address>/                    # Cache 5 actions cho cả 20 địa chỉ (100 files)
│   ├── pilot/                            # Dữ liệu thử nghiệm quy mô nhỏ (Pilot)
│   │   ├── positive/                     # Dữ liệu pilot 10 Positive
│   │   │   ├── pilot_addresses.csv       # 10 địa chỉ Positive chuẩn schema
│   │   │   └── pilot_transactions.parquet# 16 giao dịch on-chain chuẩn hóa
│   │   ├── unlabeled/                    # Dữ liệu pilot 10 Unlabeled đối chứng
│   │   │   ├── pilot_unlabeled_addresses.csv       # 10 địa chỉ Unlabeled kèm cutoff 7 ngày
│   │   │   └── pilot_unlabeled_transactions.parquet# 5,209 giao dịch thô on-chain
│   │   └── combined/                     # Dữ liệu tổng hợp 20 địa chỉ sau cắt thời gian
│   │       ├── pilot_20_addresses.csv              # 20 địa chỉ (10 Pos + 10 Unlabeled)
│   │       └── pilot_20_transactions_before_cutoff.parquet # 2,965 giao dịch sạch trước cutoff
│   ├── processed/                        # Dữ liệu đặc trưng đã qua xử lý theo 3 View
│   │   ├── view1/                        # Statistical Tabular Features (Đã chuẩn hóa & Kiểm toán Pilot 20)
│   │   │   ├── view1_features_pilot.parquet     # 20 dòng, 32 đặc trưng số học thuần túy
│   │   │   ├── view1_features_pilot.csv         # Phiên bản CSV của ma trận đặc trưng
│   │   │   ├── view1_metadata_pilot.parquet     # Bảng metadata cô lập nhãn (PU-Learning)
│   │   │   ├── view1_metadata_pilot.csv         # Phiên bản CSV của metadata
│   │   │   ├── view1_precreation_audit_pilot.csv# Kiểm toán 4 bản ghi tiền triển khai (CREATE2)
│   │   │   └── backup_v1/                       # Bản sao lưu kết quả View 1 ban đầu
│   │   ├── view2/                        # Temporal Transaction Sequences
│   │   └── view3/                        # Multi-relational Ego-Graph
│   └── full/                             # Dữ liệu thu thập diện rộng sau này (400+ địa chỉ)
│
├── docs/                                 # Tài liệu kỹ thuật, đặc tả và kế hoạch
│   ├── pipeline_view1_latest.pdf         # Sơ đồ kiến trúc vector PDF chất lượng cao của View 1
│   ├── three_views_spec.md               # Đặc tả chi tiết toán học và schema 3 View
│   ├── view1_feature_spec.md             # Đặc tả toán học 32 đặc trưng View 1 & NOT_AVAILABLE
│   ├── VIEW1_PIPELINE_VI.md              # Tài liệu trực quan giải thích pipeline View 1 phục vụ seminar
│   ├── data_collection_plan.md           # Kế hoạch thu thập dữ liệu on-chain
│   ├── README_PILOT_VI.md                # Hướng dẫn chi tiết dòng lệnh PowerShell
│   └── README_NEXT_STEPS_VI.md           # Kế hoạch triển khai pilot 10 Unlabeled
│
├── experiments/                          # Lưu trữ checkpoints, mô hình và logs thực nghiệm
│
├── reports/                              # Báo cáo khoa học và kiểm toán
│   ├── audit/
│   │   └── dataset_audit.md              # Báo cáo kiểm toán toàn diện dataset gốc
│   ├── pilot/
│   │   ├── bao_cao_pilot_vi.md           # Báo cáo kết quả khoa học 10 địa chỉ pilot
│   │   ├── pilot_timestamp_report.csv    # Thống kê khối tạo lập & dải thời gian tx Positive
│   │   ├── api_collection_log.csv        # Nhật ký kiểm toán 100% request API Positive
│   │   ├── pilot_20_quality_report.md    # Báo cáo đánh giá chất lượng 20 địa chỉ Pilot
│   │   ├── view1_data_quality.md         # Báo cáo kiểm toán sơ bộ View 1
│   │   └── view1_final_audit.md          # Báo cáo kiểm toán ngữ nghĩa EVM & chốt View 1 Pilot 20
│   ├── experiments/                      # Báo cáo kết quả đánh giá mô hình ML/GNN
│   └── migration_manifest.json           # Bản manifest SHA-256 xác thực di chuyển 14 tệp
│
├── src/                                  # Mã nguồn Python chính của dự án
│   ├── __init__.py                       # Khai báo package src
│   ├── collect_etherscan.py              # Pipeline thu thập dữ liệu Etherscan API V2
│   ├── sample_unlabeled.py               # Module Matched Block Sampling & Point-in-Time Cutoff
│   └── build_view1.py                    # Pipeline trích xuất đặc trưng thống kê View 1 (Đã chuẩn hóa EVM)
│
└── tests/                                # Bộ kiểm thử tự động
    ├── test_data_integrity.py            # Kiểm thử toàn vẹn dữ liệu & cutoff (6/6 PASSED)
    ├── test_cache_resume.py              # Kiểm thử cơ chế cache & resume 20 địa chỉ (3/3 PASSED)
    └── test_view1.py                     # Kiểm thử 12 tiêu chí khoa học & ngữ nghĩa EVM View 1 (12/12 PASSED)
```

---

## 3. Kết Quả Thu Thập Tập 20 Mẫu & Lọc Point-in-Time

1. **10 cặp ghép thời kỳ (Matched Pairs):**
   - 100% hợp đồng Unlabeled được tìm thấy trong dải $\pm 14$ blocks từ khối tạo lập của hợp đồng Positive tương ứng (độ lệch thời gian chỉ từ 24s đến 168s).
   - 0 địa chỉ trùng lặp giữa 2 nhóm; 0 địa chỉ Unlabeled xuất hiện trong `phishing_contracts.log`.
2. **Khống chế rò rỉ thời gian (Point-in-Time Invariant):**
   - Áp dụng $T_{\text{cutoff}} = T_{\text{creation}} + 7\text{ ngày}$ ($604.800$ giây).
   - Tổng giao dịch thu thập thô: **5.225 giao dịch** (16 Positive + 5.209 Unlabeled).
   - Giao dịch sạch còn lại trước cutoff: **2.965 giao dịch** (15 Positive + 2.950 Unlabeled).
   - Giao dịch sau cutoff bị loại bỏ an toàn: **2.260 giao dịch** (trong đó có giao dịch tháng 06/2025 của Positive `0x6a87...`).
3. **Phân bố giao dịch trước Cutoff:**
   - ERC-20 transfer: 1.542 giao dịch (52.0%).
   - Internal transaction: 756 giao dịch (25.5%).
   - Normal transaction: 667 giao dịch (22.5%).
4. **Trích xuất đặc trưng View 1:**
   - 20 hợp đồng (10 Positive + 10 Unlabeled).
   - 32 đặc trưng số học được tính toán trên 2.961 bản ghi hợp lệ ($T_{\text{creation}} \le T_{\text{tx}} < T_{\text{cutoff}}$).
   - 4 bản ghi tiền triển khai (CREATE2) được cách ly an toàn vào bảng kiểm toán riêng.
   - 9/9 tiêu chí kiểm thử tự động vượt qua (100% PASSED).

---

## 4. Các Bước Tiếp Theo (Chờ Người Dùng Phê Duyệt)

1. **Nghiệm thu chất lượng dữ liệu View 1 Pilot 20 hợp đồng:**
   - Đánh giá báo cáo [view1_data_quality.md](file:///d:/KH%C3%93A%20LU%E1%BA%ACN/phishing_contract_sigmetrics25/reports/pilot/view1_data_quality.md) và tài liệu toán học [view1_feature_spec.md](file:///d:/KH%C3%93A%20LU%E1%BA%ACN/phishing_contract_sigmetrics25/docs/view1_feature_spec.md).
2. **Xin ý kiến mở rộng quy mô lên 400 địa chỉ (200 Positive + 200 Unlabeled):**
   - Áp dụng pipeline thu thập `src/sample_unlabeled.py` và trích xuất `src/build_view1.py` trên tập 400 địa chỉ.
3. **Triển khai View 2 (Temporal Sequence) & View 3 (Ego-Graph):**
   - Tuân thủ cùng nguyên tắc Temporal Cutoff 7 ngày và phân tách sự kiện/tài sản.
