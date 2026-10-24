<!-- File: PROGRESS.md -->
# Tiến Độ Dự Án Khóa Luận Tốt Nghiệp

> **Đề tài:** Learning Unified Graph Representations for Ethereum Phishing Detection under Incomplete Labels and Temporal Shifts  
> **Cập nhật ngày:** 2026-10-24  
> **Trạng thái tổng thể:** Hoàn thành Pilot 20 (cấp hợp đồng) cho View 1 và View 2. View 2 cấp hợp đồng kích hoạt tiêu chí dừng (chuỗi positive quá ngắn), nên đang chuyển sang **cấp tài khoản** theo đề cương với nhãn **DaaS dataset (IMC 2025)**: đã thu lịch sử giao dịch và `evidence_time` cho 6.141 tài khoản positive. Đang chờ chốt t\*, mốc chia thời gian và cách lấy mẫu U.

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
| **11** | **Mở rộng quy mô lên 400 địa chỉ & Xây dựng mô hình GNN** | ⏸️ Thay thế | Không mở rộng ở cấp hợp đồng nữa (xem mốc 12–14); quy mô mới là 6.141 tài khoản P từ DaaS. |
| **12** | **Pipeline View 2 (Temporal Sequences) – Pilot 20, cấp hợp đồng** | ✅ Hoàn thành | Viết `src/view2/` (client Etherscan cache theo tham số, `collect_events.py`, `build_sequences.py`, `adapt_pilot.py`, `check_client.py`); 12/12 tests (`tests/test_view2_pipeline.py`). Thu lại bằng API: 20/20 `ok`, 4.648 sự kiện (normal 667, internal 1.618, erc20 2.363), đủ `transactionIndex`. Cửa sổ `obs_start = min(T_creation, giao dịch đầu)` giữ được giao dịch nạn nhân trước triển khai ở 4/10 P. **Tiêu chí dừng bị kích hoạt:** chuỗi P trung vị 1, tối đa 2. |
| **13** | **Khảo sát dataset & chọn nguồn nhãn cấp tài khoản** | ✅ Hoàn thành | Đọc toàn văn bài DaaS (IMC 2025); kiểm tra PTXPhish, MetaMask, Etherscan labels, BigQuery. Chọn **DaaS** làm nhãn P chính (56 operator + 6.087 affiliate; tác giả kiểm tra thủ công 44,8% giao dịch, không thấy dương tính giả). SIGMETRICS dùng để giải thích lý do chuyển cấp, kiểm chứng suy nhãn, mở rộng P (tùy chọn) và loại nạn nhân. Chồng lấn: 1.209/1.910 profit-sharing contract nằm trong SIGMETRICS. Pilot: 6/6 địa chỉ suy ra từ dòng tiền khớp vai trò DaaS. |
| **14** | **Thu dữ liệu 6.141 tài khoản DaaS & `evidence_time`** | ✅ Hoàn thành | Thời điểm tạo 1.910 profit-sharing contract: 07/02/2023 – 01/04/2025. Phân loại 6.143 tài khoản: 6.141 EOA (210 có mã EIP-7702), 2 hợp đồng. `src/daas/collect_account_events.py`: 6.141/6.141 tìm được `evidence_time` (internal 3.146, erc20 2.985, normal 10); trung vị 55 sự kiện/tài khoản; 68% ví bắt đầu hoạt động dưới 1 ngày trước lần nhận tiền chia đầu; 52,5% không có giao dịch nào trước `evidence_time`. Tổng 19.101 lượt gọi API. |
| **15** | **Chốt thiết kế benchmark cấp tài khoản** | ⏸️ Chờ quyết định | t\* (đề xuất: `evidence_time` + 1 ngày, kèm ablation bỏ giao dịch chia lợi nhuận); T1/T2 (đề xuất: train ≤ 03/2024, val 04–09/2024, test 10/2024–04/2025 → 3.169 / 1.784 / 1.188 P); lấy mẫu U (EOA ngẫu nhiên cùng tháng, k × số P); xin GVHD đồng ý cập nhật nguồn nhãn trong đề cương. |

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
│   │   ├── suspicious_keywords.log       # 35 từ khóa hàm lừa đảo phổ biến
│   │   └── daas/                         # Clone repo DaaS_dataset (IMC 2025), không commit
│   ├── interim/                          # Đầu ra trung gian (không commit): view2/, view2_pilot/, daas_*.csv, daas_accounts/
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
│   │   ├── view2/                        # Temporal Transaction Sequences (Pilot 20, cấp hợp đồng)
│   │   ├── view2_pilot/                  # View 2 dựng offline từ dữ liệu pilot cũ
│   │   └── view3/                        # Multi-relational Ego-Graph
│   └── full/                             # Dữ liệu thu thập diện rộng sau này (400+ địa chỉ)
│
├── docs/                                 # Tài liệu kỹ thuật, đặc tả và kế hoạch
│   ├── pipeline_view1_latest.pdf         # Sơ đồ kiến trúc vector PDF chất lượng cao của View 1
│   ├── three_views_spec.md               # Đặc tả chi tiết toán học và schema 3 View
│   ├── view1_feature_spec.md             # Đặc tả toán học 32 đặc trưng View 1 & NOT_AVAILABLE
│   ├── VIEW1_PIPELINE_VI.md              # Tài liệu trực quan giải thích pipeline View 1 phục vụ seminar
│   ├── ACCOUNT_LEVEL_DAAS_VI.md          # Chuyển sang cấp tài khoản với DaaS: dữ liệu, kết quả, quyết định chờ chốt
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
│   ├── build_view1.py                    # Pipeline trích xuất đặc trưng thống kê View 1 (Đã chuẩn hóa EVM)
│   ├── view2/                            # Pipeline View 2: etherscan_client, check_client, collect_events, build_sequences, adapt_pilot
│   └── daas/                             # Dữ liệu cấp tài khoản: collect_account_events (lịch sử giao dịch + evidence_time)
│
└── tests/                                # Bộ kiểm thử tự động
    ├── test_data_integrity.py            # Kiểm thử toàn vẹn dữ liệu & cutoff (6/6 PASSED)
    ├── test_cache_resume.py              # Kiểm thử cơ chế cache & resume 20 địa chỉ (3/3 PASSED)
    ├── test_view1.py                     # Kiểm thử 12 tiêu chí khoa học & ngữ nghĩa EVM View 1 (12/12 PASSED)
    └── test_view2_pipeline.py            # 12 test bất biến của pipeline View 2 (12/12 PASSED)
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

