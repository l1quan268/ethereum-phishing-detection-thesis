# Ethereum Phishing Contract Detection under Incomplete Labels & Temporal Shifts

> **Đề tài Khóa Luận Tốt Nghiệp:** Learning Unified Graph Representations for Ethereum Phishing Detection under Incomplete Labels and Temporal Shifts  
> **Nhóm thực hiện:** Hai sinh viên cùng nghiên cứu & phát triển (Pair Research & Engineering)  
> **Repository GitHub:** [https://github.com/l1quan268/ethereum-phishing-detection-thesis.git](https://github.com/l1quan268/ethereum-phishing-detection-thesis.git)  
> **Tập dữ liệu gốc tham chiếu:** ACM SIGMETRICS 2025 ([DOI: 10.1145/3727138](https://doi.org/10.1145/3727138))  

---

## 1. Giới Thiệu Đề Tài & Phạm Vi Nghiên Cứu

Dự án tập trung giải quyết bài toán phát hiện hợp đồng thông minh lừa đảo (**phishing smart contracts**) trên mạng Ethereum Mainnet trong các điều kiện thực tế khắc nghiệt:

1. **Nhãn không đầy đủ (Incomplete Labels / Positive-Unlabeled Learning):**  
   Trên blockchain, chỉ có một tập nhỏ hợp đồng được xác minh và gắn cờ lừa đảo (`Positive`). Hàng triệu hợp đồng còn lại chưa bị báo cáo không thể xem là lành tính (`benign`), mà phải được mô hình hóa chính xác là chưa gán nhãn (`Unlabeled`). Mô hình được huấn luyện bằng các kỹ thuật **PU Learning** (như Elkan-Noto, Non-negative PU, Bagging PU).
2. **Dịch chuyển thời gian & Biến đổi chiến thuật (Temporal Shifts & Concept Drift):**  
   Kẻ tấn công liên tục đổi mới phương thức lừa đảo (từ hợp đồng đơn giản sang triển khai qua địa chỉ ảo CREATE2, vanity deployers, hàm dẫn dụ `claim()`, permit signature spoofing). Mô hình cần có khả năng chống suy giảm hiệu năng khi đánh giá trên các giai đoạn thời gian tương lai.
3. **Chống rò rỉ thời gian (Point-in-Time Temporal Invariant):**  
   Mọi đặc trưng của hợp đồng chỉ được trích xuất trên các giao dịch xảy ra trong cửa sổ quan sát sau tạo lập:  
   $$T_{\text{creation}} \le T_{\text{tx}} < T_{\text{cutoff}} = T_{\text{creation}} + 7\text{ ngày}$$  
   Mọi giao dịch sau $T_{\text{cutoff}}$ hoặc giao dịch trước khi triển khai đều được cách ly nghiêm ngặt để chống rò rỉ dữ liệu (data leakage).
4. **Biểu diễn đa góc nhìn hợp nhất (Unified Multi-View Representation):**  
   - **View 1:** Đặc trưng thống kê dạng bảng (Tabular / Statistical Features - 32 chiều).  
   - **View 2:** Chuỗi giao dịch theo thời gian (Temporal Transaction Sequences).  
   - **View 3:** Đồ thị con đa quan hệ quanh hợp đồng (Multi-relational Ego-Graph).  

---

## 2. Cây Thư Mục & Vai Trò Từng Thư Mục

```text
ethereum-phishing-detection-thesis/
├── .env                                  # Chứa ETHERSCAN_API_KEY (Bảo mật, KHÔNG commit lên Git)
├── .env.example                          # Mẫu khai báo biến môi trường (an toàn để commit)
├── .gitignore                            # Cấu hình loại trừ cache, virtualenv, secrets
├── PROGRESS.md                           # Bảng theo dõi tiến độ chi tiết các cột mốc
├── README.md                             # Tài liệu tổng quan dự án và cẩm nang vận hành
├── requirements.txt                      # Danh sách Python dependencies phục vụ cài đặt
│
├── configs/                              # Cấu hình pipeline & schema dữ liệu
│   └── label_schema.csv                  # Schema 6 cột chuẩn hóa cho quản lý nhãn PU
│
├── data/                                 # Quản lý dữ liệu phân tầng chặt chẽ
│   ├── raw/                              # Dữ liệu gốc nguyên bản từ paper SIGMETRICS 2025
│   │   ├── phishing_contracts.log        # 37,654 địa chỉ hợp đồng lừa đảo
│   │   ├── phishing_transactions.log     # 211,319 mã băm giao dịch lừa đảo
│   │   └── suspicious_keywords.log       # 35 từ khóa hàm lừa đảo phổ biến
│   ├── cache/                            # Bộ đệm JSON thô từ Etherscan API V2 (được ignore trên Git)
│   ├── pilot/                            # Dữ liệu kiểm thử thực nghiệm quy mô nhỏ (Pilot 20)
│   │   ├── positive/                     # Dữ liệu 10 Positive (CSV địa chỉ + Parquet giao dịch)
│   │   ├── unlabeled/                    # Dữ liệu 10 Unlabeled đối chứng (Matched Block Sampling)
│   │   └── combined/                     # Tập hợp nhất 20 địa chỉ & giao dịch sạch trước Cutoff
│   │       ├── pilot_20_addresses.csv    # 20 địa chỉ kèm mốc T_creation & T_cutoff
│   │       └── pilot_20_transactions_before_cutoff.parquet # 2,965 giao dịch sạch (0 rò rỉ thời gian)
│   ├── processed/                        # Dữ liệu đặc trưng sau trích xuất theo từng View
│   │   ├── view1/                        # Statistical Tabular Features (20 dòng x 32 đặc trưng)
│   │   │   ├── view1_features_pilot.parquet     # Ma trận đặc trưng số học X
│   │   │   ├── view1_features_pilot.csv         # Phiên bản CSV của ma trận đặc trưng
│   │   │   ├── view1_metadata_pilot.parquet     # Bảng metadata cô lập nhãn (PU-Learning)
│   │   │   ├── view1_metadata_pilot.csv         # Phiên bản CSV của metadata
│   │   │   ├── view1_precreation_audit_pilot.csv# Kiểm toán 4 bản ghi tiền triển khai (CREATE2)
│   │   │   └── backup_v1/                       # Bản lưu kết quả kiểm toán ban đầu
│   │   ├── view2/                        # (Đang phát triển) Temporal Transaction Sequences
│   │   └── view3/                        # (Đang phát triển) Multi-relational Ego-Graph
│   └── full/                             # Dữ liệu diện rộng thu thập sau này (400+ địa chỉ)
│
├── docs/                                 # Tài liệu kỹ thuật, kiến trúc & báo cáo chuyên sâu
│   ├── pipeline_view1_latest.pdf         # Sơ đồ kiến trúc vector PDF độ phân giải cao của View 1
│   ├── VIEW1_PIPELINE_VI.md              # Tài liệu trực quan giải thích pipeline View 1 cho seminar
│   ├── view1_feature_spec.md             # Đặc tả toán học 32 đặc trưng View 1 & chuẩn NOT_AVAILABLE
│   ├── three_views_spec.md               # Thiết kế chi tiết kiến trúc và schema 3 View
│   ├── data_collection_plan.md           # Kế hoạch & chi phí thu thập on-chain
│   ├── README_PILOT_VI.md                # Cẩm nang chạy pipeline Pilot 10 Positive ban đầu
│   └── README_NEXT_STEPS_VI.md           # Kế hoạch lấy mẫu 10 Unlabeled đối chứng
│
├── experiments/                          # Lưu trữ checkpoints, mô hình, logs và kết quả thực nghiệm
│
├── reports/                              # Báo cáo kiểm toán dữ liệu và báo cáo khoa học
│   ├── audit/                            # Báo cáo kiểm toán bộ dữ liệu gốc SIGMETRICS 2025
│   ├── pilot/                            # Báo cáo nghiệm thu kết quả Pilot 20 và chất lượng View 1
│   └── migration_manifest.json           # Manifest SHA-256 xác thực toàn vẹn tái cấu trúc thư mục
│
├── src/                                  # Mã nguồn Python chính của dự án
│   ├── __init__.py                       # Khai báo package src
│   ├── build_view1.py                    # Pipeline trích xuất đặc trưng thống kê View 1 (Offline)
│   ├── collect_etherscan.py              # Pipeline thu thập dữ liệu từ Etherscan API V2
│   └── sample_unlabeled.py               # Module lấy mẫu Unlabeled đối chứng & lọc Cutoff
│
└── tests/                                # Bộ kiểm thử tự động toàn diện
    ├── test_cache_resume.py              # Kiểm thử bộ đệm cache và tính năng khôi phục
    ├── test_data_integrity.py            # Kiểm thử tính toàn vẹn dữ liệu, schema và mốc cutoff
    └── test_view1.py                     # Kiểm thử 12 tiêu chí khoa học & ngữ nghĩa EVM của View 1
```

---

## 3. Hướng Dẫn Clone & Thiết Lập Môi Trường (Windows)

Dành cho thành viên thứ hai của nhóm sau khi clone repository:

### 3.1 Clone Repository
Mở **PowerShell** hoặc **Git Bash** và thực hiện:
```powershell
git clone https://github.com/l1quan268/ethereum-phishing-detection-thesis.git
cd ethereum-phishing-detection-thesis
```

### 3.2 Cài đặt Python 3.11 & Khởi tạo Virtual Environment
Dự án được xây dựng và kiểm thử chuẩn hóa trên **Python 3.11**:
1. Đảm bảo máy tính đã cài Python 3.11 (kiểm tra bằng `python --version` hoặc `py -3.11 --version`).
2. Mở PowerShell tại thư mục dự án và tạo môi trường ảo `.venv`:
   ```powershell
   python -m venv .venv
   ```
3. Kích hoạt môi trường ảo trên Windows PowerShell:
   ```powershell
   # Nếu gặp lỗi Execution Policy, cấp quyền chạy script trong phiên hiện tại:
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process

   # Kích hoạt virtualenv:
   .\.venv\Scripts\Activate.ps1
   ```
   *(Khi kích hoạt thành công, đầu dòng lệnh sẽ xuất hiện tiền tố `(.venv)`).*

### 3.3 Cài đặt Dependencies
Cài đặt toàn bộ các thư viện cần thiết thông qua `requirements.txt`:
```powershell
pip install --upgrade pip
pip install -r requirements.txt
```

---

---

## 4. Chạy Toàn Bộ Kiểm Thử (Unit & Integration Tests)

Dự án tích hợp bộ kiểm thử tự động gồm **20 test functions** do `pytest` thu thập (kiểm tra đầy đủ 21 tiêu chí khoa học & kỹ thuật):
- `tests/test_data_integrity.py`: 6 tests (xác thực toàn vẹn schema, dữ liệu Pilot 20, mốc cutoff và manifest).
- `tests/test_view1.py`: 11 test functions (kiểm tra 12 tiêu chí khoa học của View 1; trong đó Tiêu chí 1 về số dòng và Tiêu chí 2 về tính duy nhất được gộp chung trong hàm `test_1_and_2_row_count_and_uniqueness`).
- `tests/test_cache_resume.py`: 3 tests (kiểm tra cơ chế nạp cache JSON và chặn gọi mạng).

```powershell
# Chạy toàn bộ test bằng pytest:
pytest -v

# Hoặc chạy trực tiếp qua python:
python -m pytest -v
```

**Kết quả thực thi:**
- **Trên môi trường clone sạch mới tải về:** `16 passed, 4 skipped` (16 tests cốt lõi cho View 1 và Pilot 20 vượt qua 100%; 4 tests về cache Etherscan và dataset gốc tự động skip an toàn với thông báo rõ ràng).
- **Trên môi trường local đầy đủ (đã có cache & data/raw):** `20 passed in ~1.8s`.

---

## 4.1 Hướng Dẫn Tải Bộ Dữ Liệu Gốc SIGMETRICS 2025 (Tùy Chọn)

> ℹ️ **Lưu ý về Bản quyền & Tái phân phối:**  
> Repository nguồn của BlockSec ([blocksecteam/phishing_contract_sigmetrics25](https://github.com/blocksecteam/phishing_contract_sigmetrics25)) không đính kèm giấy phép mã nguồn mở (Open Source License) cho phép tái phân phối tự do. Để tuân thủ nghiêm ngặt quyền tác giả và tiêu chuẩn Research Software Engineering, dự án này **không commit ba tệp log gốc** lên GitHub Public. Thay vào đó, bạn có thể dễ dàng tải trực tiếp từ nguồn chính thức của tác giả:

Nếu bạn muốn chạy bài kiểm thử đối chiếu toàn diện `test_raw_dataset_integrity` (37,654 hợp đồng và 211,319 giao dịch gốc):

1. Tạo thư mục `data/raw` (nếu chưa có):
   ```powershell
   New-Item -ItemType Directory -Path "data\raw" -Force
   ```
2. Tải 3 tệp dữ liệu gốc từ repository của BlockSec và đặt vào `data/raw/`:
   ```powershell
   # Tải phishing_contracts.log (1.65 MB)
   Invoke-WebRequest -Uri "https://raw.githubusercontent.com/blocksecteam/phishing_contract_sigmetrics25/main/phishing_contracts.log" -OutFile "data\raw\phishing_contracts.log"

   # Tải phishing_transactions.log (14.36 MB)
   Invoke-WebRequest -Uri "https://raw.githubusercontent.com/blocksecteam/phishing_contract_sigmetrics25/main/phishing_transactions.log" -OutFile "data\raw\phishing_transactions.log"

   # Tải suspicious_keywords.log (282 B)
   Invoke-WebRequest -Uri "https://raw.githubusercontent.com/blocksecteam/phishing_contract_sigmetrics25/main/suspicious_keywords.log" -OutFile "data\raw\suspicious_keywords.log"
   ```
3. Sau khi tải, chạy lại `pytest -v` sẽ đạt kết quả tối đa **20/20 passed** (nếu có thêm cả thư mục `data/cache/`).
4. **Các tests cần bộ dữ liệu này:**
   - `tests/test_data_integrity.py::test_raw_dataset_integrity`: Kiểm tra số lượng và tính duy nhất của 37,654 hợp đồng và 211,319 giao dịch gốc.
   - `tests/test_view1.py::test_9_immutability_of_raw_and_pilot_sources`: Kiểm tra tính bất biến của dữ liệu gốc so với dữ liệu pilot.
   *(Nếu chưa tải, 2 test trên sẽ tự động bỏ qua phần kiểm tra file gốc mà không gây lỗi build).*

---

## 5. Tái Lập View 1 Bằng Dữ Liệu Pilot 20 (Offline 100%, Không Cần API Key)

Thành viên thứ hai **hoàn toàn không cần API key Etherscan hay kết nối Internet** để tái lập lại toàn bộ ma trận đặc trưng View 1:

```powershell
python src/build_view1.py
```

### Luồng xử lý dữ liệu offline:
- **Dữ liệu đầu vào:**
  - `data/pilot/combined/pilot_20_addresses.csv`: Danh sách 20 hợp đồng (10 Positive + 10 Unlabeled) cùng mốc $T_{\text{creation}}$ và $T_{\text{cutoff}}$.
  - `data/pilot/combined/pilot_20_transactions_before_cutoff.parquet`: 2,965 giao dịch sạch đã được lọc bỏ rò rỉ thời gian.
- **Dữ liệu đầu ra được tạo mới:**
  - `data/processed/view1/view1_features_pilot.parquet` & `.csv`: Ma trận đặc trưng số học thuần túy gồm **20 dòng × 32 đặc trưng**.
  - `data/processed/view1/view1_metadata_pilot.parquet` & `.csv`: Bảng metadata cô lập nhãn và nguồn nhãn.
  - `data/processed/view1/view1_precreation_audit_pilot.csv`: Danh sách 4 giao dịch gửi vào địa chỉ trước thời điểm triển khai hợp đồng (CREATE2 counterfactual).

---

## 6. Xem Tài Liệu Kiến Trúc & Sơ Đồ Pipeline

Dự án cung cấp tài liệu giải thích chi tiết cơ chế hoạt động phục vụ báo cáo tiến độ và seminar:

1. **Sơ đồ kiến trúc vector độ phân giải cao:**
   - Mở tệp: [`docs/pipeline_view1_latest.pdf`](docs/pipeline_view1_latest.pdf)
   - Chứa sơ đồ 5 tầng xử lý từ Ethereum on-chain đến ma trận đặc trưng View 1, thiết kế chuẩn vector để in ấn hoặc chèn vào slide báo cáo.
2. **Tài liệu hướng dẫn trực quan cho Seminar:**
   - Mở tệp: [`docs/VIEW1_PIPELINE_VI.md`](docs/VIEW1_PIPELINE_VI.md)
   - Giải thích chi tiết cơ chế lọc Point-in-Time, xử lý CREATE2 tiền triển khai, lọc Revert transactions, khử trùng lặp Gas, phân tách đơn vị tài sản và nguyên tắc cô lập nhãn PU.
3. **Đặc tả toán học 32 đặc trưng View 1:**
   - Mở tệp: [`docs/view1_feature_spec.md`](docs/view1_feature_spec.md)
   - Công thức tính toán chi tiết cho từng nhóm đặc trưng: Volume, Network Structure, Temporal Activity, Asset Diversity.

---

## 7. Cấu Hình Thu Thập Dữ Liệu Mới (Khi Cần Dùng API)

Nếu muốn thu thập thêm dữ liệu on-chain cho các địa chỉ mới ngoài tập Pilot 20:

1. Sao chép tệp cấu hình mẫu `.env.example` thành `.env`:
   ```powershell
   Copy-Item .env.example .env
   ```
2. Đăng ký tài khoản và lấy Etherscan API Key miễn phí tại: [https://etherscan.io/myapikey](https://etherscan.io/myapikey).
3. Mở tệp `.env` và điền key:
   ```env
   ETHERSCAN_API_KEY=dien_api_key_cua_ban_vao_day
   ```
4. Chạy pipeline thu thập (có cơ chế cache tự động và rate limit 2 req/s an toàn cho gói miễn phí):
   ```powershell
   python src/collect_etherscan.py --limit 10 --seed 42 --rate-limit 2.0
   ```
   > ⚠️ **LƯU Ý BẢO MẬT:** Tệp `.env` đã được cấu hình trong `.gitignore`. Tuyệt đối không xóa `.gitignore` hoặc commit tệp `.env` lên GitHub.

---

## 8. Lộ Trình Nghiên Cứu & Các Phần Chưa Hoàn Thành (Roadmap)

Sau khi nghiệm thu thành công cột mốc Pilot View 1, hai thành viên sẽ tiếp tục phát triển các hạng mục tiếp theo của khóa luận:

| Hạng mục | Trạng thái | Mô tả & Nhiệm vụ tiếp theo |
| :--- | :---: | :--- |
| **View 1: Statistical Features** | ✅ Hoàn thành | Đã hoàn thành và kiểm toán trên Pilot 20, đạt 20/20 tests. |
| **Mở rộng quy mô (Scale-up 400)** | ⏸️ Sắp làm | Thu thập dữ liệu on-chain cho 200 Positive + 200 Unlabeled. |
| **View 2: Temporal Sequences** | 🔄 Chưa hoàn thành | Trích xuất chuỗi thời gian các giao dịch (tx type, delta time, value, method) làm đầu vào cho mô hình Recurrent / Transformer (LSTM, GRU, Temporal GNN). |
| **View 3: Multi-relational Ego-Graph**| 🔄 Chưa hoàn thành | Xây dựng đồ thị con quanh hợp đồng (nút: External EOA, Contract, Token; cạnh: Call, Create, Transfer ETH, Transfer ERC-20). |
| **Fusion: Đa góc nhìn (Multi-View)** | 🔄 Chưa hoàn thành | Thiết kế cơ chế tích hợp đặc trưng từ 3 View (Early Fusion / Late Fusion / Hierarchical Attention Graph Fusion). |
| **PU Learning Modeling** | 🔄 Chưa hoàn thành | Áp dụng các thuật toán học từ dữ liệu nhãn dương và chưa gán nhãn (Elkan-Noto estimator, Non-negative PU, Bagging PU). |
| **Temporal Shift Evaluation** | 🔄 Chưa hoàn thành | Đánh giá khả năng khái quát hóa và độ bền vững của mô hình qua các mốc thời gian khác nhau (Train: 2022-2023, Test: 2024-2025). |

---

## 9. Trích Dẫn Bài Báo Gốc (Citation)

Nếu sử dụng tập dữ liệu này trong các nghiên cứu học thuật, vui lòng trích dẫn bài báo gốc:

```bibtex
@article{phishing_contracts,
  title={Phishing Tactics Are Evolving: An Empirical Study of Phishing Contracts on Ethereum},
  author={He, Bowen and Hu, Xiaohui and Hu, Yufeng and Yu, Ting and Chang, Rui and Wu, Lei and Zhou, Yajin},
  journal={Proceedings of the ACM on Measurement and Analysis of Computing Systems},
  volume={9},
  number={2},
  pages={1--24},
  year={2025},
  publisher={ACM New York, NY, USA}
}
```
