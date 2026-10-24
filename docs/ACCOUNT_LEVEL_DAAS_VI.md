<!-- File: docs/ACCOUNT_LEVEL_DAAS_VI.md -->
# Chuyển Sang Cấp Tài Khoản Với DaaS Dataset

> **Đề tài:** Learning Unified Graph Representations for Ethereum Phishing Detection under Incomplete Labels and Temporal Shifts  
> **Cập nhật:** 24/10/2026. Trạng thái: **đã thu xong dữ liệu P; đang chờ chốt thiết kế benchmark**  
> **Mã liên quan:** `src/daas/collect_account_events.py`, `src/view2/etherscan_client.py`, `src/view2/collect_events.py`

---

## 1. Vì sao chuyển sang cấp tài khoản

1. **Đề cương** yêu cầu: *"phân loại nhị phân phát hiện địa chỉ lừa đảo phishing trên nền tảng Ethereum ở cấp độ tài khoản account-level"*, với đầu vào gồm *"đặc trưng tài khoản, chuỗi giao dịch, ego-graph, timestamp và trạng thái nhãn Positive/Unlabeled"*.
2. **SIGMETRICS 2025 chỉ gán nhãn hợp đồng** [1]. Pilot 20 cấp hợp đồng cho thấy chuỗi giao dịch của hợp đồng phishing quá ngắn (View 2: positive trung vị 1, tối đa 2 giao dịch; xem README mục 5.1). Tiêu chí dừng đặt trước (trung vị ≤ 3) bị kích hoạt.
3. **DaaS dataset (IMC 2025)** [2], [3] cung cấp sẵn **nhãn ở cấp tài khoản**, cùng nhóm tác giả với SIGMETRICS.

---

## 2. Nguồn dữ liệu

### 2.1. DaaS dataset (nguồn nhãn P chính)

| Tệp | Số lượng | Là gì |
|---|---|---|
| `operator_accounts.log` | 56 | Tài khoản vận hành drainer, nhận phần phí |
| `affiliate_accounts.log` | 6.087 | Tài khoản thuê dịch vụ, trực tiếp lừa, nhận phần lớn tiền |
| `profit_sharing_contracts.log` | 1.910 | Hợp đồng chia lợi nhuận |
| `profit_sharing_transactions.log` | 87.077 | Giao dịch chia lợi nhuận |

Bằng chứng từ bài báo [2]:

- **Giai đoạn:** *"over a period of 21 months, from March 1, 2023 to April 1, 2025"* (§5.2). Khoảng ngày thực tế là khoảng 25 tháng; khi trích dẫn nên dùng mốc ngày.
- **Cách xác định:** giao dịch chia lợi nhuận là giao dịch mà *"The fund flow consists of two transfers"*, *"Both transfers originate from the same account"*, và tỉ lệ đúng mẫu. Operator và affiliate được phân biệt *"based on the transfer amounts"* (§5.1). Tỉ lệ phổ biến cho operator: *"20%, 15%, and 17.5%"* (§4.3).
- **Kiểm chứng:** 3 chuyên gia, mỗi tài khoản 2 người, tổng *"39,037 transactions, accounting for 44.8%"*; *"No false positives were identified"* (§5.2).
- **Hạn chế tác giả tự nêu:** phụ thuộc vào độ tin cậy của tập hạt giống; *"DaaS accounts not linked to the seed dataset through transactions may be overlooked"*.
- **Họ DaaS** (Bảng 2): Angel (3.338 affiliate, 04/2023 → "Now"), Inferno (1.958, 05/2023 → **11/2024**), Pink (279, 04/2023 → **05/2024**), Ace (335), Medusa (56, từ **05/2024**)…
- Repo **không có LICENSE**, nên chỉ tải từ nguồn, không commit.

### 2.2. SIGMETRICS 2025 (vai trò phụ)

| Vai trò | Ghi chú |
|---|---|
| Lý do chuyển cấp | Kết quả View 2 cấp hợp đồng (README mục 5.1) |
| Kiểm chứng cách suy nhãn tài khoản | 1.209/1.910 profit-sharing contract của DaaS nằm trong SIGMETRICS. Pilot: 6/6 địa chỉ suy ra bằng dòng tiền khớp vai trò DaaS (`0x000099b4…`, `0x0000e53a…` là operator; 3 ví nhận 85% là affiliate; `0xee2a0343…` là profit-sharing contract) |
| Mở rộng P (tùy chọn) | Creator và ví nhận của khoảng 36,4 nghìn hợp đồng **không** thuộc DaaS, nhãn suy ra mức B/C |
| Danh sách loại trừ | Nạn nhân (xác định bằng **dòng tiền**, không phải bằng `from` của giao dịch phishing), hợp đồng phishing |