## 3.1 Kết Quả View 2 Cấp Hợp Đồng & Dữ Liệu Cấp Tài Khoản (DaaS)

1. **View 2 cấp hợp đồng (Pilot 20, dữ liệu API):**

   | label_status | n | min | median | mean | max | có sự kiện trước deploy |
   |---|---|---|---|---|---|---|
   | positive | 10 | 1 | 1.0 | 1.4 | 2 | 4 |
   | unlabeled | 10 | 1 | 2.0 | 221.5 | 2135 | 0 |

   Hợp đồng phishing gần như dùng một lần, nên không có động thái theo thời gian để mô hình chuỗi học. Đây là cơ sở thực nghiệm cho việc chuyển sang cấp tài khoản.
2. **DaaS dataset:** 56 operator + 6.087 affiliate (6.141 EOA), 1.910 profit-sharing contract, 87.077 profit-sharing transaction; giai đoạn 03/2023 – 04/2025.
3. **`evidence_time` của 6.141 EOA (lần đầu tham gia chia lợi nhuận):** tìm được 100%.

   | Số giao dịch trước `evidence_time` | 0 | 1–2 | 3–9 | 10–99 | 100+ |
   |---|---|---|---|---|---|
   | Số tài khoản | 3.225 | 1.006 | 838 | 901 | 171 |

   Trong 24 giờ đầu kể từ `evidence_time`: trung vị 3 giao dịch, P90 19.
4. **Phân phối `evidence_time` theo tháng:** tăng dần từ 03/2023, đỉnh 03/2024 (460), giảm từ 01/2025. Tỉ lệ tích lũy: 51,6% đến hết 03/2024; 80,7% đến hết 09/2024.

Chi tiết và đoạn mã tái lập: [`docs/ACCOUNT_LEVEL_DAAS_VI.md`](docs/ACCOUNT_LEVEL_DAAS_VI.md).

---

## 4. Các Bước Tiếp Theo (Chờ Người Dùng Phê Duyệt)

1. **Chốt với GVHD:**
   - Chuyển bài toán sang cấp tài khoản và cập nhật nguồn nhãn trong đề cương (DaaS + SIGMETRICS; XBlock-ETH chỉ để tái hiện baseline).
   - Thiết lập t\* chính: `evidence_time` + 1 ngày ("phát hiện sau lần nhận tiền lừa đầu tiên"), kèm ablation bỏ giao dịch chia lợi nhuận, và phân tích phụ Δ = 0 trên 1.910 P có ≥ 3 giao dịch trước `evidence_time`.
2. **Chốt mốc chia theo tháng của t\*:** đề xuất train ≤ 03/2024, val 04–09/2024, test 10/2024–04/2025.
3. **Lấy mẫu U:** EOA ngẫu nhiên trên toàn mạng, cùng tháng với P, số U = k × số P mỗi tháng (pilot k = 5; chính thức k = 10). Chọn công cụ: Etherscan (cách lấy theo giao dịch có hiệu chỉnh) hay BigQuery (lấy đều theo địa chỉ).
4. **Chuyển các đoạn mã khảo sát thành script trong `src/daas/` và viết test** (phân loại EOA, thời điểm tạo profit-sharing contract, làm giàu `accounts.csv`). Sửa `_is_cacheable` để cache kết quả `getcontractcreation` khi cả lô là EOA (`result = None`).
5. **Dựng 3 View cấp tài khoản** từ cùng tập giao dịch trước t\*: View 2 (chế độ tài khoản của `build_sequences.py`), View 1 (đặc trưng tài khoản theo đề cương), View 3 (ego-graph 1-hop, sau đó 2-hop lấy mẫu).