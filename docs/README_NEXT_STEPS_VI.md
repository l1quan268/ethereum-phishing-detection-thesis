<!-- File: docs/README_NEXT_STEPS_VI.md -->
# Kế Hoạch & Hướng Dẫn Kỹ Thuật Bước Tiếp Theo: Pilot 10 Unlabeled & Tập Dữ Liệu Kết Hợp 20 Địa Chỉ

> **Dự án:** Learning Unified Graph Representations for Ethereum Phishing Detection under Incomplete Labels and Temporal Shifts  
> **Giai đoạn:** Chuẩn bị triển khai Pilot Unlabeled (PU-Learning) & Lọc Point-in-Time Cutoff  
> **Tài liệu tham chiếu:** `docs/data_collection_plan.md`, `docs/three_views_spec.md`, `reports/pilot/bao_cao_pilot_vi.md`  

---

## 1. Mục Tiêu & Cơ Sở Khoa Học

Sau khi đã hoàn thành thu thập và kiểm toán 100% dữ liệu cho **10 địa chỉ Positive**, bước tiếp theo là xây dựng tập đối chứng gồm **10 địa chỉ Unlabeled** cùng thời kỳ triển khai, hướng tới khung bài toán **Positive-Unlabeled Learning (PU-Learning)**.

### Các nguyên tắc khoa học cốt lõi:
1. **Không giả định Unlabeled là Benign:** Các địa chỉ không nằm trong danh sách phishing chỉ được gán nhãn `unlabeled`, bảo đảm tính trung thực khoa học theo đúng bản chất của dữ liệu blockchain.
2. **Khống chế sai lệch phân phối thời gian (Temporal Shift):** Các hợp đồng Unlabeled phải được lấy mẫu trong cùng dải khối ($\pm 50$ blocks) với hợp đồng Positive tương ứng nhằm kiểm soát biến số thời gian (Covariate Shift).
3. **Triệt tiêu rò rỉ thời gian (No Temporal Leakage):** Mọi giao dịch dùng để trích xuất đặc trưng sau này phải tuân thủ điều kiện $T_{\text{tx}} < T_{\text{cutoff}}$.

---

## 2. Quy Trình Kỹ Thuật Dự Kiến

### Bước 2.1: Thuật toán lấy mẫu Matched Unlabeled Contracts
- **Đầu vào:** `data/pilot/positive/pilot_addresses.csv` và `reports/pilot/pilot_timestamp_report.csv` (chứa `creation_block` của 10 hợp đồng Positive).
- **Phạm vi tìm kiếm:** Với mỗi hợp đồng Positive tại khối $B_{\text{pos}}$, quét dải $[B_{\text{pos}} - 50, B_{\text{pos}} + 50]$.
- **Lọc điều kiện:**
  - Là giao dịch tạo hợp đồng (`contract_creation` hoặc `CREATE2`).
  - Địa chỉ hợp đồng tạo ra **KHÔNG ĐƯỢC** xuất hiện trong `data/raw/phishing_contracts.log` (37.654 địa chỉ).
  - Lấy mẫu 1 hợp đồng cho mỗi hợp đồng Positive (tổng cộng 10 hợp đồng Unlabeled).
- **Đầu ra địa chỉ:**
  - Đường dẫn: `data/pilot/unlabeled/pilot_unlabeled_addresses.csv`
  - Định dạng: Tuân thủ đúng `configs/label_schema.csv` với `label_status = unlabeled`.

### Bước 2.2: Thu thập dữ liệu On-Chain cho 10 Hợp đồng Unlabeled
- Chạy pipeline thu thập qua Etherscan API V2:
  - Thông tin tạo lập: `getcontractcreation`
  - Giao dịch trực tiếp: `txlist`
  - Giao dịch nội bộ: `txlistinternal`
  - Chuyển giao token: `tokentx` (ERC-20), `tokennfttx` (ERC-721)
- Áp dụng đệm cache tại `data/cache/<address>/`.
- **Đầu ra giao dịch:**
  - Đường dẫn: `data/pilot/unlabeled/pilot_unlabeled_transactions.parquet`

### Bước 2.3: Tổng hợp tập 20 địa chỉ và Áp dụng Point-in-Time Cutoff
- **Hợp nhất danh sách địa chỉ:**
  - Gộp 10 Positive + 10 Unlabeled thành `data/pilot/combined/pilot_20_addresses.csv`.
- **Xác định ranh giới cắt thời gian (`feature_cutoff_at`):**
  - Thiết lập công thức nhất quán: $T_{\text{cutoff}} = T_{\text{first\_seen}} + \Delta t$ (ví dụ: $\Delta t = 24\text{ giờ}$ hoặc $72\text{ giờ}$).
- **Lọc giao dịch Point-in-Time:**
  - Loại bỏ toàn bộ giao dịch xảy ra sau $T_{\text{cutoff}}$.
  - **Đầu ra:** `data/pilot/combined/pilot_20_transactions_before_cutoff.parquet`.

### Bước 2.4: Báo cáo Kiểm Toán Chất Lượng Dữ Liệu
- Đánh giá phân phối giao dịch, tỷ lệ rò rỉ bị chặn, tỷ lệ khớp nhãn.
- **Đầu ra:** `reports/pilot/pilot_20_quality_report.md`.

---

## 3. Bản Đồ Đường Dẫn Các File Đầu Ra Chuẩn Bị Sẵn

Các thư mục cha đã được tổ chức hoàn chỉnh trong workspace; các tệp đầu ra sẽ được sinh tự động khi chạy bước kế tiếp:

| STT | File đầu ra dự kiến | Thư mục lưu trữ | Mục đích & Ý nghĩa |
| :---: | :--- | :--- | :--- |
| 1 | `pilot_unlabeled_addresses.csv` | `data/pilot/unlabeled/` | Danh sách 10 địa chỉ Unlabeled đối chứng |
| 2 | `pilot_unlabeled_transactions.parquet` | `data/pilot/unlabeled/` | Toàn bộ giao dịch on-chain của 10 Unlabeled |
| 3 | `pilot_20_addresses.csv` | `data/pilot/combined/` | Tập tổng hợp 20 địa chỉ (10 Positive + 10 Unlabeled) |
| 4 | `pilot_20_transactions_before_cutoff.parquet` | `data/pilot/combined/` | Giao dịch đã lọc bỏ rò rỉ thời gian trước cutoff |
| 5 | `pilot_20_quality_report.md` | `reports/pilot/` | Báo cáo kiểm định chất lượng khoa học tập 20 mẫu |

---

## 4. Kiểm Thử Hệ Thống Trước Khi Khởi Chạy

Trước khi kích hoạt pipeline thu thập cho bước kế tiếp, hãy bảo đảm toàn bộ hệ thống vượt qua 2 bộ kiểm tra tự động:

```powershell
& .\.venv\Scripts\python.exe tests/test_data_integrity.py
& .\.venv\Scripts\python.exe tests/test_cache_resume.py
```