**Không** dùng `in_sigmetrics_tx_log` hay thuộc tính "là hợp đồng phishing" làm đặc trưng, vì đó là thông tin suy ra từ nhãn.

### 2.3. Các nguồn đã xem và **không** dùng

| Nguồn | Lý do |
|---|---|
| MetaMask `eth-phishing-detect` | Danh sách **tên miền**, không phải ví [4] |
| Etherscan `exportaddresstags` | Gói Enterprise, 100 lượt/ngày, chỉ có `lastupdatedtimestamp` [5] |
| PTXPhish (NDSS 2025) | Nhãn mức giao dịch, giai đoạn 2022–2023; chỉ có thể làm test ngoài phân phối [6] |

---

## 3. Các bước đã thực hiện (tái lập được)

Mọi lệnh chạy ở thư mục gốc repo, sau khi kích hoạt `.venv` và có `ETHERSCAN_API_KEY` trong `.env`. Các bước 3.2, 3.3 và 3.5 hiện chạy bằng đoạn mã tạm qua PowerShell (`@' … '@ | python -`) và **cần chuyển thành script trong `src/daas/`**.

### 3.1. Tải DaaS dataset

```powershell
git clone https://github.com/blocksecteam/DaaS_dataset data/raw/daas
```

### 3.2. Thời điểm tạo của profit-sharing contract (382 lượt gọi)

```python
import os, pandas as pd
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(".env")
from src.view2.etherscan_client import EtherscanClient
c = EtherscanClient(os.getenv("ETHERSCAN_API_KEY"), Path("data/cache/view2"))
addrs = [l.strip().lower() for l in open("data/raw/daas/profit_sharing_contracts.log") if l.strip()]
rows = []
for i in range(0, len(addrs), 5):
    for r in c.contract_creation(addrs[i:i + 5]):
        rows.append({"address": r["contractAddress"].lower(), "creation_ts": int(r["timestamp"]),
                     "creation_block": int(r["blockNumber"]), "creator": (r.get("contractCreator") or "").lower()})
df = pd.DataFrame(rows)
df["month"] = pd.to_datetime(df.creation_ts, unit="s", utc=True).dt.strftime("%Y-%m")
df.to_csv("data/interim/daas_contract_creation.csv", index=False)
```

**Kết quả:** 1.910/1.910 lấy được; sớm nhất 07/02/2023, muộn nhất 01/04/2025. Hai đỉnh: 12/2023–01/2024 (528 hợp đồng, 27,6%) và 12/2024–03/2025 (589, 30,8%).

### 3.3. Phân loại EOA / hợp đồng của 6.143 tài khoản (7.371 lượt gọi)

Quy tắc: có thông tin tạo hợp đồng → `contract`; không có và `eth_getCode` = `0x` → `eoa`; mã dạng `0xef0100 ‖ address` (23 byte, EIP-7702 [7]) → `eoa_7702`; còn lại → `unknown`.

```python
import os, pandas as pd
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(".env")
from src.view2.etherscan_client import EtherscanClient, EtherscanError
c = EtherscanClient(os.getenv("ETHERSCAN_API_KEY"), Path("data/cache/view2"))
def read(p): return [l.strip().lower() for l in open(p) if l.strip()]
roles = {a: "operator" for a in read("data/raw/daas/operator_accounts.log")}
roles.update({a: "affiliate" for a in read("data/raw/daas/affiliate_accounts.log")})
addrs = sorted(roles)
created = {}
for i in range(0, len(addrs), 5):
    try:
        for r in c.contract_creation(addrs[i:i + 5]):
            created[r["contractAddress"].lower()] = int(r["timestamp"])
    except EtherscanError:
        pass  # ca lo deu la EOA: Etherscan tra result = None (xem muc 6)
rows = []
for a in [a for a in addrs if a not in created]:
    code = (c.query(module="proxy", action="eth_getCode", address=a, tag="latest").get("result") or "0x").lower()
    kind = "eoa" if code in ("0x", "") else ("eoa_7702" if code.startswith("0xef0100") and len(code) == 48 else "unknown")
    rows.append({"address": a, "role": roles[a], "kind": kind, "code_len": (len(code) - 2) // 2, "creation_ts": None})
rows += [{"address": a, "role": roles[a], "kind": "contract", "code_len": None, "creation_ts": t} for a, t in created.items()]
pd.DataFrame(rows).to_csv("data/interim/daas_account_types.csv", index=False)
```

