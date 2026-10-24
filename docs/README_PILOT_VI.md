<!-- File: docs/README_PILOT_VI.md -->
# Hướng Dẫn Vận Hành Pipeline Thu Thập Dữ Liệu On-Chain (Etherscan API V2)

> **Dự án:** Learning Unified Graph Representations for Ethereum Phishing Detection under Incomplete Labels and Temporal Shifts  
> **Ngôn ngữ:** Python 3.x (Môi trường ảo `.venv`)  
> **Hệ điều hành:** Windows (PowerShell)  

---

## 1. Cấu Trúc Thư Mục Chuẩn Hóa

```text
phishing_contract_sigmetrics25/
├── .env                                  # Chứa ETHERSCAN_API_KEY (KHÔNG commit file này)
├── .gitignore                            # Cấu hình bỏ qua .env, .venv, data/cache/
├── .venv/                                # Môi trường ảo Python đã cài sẵn thư viện
├── configs/
│   └── label_schema.csv                  # Đặc tả schema 6 cột chuẩn cho nhãn
├── data/
│   ├── raw/                              # Dữ liệu gốc SIGMETRICS 2025
│   │   ├── phishing_contracts.log        # 37,654 địa chỉ hợp đồng lừa đảo
│   │   ├── phishing_transactions.log     # 211,319 mã băm giao dịch
│   │   └── suspicious_keywords.log       # 35 từ khóa hàm lừa đảo
│   ├── cache/                            # Bộ đệm JSON thô theo từng địa chỉ (Resume)
│   │   └── <address>/
│   │       ├── getcontractcreation_page1.json
│   │       ├── txlist_page1.json
│   │       ├── txlistinternal_page1.json
│   │       ├── tokentx_page1.json
│   │       └── tokennfttx_page1.json
│   ├── pilot/
│   │   ├── positive/                     # Dữ liệu pilot 10 Positive hiện tại
│   │   │   ├── pilot_addresses.csv
│   │   │   └── pilot_transactions.parquet
│   │   ├── unlabeled/                    # Dữ liệu pilot 10 Unlabeled (sắp thực hiện)
│   │   └── combined/                     # Dữ liệu tổng hợp 20 địa chỉ
│   ├── processed/                        # Dữ liệu đặc trưng 3 View
│   │   ├── view1/
│   │   ├── view2/
│   │   └── view3/
│   └── full/                             # Dữ liệu thu thập diện rộng sau này
├── docs/                                 # Tài liệu kiến trúc và hướng dẫn
│   ├── three_views_spec.md
│   ├── data_collection_plan.md
│   ├── README_PILOT_VI.md
│   └── README_NEXT_STEPS_VI.md
├── reports/                              # Báo cáo kiểm toán, pilot, thí nghiệm
│   ├── audit/
│   │   └── dataset_audit.md
│   ├── pilot/
│   │   ├── bao_cao_pilot_vi.md
│   │   ├── pilot_timestamp_report.csv
│   │   └── api_collection_log.csv
│   ├── experiments/
│   └── migration_manifest.json           # Manifest SHA-256 xác thực di chuyển file
├── src/                                  # Mã nguồn Python dự án
│   ├── __init__.py
│   └── collect_etherscan.py              # Script thu thập dữ liệu Etherscan API V2
├── tests/                                # Bộ kiểm thử tự động
│   ├── test_data_integrity.py
│   └── test_cache_resume.py
├── PROGRESS.md                           # Bảng theo dõi tiến độ tổng thể
└── README.md                             # Tổng quan dự án và tài liệu nghiên cứu
```

---

## 2. Chuẩn Bị Môi Trường

Đảm bảo file `.env` đã tồn tại ở thư mục gốc của workspace và chứa khóa API:

```bash
ETHERSCAN_API_KEY=YOUR_ETHERSCAN_API_KEY_HERE
```

*Lưu ý: Script hoàn toàn tự động đọc khóa từ `.env` bằng `pathlib.Path` và bảo đảm không hiển thị hay in khóa ra màn hình hoặc log.*

---

## 3. Lệnh PowerShell Chạy Thử Nghiệm (Pilot)

Mở **PowerShell** tại thư mục gốc của dự án:

### 3.1 Chạy thử nghiệm 10 địa chỉ Positive (Khuyến nghị mặc định)
Lấy ngẫu nhiên 10 địa chỉ với random seed = 42, tốc độ tối đa 2 request/giây:

```powershell
& .\.venv\Scripts\python.exe src/collect_etherscan.py --limit 10 --seed 42 --rate-limit 2.0
```

