# Quy Ước Lưu Code Và Bằng Chứng Chạy

Mục tiêu: mọi con số đưa vào báo cáo/luận văn đều truy ngược được về **đúng đoạn code**, **đúng commit**, **đúng dữ liệu vào** và **đúng output màn hình** của lần chạy sinh ra nó.

## 1. Code để ở đâu

| Loại | Vị trí | Ví dụ |
|---|---|---|
| Thư viện / pipeline dùng lại | `src/<module>/` | `src/view2/collect_events.py`, `src/daas/collect_account_events.py` |
| Bước phân tích / khảo sát đánh số | `scripts/<khu_vuc>/sNN_<ten>.py` | `scripts/daas/s01_contract_creation.py` |
| Bộ chạy ghi bằng chứng | `scripts/run.py` | (dùng cho mọi lần chạy ở trên) |
| Kiểm thử | `tests/test_*.py` | `tests/test_evidence_scripts.py` |

Mỗi script `sNN_*.py` có docstring ghi: mục đích, đầu vào, đầu ra, lệnh chạy, chi phí API ước tính. Không chạy đoạn Python dán thẳng vào terminal cho kết quả sẽ dùng trong báo cáo: lưu nó thành script trước.

## 2. Chạy thế nào

```bash
python -m scripts.run --name <ten_ngan> \
    --inputs  <tep_vao> ... \
    --outputs <tep_ra> ... \
    -- <module> [tham so cua module]
```

Dấu `--` trước `<module>` là **bắt buộc**; thiếu nó thì `--outputs` nuốt luôn tên module.

## 3. Kết quả nằm ở đâu, có commit không

| Thư mục | Nội dung | Commit? |
|---|---|---|
| `reports/runs/<YYYY-MM-DDTHHMMSSZ>_<ten>/stdout.txt` | Toàn bộ output màn hình (stdout + stderr) | **Có** |
| `reports/runs/<...>/meta.json` | Commit git, nhánh, có thay đổi chưa commit không (`git_dirty`), lệnh, phiên bản Python/thư viện, SHA-256 + kích thước tệp vào/ra, trạng thái, thời gian chạy | **Có** |
| `reports/<khu_vuc>/sNN_*.csv` | Bảng tóm tắt nhỏ (đưa vào báo cáo) | **Có** |
| `data/interim/`, `data/processed/` | Dữ liệu chi tiết, lớn | Không (chỉ lưu SHA-256 trong `meta.json`) |
| `data/raw/`, `data/cache/`, `.env` | Dữ liệu gốc, cache API, khóa | **Không bao giờ** |

`stdout.txt` dùng đuôi `.txt` vì `.gitignore` đang bỏ qua `*.log`. `meta.json` không ghi biến môi trường nên không lộ API key.

## 4. Quy tắc

1. Commit code **trước** khi chạy lần cho số liệu chính thức, để `git_commit` trỏ đúng code và `git_dirty=false`.
2. Không sửa tay `stdout.txt`, `meta.json` hay CSV trong `reports/`. Chạy lại thì tạo thư mục run mới; giữ cả lần cũ.
3. Lần chạy lỗi cũng giữ lại (`status` khác `ok`): đó là bằng chứng cho quyết định đổi hướng.
4. Trong tài liệu (`docs/`, `PROGRESS.md`), mỗi bảng số liệu ghi nguồn dạng: `nguồn: reports/runs/2026-10-24T101356Z_daas_enrich_accounts/`.
5. Kiểm tra lại dữ liệu chi tiết: so SHA-256 trong `meta.json` với tệp hiện có (`sha256sum` trên Linux/macOS, `Get-FileHash -Algorithm SHA256` trên PowerShell).

## 5. Các bước DaaS hiện có

| Bước | Module | Đầu ra commit |
|---|---|---|
| S01 | `scripts.daas.s01_contract_creation` | `reports/daas/s01_contract_creation_by_month.csv` |
| S02 | `scripts.daas.s02_account_types` | `reports/daas/s02_account_types_summary.csv`, `s02_non_eoa.csv` |
| S03 | `src.daas.collect_account_events --sample 0` | (chỉ `stdout.txt` + `meta.json`) |
| S04 | `scripts.daas.s04_enrich_accounts` | `reports/daas/s04_tx_before_evidence.csv`, `s04_evidence_by_month.csv` |