**Kết quả:**

| | contract | eoa | eoa_7702 | Tổng |
|---|---|---|---|---|
| affiliate | 2 | 5.881 | 204 | 6.087 |
| operator | 0 | 50 | 6 | 56 |
| **Tổng** | **2** | **5.931** | **210** | **6.143** |

- 2 hợp đồng (`0x000b2191…0000`, `0x000bca04…0000`) bị loại khỏi P tài khoản.
- `eth_getCode` trả trạng thái **hiện tại**, nên cờ `eoa_7702` **không** được dùng làm đặc trưng.

### 3.4. Lịch sử giao dịch và `evidence_time` (19.101 lượt gọi)

```powershell
python -m src.daas.collect_account_events --sample 0
```

- Với mỗi EOA: thu `normal` + `internal` + `erc20` từ khối 0 đến `block(2025-04-08)`.
- `evidence_time` = thời điểm sớm nhất của giao dịch có `tx_hash` thuộc `profit_sharing_transactions.log`.
- Lấy lịch sử **của chính tài khoản** thì bắt được cả trường hợp ETH (chia qua giao dịch nội bộ) lẫn trường hợp token (`transferFrom` thẳng từ nạn nhân, §4.2 [2]).
- **Đầu ra:** `data/interim/daas_accounts/events.parquet`, `accounts.csv`.

**Kết quả:**

| Chỉ số | Giá trị |
|---|---|
| Thành công / có `evidence_time` | 6.141 / 6.141 (100%) |
| Nguồn của giao dịch evidence | internal 3.146 · erc20 2.985 · normal 10 |
| Số sự kiện mỗi tài khoản | trung vị 55 · P90 419 · tối đa 39.833 |
| `gap_days` (`first_seen` → `evidence_time`) | trung vị 0 · P75 3,5 · P90 41,9 · tối đa 1.745,5 |
| < 1 ngày / > 30 ngày / > 365 ngày | 4.172 / 735 / 111 |

### 3.5. Làm giàu `accounts.csv` (không gọi API)

```python
import pandas as pd
acc = pd.read_csv("data/interim/daas_accounts/accounts.csv")
ev = pd.read_parquet("data/interim/daas_accounts/events.parquet", columns=["target_address", "tx_hash", "timestamp"])
m = ev.merge(acc[["address", "evidence_ts"]], left_on="target_address", right_on="address")
pre = m[m.timestamp < m.evidence_ts].groupby("address").tx_hash.nunique()
day1 = m[(m.timestamp >= m.evidence_ts) & (m.timestamp < m.evidence_ts + 86400)].groupby("address").tx_hash.nunique()
acc["n_tx_before"] = acc.address.map(pre).fillna(0).astype(int)
acc["n_tx_first_day"] = acc.address.map(day1).fillna(0).astype(int)
acc["ev_month"] = pd.to_datetime(acc.evidence_ts, unit="s", utc=True).dt.strftime("%Y-%m")
acc.to_csv("data/interim/daas_accounts/accounts_enriched.csv", index=False)
```

**Số giao dịch trước `evidence_time`:**

| | 0 | 1–2 | 3–9 | 10–99 | 100+ | Tổng |
|---|---|---|---|---|---|---|
| affiliate | 3.214 | 995 | 821 | 892 | 163 | 6.085 |
| operator | 11 | 11 | 17 | 9 | 8 | 56 |
| **Tổng** | **3.225** | **1.006** | **838** | **901** | **171** | **6.141** |

Trong 24 giờ đầu kể từ `evidence_time`: trung vị 3 giao dịch, P90 19.

**`evidence_time` theo tháng:**

| Tháng | n | % tích lũy | Tháng | n | % tích lũy |
|---|---|---|---|---|---|
| 2023-03 | 17 | 0,3 | 2024-04 | 308 | 56,6 |
| 2023-04 | 68 | 1,4 | 2024-05 | 349 | 62,3 |
| 2023-05 | 148 | 3,8 | 2024-06 | 331 | 67,7 |
| 2023-06 | 191 | 6,9 | 2024-07 | 300 | 72,6 |
| 2023-07 | 192 | 10,0 | 2024-08 | 246 | 76,6 |
| 2023-08 | 250 | 14,1 | 2024-09 | 250 | 80,7 |
| 2023-09 | 232 | 17,9 | 2024-10 | 275 | 85,1 |
| 2023-10 | 206 | 21,2 | 2024-11 | 227 | 88,8 |
| 2023-11 | 272 | 25,7 | 2024-12 | 278 | 93,4 |
| 2023-12 | 316 | 30,8 | 2025-01 | 192 | 96,5 |
| 2024-01 | 437 | 37,9 | 2025-02 | 120 | 98,4 |
| 2024-02 | 380 | 44,1 | 2025-03 | 93 | 100,0 |
| 2024-03 | 460 | 51,6 | 2025-04 | 3 | 100,0 |

