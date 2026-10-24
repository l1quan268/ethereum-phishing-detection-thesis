<!-- File: README.md -->
# Ethereum Phishing Contract Detection under Incomplete Labels & Temporal Shifts

> **Đề tài Khóa Luận Tốt Nghiệp:** Learning Unified Graph Representations for Ethereum Phishing Detection under Incomplete Labels and Temporal Shifts  
> **Nhóm thực hiện:** Hai sinh viên cùng nghiên cứu & phát triển (Pair Research & Engineering)  
> **Repository GitHub:** [https://github.com/l1quan268/ethereum-phishing-detection-thesis.git](https://github.com/l1quan268/ethereum-phishing-detection-thesis.git)  
> **Tập dữ liệu gốc tham chiếu:** ACM SIGMETRICS 2025 ([DOI: 10.1145/3727138](https://doi.org/10.1145/3727138)); DaaS dataset, ACM IMC 2025 ([DOI: 10.1145/3730567.3764476](https://doi.org/10.1145/3730567.3764476))  

> ℹ️ **Trạng thái hướng nghiên cứu (24/10/2026):** Pilot 20 ban đầu làm ở **cấp hợp đồng** (SIGMETRICS 2025). Thử nghiệm View 2 cho thấy chuỗi giao dịch của hợp đồng phishing quá ngắn (mục 5.1), nên nhóm đang chuyển sang **cấp tài khoản** đúng như đề cương, dùng nhãn tài khoản của **DaaS dataset (IMC 2025)**. Đã thu xong lịch sử giao dịch của 6.141 tài khoản positive (mục 5.2, chi tiết tại [`docs/ACCOUNT_LEVEL_DAAS_VI.md`](docs/ACCOUNT_LEVEL_DAAS_VI.md)). Một số quyết định phương pháp còn chờ chốt.

---

## 1. Giới Thiệu Đề Tài & Phạm Vi Nghiên Cứu

Dự án tập trung giải quyết bài toán phát hiện hợp đồng thông minh lừa đảo (**phishing smart contracts**) trên mạng Ethereum Mainnet trong các điều kiện thực tế khắc nghiệt:

1. **Nhãn không đầy đủ (Incomplete Labels / Positive-Unlabeled Learning):**  
   Trên blockchain, chỉ có một tập nhỏ hợp đồng được xác minh và gắn cờ lừa đảo (`Positive`). Hàng triệu hợp đồng còn lại chưa bị báo cáo không thể xem là lành tính (`benign`), mà phải được mô hình hóa chính xác là chưa gán nhãn (`Unlabeled`). Mô hình được huấn luyện bằng các kỹ thuật **PU Learning** (như Elkan-Noto, Non-negative PU, Bagging PU).
2. **Dịch chuyển thời gian & Biến đổi chiến thuật (Temporal Shifts & Concept Drift):**  
   Kẻ tấn công liên tục đổi mới phương thức lừa đảo (từ hợp đồng đơn giản sang triển khai qua địa chỉ ảo CREATE2, vanity deployers, hàm dẫn dụ `claim()`, permit signature spoofing). Mô hình cần có khả năng chống suy giảm hiệu năng khi đánh giá trên các giai đoạn thời gian tương lai.
3. **Chống rò rỉ thời gian (Point-in-Time Temporal Invariant):**  
   Mọi đặc trưng chỉ được trích xuất từ giao dịch xảy ra trước mốc $T_{\text{cutoff}}$. Hai View hiện dùng hai cách đặt mốc bắt đầu:
   - **View 1** (cửa sổ sau tạo lập; giao dịch trước khi triển khai được tách riêng vào `view1_precreation_audit_pilot.csv`):  
     $$T_{\text{creation}} \le T_{\text{tx}} < T_{\text{cutoff}} = T_{\text{creation}} + 7\text{ ngày}$$
   - **View 2** (giữ cả giao dịch gửi tới địa chỉ CREATE2 *trước* khi hợp đồng được tạo; áp dụng như nhau cho P và U):  
     $$T_{\text{obs\_start}} = \min(T_{\text{creation}},\ T_{\text{first\_event}}) \le T_{\text{tx}} < T_{\text{cutoff}} = T_{\text{obs\_start}} + 7\text{ ngày}$$  

   Mọi giao dịch từ $T_{\text{cutoff}}$ trở đi đều bị loại để chống rò rỉ dữ liệu (data leakage).
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
│   │   ├── suspicious_keywords.log       # 35 từ khóa hàm lừa đảo phổ biến
│   │   └── daas/                         # Clone repo blocksecteam/DaaS_dataset (IMC 2025), không commit
│   │       ├── operator_accounts.log     # 56 tài khoản operator
│   │       ├── affiliate_accounts.log    # 6.087 tài khoản affiliate
│   │       ├── profit_sharing_contracts.log    # 1.910 hợp đồng chia lợi nhuận
│   │       └── profit_sharing_transactions.log # 87.077 giao dịch chia lợi nhuận
│   ├── cache/                            # Bộ đệm JSON thô từ Etherscan API V2 (được ignore trên Git)
│   │   └── view2/                        # Cache dùng chung cho View 2 và DaaS, khóa theo hash toàn bộ tham số
│   ├── interim/                          # Đầu ra trung gian (được ignore trên Git)
│   │   ├── view2/                        # Giai đoạn A View 2: creation.parquet, events.parquet, collection_report.csv
│   │   ├── view2_pilot/                  # Dữ liệu pilot cũ đổi sang schema giai đoạn A (adapt_pilot)
│   │   ├── daas_contract_creation.csv    # Thời điểm tạo 1.910 profit-sharing contract
│   │   ├── daas_account_types.csv        # Phân loại EOA / EOA-7702 / hợp đồng của 6.143 tài khoản DaaS
│   │   └── daas_accounts/                # Lịch sử giao dịch 6.141 EOA DaaS: events.parquet, accounts.csv, accounts_enriched.csv
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
│   │   ├── view2/                        # Temporal Transaction Sequences (đầu ra giai đoạn B, không commit)
│   │   │   ├── view2_sequences.npz       # X_num [N,L,14], X_dir [N,L], X_method [N,L], mask [N,L], address
│   │   │   ├── view2_metadata.csv        # Nhãn, split, mốc obs_start/cutoff, độ dài chuỗi
│   │   │   ├── view2_spec.json           # Tên đặc trưng, từ vựng, tham số chuẩn hóa
│   │   │   └── view2_report.md           # Thống kê độ dài chuỗi theo nhãn & tiêu chí dừng
│   │   ├── view2_pilot/                  # Như view2/ nhưng dựng offline từ data/interim/view2_pilot
│   │   └── view3/                        # (Đang phát triển) Multi-relational Ego-Graph
│   └── full/                             # Dữ liệu diện rộng thu thập sau này (400+ địa chỉ)
│
├── docs/                                 # Tài liệu kỹ thuật, kiến trúc & báo cáo chuyên sâu
│   ├── pipeline_view1_latest.pdf         # Sơ đồ kiến trúc vector PDF độ phân giải cao của View 1
│   ├── VIEW1_PIPELINE_VI.md              # Tài liệu trực quan giải thích pipeline View 1 cho seminar
│   ├── ACCOUNT_LEVEL_DAAS_VI.md          # Chuyển sang cấp tài khoản với DaaS: dữ liệu, kết quả, quyết định chờ chốt
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
│   ├── sample_unlabeled.py               # Module lấy mẫu Unlabeled đối chứng & lọc Cutoff
│   ├── view2/                            # Pipeline View 2 (chuỗi giao dịch point-in-time)
│   │   ├── __init__.py                   # Khai báo package
│   │   ├── etherscan_client.py           # Client Etherscan V2: cache theo tham số, retry, tự chia đôi khoảng khối
│   │   ├── check_client.py               # Thử nhanh client với 1 hợp đồng pilot đã biết đáp án
│   │   ├── collect_events.py             # Giai đoạn A: địa chỉ -> creation.parquet + events.parquet (gọi API)
│   │   ├── build_sequences.py            # Giai đoạn B: sự kiện -> tensor chuỗi (không gọi API)
│   │   └── adapt_pilot.py                # Đổi dữ liệu pilot cũ sang schema giai đoạn A (chạy offline)
│   └── daas/                             # Dữ liệu cấp tài khoản từ DaaS dataset
│       ├── __init__.py                   # Khai báo package
│       └── collect_account_events.py     # Thu lịch sử giao dịch tài khoản DaaS & tính evidence_time
│
└── tests/                                # Bộ kiểm thử tự động toàn diện
    ├── test_cache_resume.py              # Kiểm thử bộ đệm cache và tính năng khôi phục
    ├── test_data_integrity.py            # Kiểm thử tính toàn vẹn dữ liệu, schema và mốc cutoff
    ├── test_view1.py                     # Kiểm thử 12 tiêu chí khoa học & ngữ nghĩa EVM của View 1
    └── test_view2_pipeline.py            # 12 test bất biến của pipeline View 2
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

Dự án tích hợp bộ kiểm thử tự động gồm **32 test functions** do `pytest` thu thập:
- `tests/test_data_integrity.py`: 6 tests (xác thực toàn vẹn schema, dữ liệu Pilot 20, mốc cutoff và manifest).
- `tests/test_view1.py`: 11 test functions (kiểm tra 12 tiêu chí khoa học của View 1; trong đó Tiêu chí 1 về số dòng và Tiêu chí 2 về tính duy nhất được gộp chung trong hàm `test_1_and_2_row_count_and_uniqueness`).
- `tests/test_cache_resume.py`: 3 tests (kiểm tra cơ chế nạp cache JSON và chặn gọi mạng).
- `tests/test_view2_pipeline.py`: 12 tests (cửa sổ quan sát, thứ tự giao dịch, khử trùng lặp, chia split, chuẩn hóa chỉ fit trên train, nhãn không lọt vào tensor, chính sách `method_id`, client chia đôi khoảng khối & cache). Chỉ chạy riêng: `python -m pytest tests/test_view2_pipeline.py -q`.

```powershell
# Chạy toàn bộ test bằng pytest:
pytest -v

# Hoặc chạy trực tiếp qua python:
python -m pytest -v
```

**Kết quả thực thi:**
- **Trên môi trường clone sạch mới tải về:** `16 passed, 4 skipped` (16 tests cốt lõi cho View 1 và Pilot 20 vượt qua 100%; 4 tests về cache Etherscan và dataset gốc tự động skip an toàn với thông báo rõ ràng).
- **Trên môi trường local đầy đủ (đã có cache & data/raw):** `20 passed in ~1.8s`.
- **Sau khi thêm View 2 (đo ngày 23/10/2026, Windows, Python 3.14, đã tải `data/raw`):** `1 failed, 28 passed, 3 skipped`. Test lỗi là `test_data_integrity.py::test_migration_manifest`: kích thước `data/raw/phishing_contracts.log` tải từ GitHub (1.619.121 B) khác manifest (1.656.774 B). Lỗi này có từ trước View 2; nguyên nhân nhiều khả năng là khác kiểu xuống dòng (LF/CRLF), **chưa kiểm chứng**.

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

## 5.1 Tái Lập View 2: Chuỗi Giao Dịch Point-in-Time

Mọi lệnh chạy ở **thư mục gốc repo**, sau khi đã kích hoạt `.venv`. View 2 có hai giai đoạn:

| Giai đoạn | Script | Đầu vào | Đầu ra | Gọi API |
|---|---|---|---|:---:|
| **A** | `src/view2/collect_events.py` | CSV có cột `address`; `data/raw/phishing_transactions.log` (chỉ để tạo cờ kiểm tra) | `data/interim/view2/creation.parquet`, `events.parquet`, `collection_report.csv` | Có |
| **B** | `src/view2/build_sequences.py` | Đầu ra giai đoạn A; CSV nhãn (`address`, `label_status`) | `data/processed/view2/view2_sequences.npz`, `view2_metadata.csv`, `view2_spec.json`, `view2_report.md` | Không |

### Chạy offline trên pilot (không cần API key)

```powershell
python -m src.view2.adapt_pilot
python -m src.view2.build_sequences --in-dir data/interim/view2_pilot --labels data/pilot/combined/pilot_20_addresses.csv --out-dir data/processed/view2_pilot
```

Dữ liệu pilot cũ không có `transactionIndex` và `traceId`, nên luồng này **chỉ để kiểm tra pipeline**, không dùng để đánh giá.

### Chạy với dữ liệu thật (cần `ETHERSCAN_API_KEY` trong `.env`)

```powershell
python -m src.view2.check_client          # thử client; lần chạy thứ 2 phải đọc hoàn toàn từ cache
python -m src.view2.collect_events --addresses data/pilot/combined/pilot_20_addresses.csv --sources normal,internal,erc20
python -m src.view2.build_sequences --labels data/pilot/combined/pilot_20_addresses.csv --t1 <ISO UTC> --t2 <ISO UTC>
python -m src.view2.build_sequences --labels data/pilot/combined/pilot_20_addresses.csv --t1 <ISO UTC> --t2 <ISO UTC> --method-policy drop --out-dir data/processed/view2_drop
```

Không truyền `--t1/--t2` thì mọi mẫu có `split = all`, chuẩn hóa fit trên toàn bộ dữ liệu, và kết quả chỉ dùng để kiểm tra.

### Quy tắc thiết kế chính

- **Cửa sổ:** $T_{\text{obs\_start}} = \min(T_{\text{creation}}, T_{\text{first\_event}})$, $T_{\text{cutoff}} = T_{\text{obs\_start}} + 7$ ngày. Giai đoạn A thu thập khoảng khối `[0, block(T_creation + 7 ngày)]`.
- **Nguồn:** luôn lấy `normal` + `internal`. Hợp đồng tạo qua factory bằng `create2` chỉ xuất hiện trong `internal`; nếu bỏ nguồn này, 9/10 P của pilot có chuỗi rỗng. Token (`erc20`, `erc721`) là tùy chọn.
- **Phần tử chuỗi:** một phần tử là một giao dịch (`tx_hash`); sự kiện internal/token của cùng giao dịch được gộp thành đặc trưng. Không cộng ETH với số lượng token.
- **Thứ tự:** `block_number → transactionIndex`. Nếu thiếu index trong khối có hơn 1 giao dịch thì gán `order_uncertain = 1`.
- **Đặc trưng (14 mỗi phần tử):**
  - liên tục (log1p rồi z-score): `log_eth_in`, `log_eth_out`, `log_dt`, `log_age`, `log_gas`, `log_n_internal`, `log_n_tok_in`, `log_n_tok_out`, `log_n_tok_distinct`;
  - nhị phân: `is_error`, `is_pre_deploy`, `dt_mask`, `gas_known`, `order_uncertain`;
  - mảng riêng `X_dir` (hướng) và `X_method` (selector).
- **Chống rò rỉ:**
  - z-score và từ vựng `method_id` chỉ fit trên split `train`;
  - nhãn chỉ nằm trong `view2_metadata.csv`, không nằm trong tensor;
  - không dùng loại đối tác (EOA hay hợp đồng), vì API trả trạng thái hiện tại;
  - `in_sigmetrics_tx_log` chỉ để kiểm tra.
- **Chia theo thời gian:**
  - `train`: `cutoff ≤ T1`;
  - `val`: `obs_start ≥ T1` và `cutoff ≤ T2`;
  - `test`: `obs_start ≥ T2`;
  - `gap`: cửa sổ vắt qua T1 hoặc T2, bị loại.
- **Cắt chuỗi:** giữ L = 256 giao dịch gần cutoff nhất, đệm bên trái.
- **Ablation `method_id`:** `--method-policy keep | drop | mask_keywords`. Positive SIGMETRICS được phát hiện nhờ tên hàm khớp từ khóa, nên ablation `drop` là bắt buộc.

### Kết quả pilot 20 và tiêu chí dừng

Giai đoạn A trên 20 địa chỉ pilot: `collection_report.csv` có 20/20 `ok`, không có `saturated_ranges`. Độ dài chuỗi theo `view2_report.md`:

| label_status | n | min | median | mean | max | có sự kiện trước deploy |
|---|---|---|---|---|---|---|
| positive | 10 | 1 | 1.0 | 1.4 | 2 | 4 |
| unlabeled | 10 | 1 | 2.0 | 221.5 | 2135 | 0 |

> ⚠️ **Tiêu chí dừng đang bị kích hoạt:** trung vị độ dài chuỗi của positive = 1 ≤ 3. Ở cấp hợp đồng, chuỗi của P quá ngắn để mô hình hóa theo thời gian, và chênh lệch độ dài P/U là nguồn học đường tắt. Cần quyết định trước khi mở rộng:
> - giữ View 2 ở cấp hợp đồng;
> - hoặc chuyển tín hiệu (`n_pre_deploy`, `pre_deploy_lead_s`) thành đặc trưng tĩnh cho View 1;
> - hoặc chuyển bài toán sang cấp tài khoản.
>
> Kết luận này dựa trên 10 P, cần kiểm tra lại trên mẫu lớn hơn.

### Hạn chế đã biết

- `tokentx` không có `logIndex`, nên khử trùng lặp theo (tx, token, from, to, value) có thể gộp nhầm hai lần chuyển giống hệt nhau.
- 7/10 P pilot được tạo từ chỉ 2 factory, nên có rủi ro rò rỉ theo nhóm giữa train và test.
- Không có thời điểm gắn nhãn, nên chỉ chặn được rò rỉ ở phía đặc trưng.
- Giả định SCAR gần như chắc chắn bị vi phạm.

---

## 5.2 Chuyển Sang Cấp Tài Khoản Với DaaS Dataset (Đang Thực Hiện)

Đề cương yêu cầu phân loại ở **cấp tài khoản**. SIGMETRICS chỉ gán nhãn hợp đồng, nên nhóm dùng thêm **DaaS dataset** (IMC 2025, cùng nhóm tác giả BlockSec): 56 operator + 6.087 affiliate, tức các tài khoản tham gia chia lợi nhuận từ drainer. Tác giả kiểm tra thủ công 39.037 giao dịch (44,8%) và *"No false positives were identified"* (§5.2 của bài báo). Chi tiết toàn bộ bước làm, số liệu và đoạn mã tái lập: [`docs/ACCOUNT_LEVEL_DAAS_VI.md`](docs/ACCOUNT_LEVEL_DAAS_VI.md).

**Tải dữ liệu DaaS** (repo không có LICENSE nên không commit, nằm trong `data/raw/` đã được ignore):

```powershell
git clone https://github.com/blocksecteam/DaaS_dataset data/raw/daas
```

**Thu lịch sử giao dịch tài khoản và tính `evidence_time`** (cần `.env`; trước đó phải có `data/interim/daas_account_types.csv`, xem tài liệu):

```powershell
python -m src.daas.collect_account_events --sample 30   # chạy thử
python -m src.daas.collect_account_events --sample 0    # toàn bộ 6.141 EOA (khoảng 19 nghìn lượt gọi)
```

**Kết quả chính đến 24/10/2026:**

| Hạng mục | Kết quả |
|---|---|
| Giai đoạn profit-sharing contract | 07/02/2023 – 01/04/2025 (bài báo ghi 01/03/2023 – 01/04/2025) |
| Loại tài khoản | 6.141 EOA (5.931 EOA thường + 210 EOA có mã ủy quyền EIP-7702), 2 hợp đồng (loại khỏi P) |
| Chồng lấn với SIGMETRICS | 1.209/1.910 profit-sharing contract; 42.242/87.077 giao dịch |
| Kiểm chứng suy nhãn trên pilot | 6/6 địa chỉ suy ra từ dòng tiền khớp vai trò trong DaaS |
| `evidence_time` (lần đầu tham gia chia lợi nhuận) | Tìm được 6.141/6.141; nguồn: internal 3.146, erc20 2.985, normal 10 |
| Số sự kiện mỗi tài khoản | Trung vị 55, P90 419, tối đa 39.833 |
| Ví "mới tạo để lừa" | 4.172 tài khoản (68%) có `first_seen` cách `evidence_time` dưới 1 ngày |
| Giao dịch **trước** `evidence_time` | 0 giao dịch: 3.225 (52,5%); ≥ 3 giao dịch: 1.910 |

> ⚠️ **Quyết định đang chờ chốt** (xem tài liệu): (1) thời điểm quyết định t\* (đề xuất chính: `evidence_time` + 1 ngày, kèm ablation bỏ giao dịch chia lợi nhuận để tránh mô hình học lại quy tắc gán nhãn); (2) mốc chia theo tháng của t\* (đề xuất: train ≤ 03/2024, val 04–09/2024, test 10/2024–04/2025); (3) cách lấy mẫu và số lượng U; (4) xin GVHD đồng ý cập nhật nguồn nhãn trong đề cương.

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
| **Mở rộng quy mô (Scale-up 400)** | ⏸️ Thay thế | Không tiếp tục ở cấp hợp đồng; quy mô mới là 6.141 tài khoản P từ DaaS (mục 5.2). |
| **View 2: Temporal Sequences (cấp hợp đồng)** | 🧪 Pipeline xong, dừng theo tiêu chí | Pipeline 2 giai đoạn (`src/view2/`) đã chạy trên Pilot 20, 12/12 tests đạt. Tiêu chí dừng bị kích hoạt (trung vị độ dài chuỗi P = 1), là cơ sở chuyển sang cấp tài khoản (mục 5.1). Client và bộ dựng chuỗi được tái sử dụng cho cấp tài khoản. |
| **Dữ liệu cấp tài khoản (DaaS)** | 🔄 Đang làm | Đã thu lịch sử giao dịch và `evidence_time` cho 6.141 EOA (mục 5.2). Còn: chốt t\*, T1/T2; lấy mẫu U; chuyển các bước khảo sát thành script; viết test cho `src/daas/`. |
| **View 1 / View 2 / View 3 cấp tài khoản** | 🔄 Chưa hoàn thành | Dựng lại 3 View từ cùng một tập giao dịch trước t\* của mỗi tài khoản (xem `docs/ACCOUNT_LEVEL_DAAS_VI.md`). |
| **View 3: Multi-relational Ego-Graph**| 🔄 Chưa hoàn thành | Ego-graph 1-hop từ giao dịch trước t\* (không cần gọi thêm API); 2-hop lấy mẫu nếu còn quota. Không dùng nhãn của nút lân cận làm đặc trưng. |
| **Fusion: Đa góc nhìn (Multi-View)** | 🔄 Chưa hoàn thành | Thiết kế cơ chế tích hợp đặc trưng từ 3 View (Early Fusion / Late Fusion / Hierarchical Attention Graph Fusion). |
| **PU Learning Modeling** | 🔄 Chưa hoàn thành | Áp dụng các thuật toán học từ dữ liệu nhãn dương và chưa gán nhãn (Elkan-Noto estimator, Non-negative PU, Bagging PU). |
| **Temporal Shift Evaluation** | 🔄 Chưa hoàn thành | Đánh giá khả năng khái quát hóa qua các mốc thời gian. Dữ liệu DaaS phủ 03/2023 – 04/2025; đề xuất train ≤ 03/2024, val 04–09/2024, test 10/2024–04/2025 (tập test bao trùm thời điểm họ Inferno ngừng hoạt động, 11/2024). |

---

## 9. Trích Dẫn Bài Báo Gốc (Citation)

Nếu sử dụng các tập dữ liệu này trong nghiên cứu học thuật, vui lòng trích dẫn bài báo gốc.

DaaS dataset (nguồn nhãn tài khoản):

```bibtex
@inproceedings{he2025unmasking,
  title={Unmasking the Shadow Economy: A Deep Dive into Drainer-as-a-Service Phishing on Ethereum},
  author={He, Bowen and Hu, Yufeng and Chen, Zhuo and Chen, Yuan and Yu, Ting and Chang, Rui and Wu, Lei and Zhou, Yajin},
  booktitle={Proceedings of the 2025 ACM Internet Measurement Conference},
  pages={430--444},
  year={2025}
}
```

SIGMETRICS 2025 (nguồn nhãn hợp đồng):

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