### 3.2 Tiếp tục thu thập khi bị gián đoạn (Resume)
Script tự động kích hoạt cơ chế đệm cache (`data/cache/`). Nếu pipeline bị ngắt (mất mạng, tắt máy, ngắt tiến trình), chỉ cần gõ lại lệnh trên:
- Các endpoint đã tải thành công trước đó sẽ được đọc tức thì từ ổ cứng (thời gian xử lý `< 0.01s`).
- Pipeline chỉ gửi yêu cầu mạng cho các phần dữ liệu chưa tải xong.

```powershell
& .\.venv\Scripts\python.exe src/collect_etherscan.py --limit 10 --seed 42
```

### 3.3 Tải lại mới toàn bộ (Bỏ qua cache)
Khi cần cập nhật dữ liệu mới nhất trên chuỗi và bỏ qua cache cũ:

```powershell
& .\.venv\Scripts\python.exe src/collect_etherscan.py --limit 10 --seed 42 --force-refresh
```

### 3.4 Tùy chỉnh tham số dòng lệnh
| Tham số | Ý nghĩa | Mặc định | Ví dụ |
| :--- | :--- | :---: | :--- |
| `--limit` | Số lượng địa chỉ hợp đồng cần thu thập | `10` | `--limit 50` |
| `--seed` | Random seed cố định để tái lập kết quả | `42` | `--seed 123` |
| `--rate-limit` | Tốc độ tối đa (requests/giây) | `2.0` | `--rate-limit 1.5` |
| `--cache-dir` | Thư mục lưu JSON cache | `data/cache` | `--cache-dir data/cache` |
| `--output-dir` | Thư mục xuất dataset CSV và Parquet | `data/pilot/positive` | `--output-dir data/pilot/positive` |
| `--report-dir` | Thư mục xuất báo cáo và log API | `reports/pilot` | `--report-dir reports/pilot` |
| `--contracts-file` | Đường dẫn `phishing_contracts.log` | `data/raw/phishing_contracts.log` | `--contracts-file data/raw/phishing_contracts.log` |
| `--txs-log-file` | Đường dẫn `phishing_transactions.log` | `data/raw/phishing_transactions.log` | `--txs-log-file data/raw/phishing_transactions.log` |
| `--force-refresh` | Cờ xóa đệm, ép buộc gọi API mới | `False` | `--force-refresh` |

---

## 4. Kiểm Tra Dữ Liệu Kết Quả Sau Khi Chạy

Sử dụng PowerShell và Python trong môi trường ảo để kiểm tra nhanh các file xuất ra:

### 4.1 Xem danh sách địa chỉ và thời gian tạo lập
```powershell
& .\.venv\Scripts\python.exe -c "
import pandas as pd
df = pd.read_csv('reports/pilot/pilot_timestamp_report.csv')
print(df[['address', 'creation_block', 'creation_timestamp_utc', 'tx_count_total', 'status']].to_string())
"
```

### 4.2 Kiểm tra file giao dịch Parquet
```powershell
& .\.venv\Scripts\python.exe -c "
import pandas as pd
df = pd.read_parquet('data/pilot/positive/pilot_transactions.parquet')
print('Tong so giao dich:', len(df))
print(df['tx_type'].value_counts())
"
```

### 4.3 Kiểm tra nhật ký gọi API
```powershell
& .\.venv\Scripts\python.exe -c "
import pandas as pd
df = pd.read_csv('reports/pilot/api_collection_log.csv')
print('Tong so requests:', len(df))
print('Trang thai HTTP:', df['http_status'].value_counts())
"
```

### 4.4 Chạy bộ kiểm thử tự động
```powershell
& .\.venv\Scripts\python.exe tests/test_data_integrity.py
& .\.venv\Scripts\python.exe tests/test_cache_resume.py
```

---

## 5. Xử Lý Sự Cố Thường Gặp (Troubleshooting)

1. **Lỗi `ModuleNotFoundError`:**
   - Hãy chắc chắn chạy bằng đường dẫn Python của virtualenv: `& .\.venv\Scripts\python.exe`.
2. **Lỗi `Missing/Invalid API Key`:**
   - Kiểm tra xem file `.env` đã được đặt đúng tại thư mục gốc chưa, tên biến phải chính xác là `ETHERSCAN_API_KEY`.
3. **Hiện tượng mạng chập chờn / timeout:**
   - Script đã tích hợp sẵn cơ chế thử lại (retry) tối đa 5 lần với exponential backoff. Nếu mạng đứt hoàn toàn, hãy kết nối lại mạng và gõ lại lệnh, tiến trình sẽ tiếp tục tự động từ điểm dừng.