---

## 4. Quyết định thiết kế đang chờ chốt

### 4.1. Thời điểm quyết định t\*

52,5% P **không có giao dịch nào trước** `evidence_time`: giao dịch đầu tiên của ví chính là lần nhận tiền chia (nhận tiền không cần trả gas). Vì vậy "phát hiện trước lần lừa đầu tiên" không làm được cho phần lớn P.

| Thiết lập | t\* | Tập P | Vai trò |
|---|---|---|---|
| **Chính** (đề xuất) | `evidence_time` + 1 ngày | 6.141 | "Phát hiện sau lần nhận tiền lừa đầu tiên" |
| **Ablation chống vòng lặp nhãn** | Như trên, **xóa giao dịch chia lợi nhuận khỏi đặc trưng của cả P và U** theo cùng quy tắc | 6.141 | Kiểm tra mô hình có chỉ học lại quy tắc gán nhãn của DaaS hay không (bắt buộc) |
| **Cảnh báo sớm** (phụ) | `evidence_time` (Δ = 0) | 1.910 (≥ 3 giao dịch trước) | "Phát hiện trước lần lừa đầu tiên" cho ví có lịch sử |

### 4.2. Mốc chia theo tháng của t\*

| Phương án | Train | Val | Test | Số P |
|---|---|---|---|---|
| **B (đề xuất)** | ≤ 03/2024 | 04–09/2024 | 10/2024–04/2025 | 3.169 / 1.784 / 1.188 |
| A | ≤ 06/2024 | 07–12/2024 | 01–04/2025 | 4.158 / 1.576 / 408 (test quá nhỏ) |
| C | ≤ 05/2024 | 06–10/2024 | 11/2024–04/2025 | 3.827 / 1.402 / 913 |

Phương án B có tập test đủ lớn và bao trùm thời điểm Inferno ngừng hoạt động (11/2024), tức có **dịch chuyển phân phối thật** về thành phần các họ DaaS.

### 4.3. Tập U

- **Tổng thể:** EOA có ít nhất một giao dịch gửi đi trong tháng m, không thuộc DaaS, không là hợp đồng. Điều kiện áp dụng giống hệt cho P.
- **Số lượng:** U tháng m = k × n_P(m). Pilot k = 5; chính thức k = 10; tập test có thể thêm k = 50 nếu đủ quota.
- **Cách lấy:** Etherscan (lấy theo giao dịch ngẫu nhiên, hiệu chỉnh theo số giao dịch trong tháng) hoặc BigQuery (lấy đều theo địa chỉ).
- **t\* của U:** thời điểm ngẫu nhiên trong tháng m; yêu cầu có ít nhất 1 giao dịch trước t\*.
- **Không** dùng SIGMETRICS làm nguồn U (thiên lệch về nhóm liên quan phishing). Nạn nhân, nếu có trong U, gắn cờ `is_victim`.
- **Chọn k bằng thực nghiệm:** đường hiệu năng trên val theo k ∈ {1, 2, 5, 10, 20}; kiểm định KS so phân phối đặc trưng U giữa k = 10 và k = 20.

### 4.4. Ba View cấp tài khoản (dự kiến)

| View | Dựng từ | Ghi chú |
|---|---|---|
| View 1 | Toàn bộ giao dịch < t\* | Số dư tự tính (cần thêm `gas_price`), tuổi ví, gửi/nhận, tỉ lệ dòng tiền, cửa sổ 30 ngày cuối |
| View 2 | L = 256 giao dịch gần t\* nhất | `build_sequences.py` chế độ tài khoản: bỏ `is_pre_deploy`, thêm `is_new_counterparty`, `log_cum_net_eth` |
| View 3 | Ego-graph 1-hop từ giao dịch < t\* | Không cần gọi thêm API. **Không** dùng nhãn của nút lân cận làm đặc trưng. 2-hop lấy mẫu nếu còn quota |

---

## 5. Rủi ro và hạn chế

- **Vòng lặp nhãn:** nhãn DaaS được xác định bằng mẫu dòng tiền chia lợi nhuận; với t\* sau `evidence_time`, đặc trưng có chứa mẫu đó (xem ablation ở 4.1).
- **Đường tắt "ví trẻ":** 68% P bắt đầu hoạt động dưới 1 ngày trước lần nhận tiền chia đầu; cần so tuổi ví P/U và làm bản U khớp theo tuổi ví.
- **Độ đa dạng:** P chỉ gồm một loại hình (DaaS); hơn 80% affiliate thuộc Angel và Inferno.
- **Cùng nhóm tác giả** với SIGMETRICS, nên cùng thiên lệch phát hiện.
- **Không có thời điểm gắn nhãn:** `evidence_time` là thời điểm *hành vi*, không phải lúc bị phát hiện.
- **Rò rỉ theo nhóm:** tài khoản cùng họ hoặc cùng operator có thể nằm ở cả train và test; dataset không kèm nhãn họ cho từng tài khoản, cần tự gom.

---

## 6. Việc kỹ thuật còn tồn đọng

- `etherscan_client._is_cacheable` không cache kết quả `getcontractcreation` khi cả lô đều là EOA (`result = None`), nên chạy lại bước 3.3 sẽ gọi lại khoảng 1.229 lượt.
- Chuyển các đoạn mã 3.2, 3.3, 3.5 thành script trong `src/daas/` và viết test.
- `normalize_rows` chưa giữ `gasPrice` (cần cho số dư ở View 1).

---

## 7. Tài liệu tham khảo

[1] B. He, X. Hu, Y. Hu, T. Yu, R. Chang, L. Wu, Y. Zhou, "Phishing Tactics Are Evolving: An Empirical Study of Phishing Contracts on Ethereum," *Proc. ACM Meas. Anal. Comput. Syst.*, vol. 9, no. 2, 2025, doi: 10.1145/3727138.
[2] B. He, Y. Hu, Z. Chen, Y. Chen, T. Yu, R. Chang, L. Wu, Y. Zhou, "Unmasking the Shadow Economy: A Deep Dive into Drainer-as-a-Service Phishing on Ethereum," in *Proc. ACM IMC*, Madison, WI, USA, 2025, pp. 430–444, doi: 10.1145/3730567.3764476.
[3] BlockSec, *DaaS_dataset*, GitHub. https://github.com/blocksecteam/DaaS_dataset
[4] MetaMask, *eth-phishing-detect*, GitHub. https://github.com/MetaMask/eth-phishing-detect
[5] Etherscan, "exportaddresstags," API documentation. https://docs.etherscan.io/api-reference/endpoint/exportaddresstags.md
[6] "Dissecting Payload-based Transaction Phishing on Ethereum," in *Proc. NDSS*, 2025. https://arxiv.org/pdf/2409.02386
[7] "EIP-7702: Set Code for EOAs," Ethereum Improvement Proposals. https://eips.ethereum.org/EIPS/eip-7702

---

## 8. Giải thích ký hiệu và thuật ngữ

| Ký hiệu / thuật ngữ | Giải thích |
|---|---|
| Cấp tài khoản | Đơn vị phân loại là địa chỉ ví, không phải hợp đồng |
| EOA / `eoa_7702` | Ví do người dùng giữ khóa / ví có mã ủy quyền EIP-7702 (`0xef0100 ‖ address`) |
| DaaS / operator / affiliate | Drainer-as-a-Service / bên vận hành nhận phí / bên thuê dịch vụ, trực tiếp lừa |
| Profit-sharing contract / transaction | Hợp đồng / giao dịch chia tiền nạn nhân cho operator và affiliate |
| `evidence_time` | Lần đầu tài khoản tham gia một giao dịch chia lợi nhuận |
| `first_seen` / `gap_days` | Giao dịch đầu tiên của ví / số ngày từ đó đến `evidence_time` |
| t\* / Δ | Thời điểm quyết định / khoảng cộng thêm sau `evidence_time` |
| T1 / T2 | Mốc chia train / val / test theo thời gian |
| P / U / k | Positive / unlabeled / số U cho mỗi P trong cùng tháng |
| π | Tỉ lệ phishing ẩn trong U, tham số của nnPU |
| Vòng lặp nhãn | Đặc trưng chứa chính mẫu đã dùng để gán nhãn |
| Họ DaaS | Nhóm drainer cùng bên vận hành (Angel, Inferno, Pink…) |
| Kiểm định KS | Kolmogorov–Smirnov, kiểm tra hai mẫu có cùng phân phối |
| `transferFrom` | Hàm ERC-20 chuyển token của người khác khi đã được cấp quyền |
| `eth_getCode` | Lấy bytecode hiện tại của một địa chỉ |