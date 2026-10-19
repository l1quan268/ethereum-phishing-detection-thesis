# Báo Cáo Kiểm Toán Ngữ Nghĩa Chuỗi Khối & Chốt Phiên Bản View 1 (Pilot 20 Hợp Đồng)

> **Dự án Khóa luận Tốt nghiệp:** Learning Unified Graph Representations for Ethereum Phishing Detection under Incomplete Labels and Temporal Shifts  
> **Cấu phần:** View 1 Statistical Tabular Features (Pilot 20 Hợp Đồng: 10 Positive + 10 Unlabeled)  
> **Thời điểm thẩm định:** 2026-10-16 14:15:00 UTC  
> **Chuyên gia thực hiện:** Senior Blockchain Data Engineer, Ethereum EVM Analyst & ML Research Engineer  
> **Khung nghiên cứu:** Positive-Unlabeled (PU) Learning, Point-in-Time Temporal Invariance, EVM Execution Semantics  

---

## 1. Mục Tiêu & Phạm Vi Kiểm Toán Cuối Cùng

Phiên làm việc này tập trung **kiểm toán chuyên sâu ngữ nghĩa giao dịch Ethereum (EVM Semantics)**, khắc phục các bất cập số liệu sơ bộ, loại bỏ double-counting và chuẩn hóa dứt điểm tập đặc trưng View 1 trên tập dữ liệu thử nghiệm 20 hợp đồng (Pilot 20).

**Cam kết phương pháp luận:**
- Không làm lại từ đầu; không gọi Etherscan API mới; không mở rộng quy mô lên 400 địa chỉ; không huấn luyện mô hình học máy.
- Bảo toàn 100% tính nguyên bản của tập dữ liệu gốc (`data/raw/`) và dữ liệu pilot trung gian (`data/pilot/`).
- Toàn bộ kết quả phiên bản cũ đã được sao lưu an toàn tại `data/processed/view1/backup_v1/`.

---

## 2. Kết Quả Kiểm Toán Ngữ Nghĩa Giao Dịch Chuỗi Khối

### 2.1 Kiểm toán B1: Giải Quyết Tính Nhất Quán Giữa "Unique Tx" và "Records View 1 Hợp Lệ"

Trong các báo cáo sơ bộ trước đây, xuất hiện trường hợp một số hợp đồng Positive ghi nhận `Unique Tx = 2` nhưng cột `Records View 1 Hợp Lệ = 1` (ví dụ: `0x0729eef6...`, `0x3aba36f6...`, `0xf2bad1c8...`). 

**Nguyên nhân kỹ thuật được làm rõ:**
- **Sự khác biệt bắt nguồn từ hai cửa sổ thời gian khác nhau:**
  1. *Cửa sổ toàn bộ trước Cutoff* ($T_{\text{tx}} < T_{\text{cutoff}}$): Tệp `pilot_20_transactions_before_cutoff.parquet` chứa tất cả giao dịch thu thập được trước mốc 7 ngày, bao gồm cả các giao dịch phát sinh **trước thời điểm deploy**. Tại cửa sổ này, hợp đồng `0x0729...` có 2 giao dịch phân biệt (1 giao dịch tiền deploy ở block $B-1$ và 1 giao dịch tạo lập contract ở block $B$). Do đó, nếu đếm trên tệp này thì `Unique Tx = 2`.
  2. *Cửa sổ hợp lệ sau triển khai* ($T_{\text{creation}} \le T_{\text{tx}} < T_{\text{cutoff}}$): Đây là cửa sổ chuẩn hóa duy nhất đi vào vector đặc trưng $\mathbf{x}_C$. Tại cửa sổ này, giao dịch tiền triển khai đã bị loại trừ, nên số giao dịch hợp lệ sau deploy chỉ còn **đúng 1 giao dịch** (`unique_tx_count = 1` và `total_event_count = 1`).
- **Khắc phục chuẩn hóa:**
  * Sửa đổi tiêu đề cột trong bảng báo cáo thành: **"Unique Tx Sau Deploy ($T_{\text{creation}} \le T < T_{\text{cutoff}}$)"** và **"Tổng Tx Trước Cutoff ($T < T_{\text{cutoff}}$)"**.
  * Dữ liệu trong ma trận View 1 (`view1_features_pilot.parquet`) hoàn toàn nhất quán: đối với các hợp đồng này, `unique_tx_count = 1` và `total_event_count = 1`.

---

### 2.2 Kiểm toán B2: Ngữ Nghĩa Chuyển ETH & Giao Dịch Lỗi (Reverted Transfers)

Kiểm toán toàn bộ 752 bản ghi có `value_eth > 0` trong dữ liệu trước cutoff phát hiện:
1. **Phát hiện lỗi ngữ nghĩa EVM ở phiên bản sơ bộ:**
   - Trong 752 bản ghi có giá trị ETH, có chính xác **26 bản ghi bị revert (`is_error == 1`)**, toàn bộ đều là các cuộc gọi internal transfer hướng tới hợp đồng Unlabeled `0xa9f3acb50feb079806a03d5b66e2ebdd5c40effd`.
   - Tổng lượng ETH trong 26 giao dịch revert này là **1.614035 ETH**.
   - Trong EVM, khi một transaction hoặc sub-call bị revert (`is_error == 1`), toàn bộ state change bị hủy bỏ (rollback), số dư Ether **không hề được chuyển giao trên thực tế**.
   - Phiên bản sơ bộ đã tính gộp cả 26 giao dịch này khiến `value_total_in_eth` của `0xa9f3...` bị thổi phồng lên **27.503189 ETH**.
2. **Chuẩn hóa công thức ETH:**
   - Lọc nghiêm ngặt điều kiện thực thi thành công: `(tx_type in ['normal', 'internal']) & (is_error == 0)`.
   - Giá trị ETH nhận thực tế sau chuẩn hóa của `0xa9f3...` giảm về đúng giá trị thực: **25.889154 ETH** (chênh lệch đúng bằng 1.614035 ETH của các giao dịch lỗi).
3. **Phân biệt Normal, Internal và Token:**
   - Toàn bộ 20 hợp đồng có 5 normal txs và 747 internal txs có `value_eth > 0`.
   - Khảo sát kiểm tra cho thấy: **Không có bất kỳ giao dịch nào bị tính trùng lặp cùng một lần chuyển ETH giữa normal tx và internal trace** (trong 721 giao dịch đa sự kiện, bản ghi normal hoặc internal chỉ chuyển ETH đúng một lần, bản ghi còn lại là sự kiện chuyển token với `value_eth == 0.0`).
4. **Giới hạn của dữ liệu Etherscan API:**
   - Do Etherscan API miễn phí không cung cấp cây gọi sâu (`traceId` phân cấp hoặc sub-trace call stack), ta không thể phân tích các vi cấu trúc bên trong các hợp đồng phức tạp nhiều tầng. Pipeline ghi nhận rõ ràng giới hạn này thay vì tuyên bố giải quyết triệt để double-counting ở cấp độ sub-call.

---

### 2.3 Kiểm toán B3: Khử Trùng Lặp Gas Ở Cấp Độ Transaction Receipt

1. **Phát hiện lỗi thổi phồng Gas trong các giao dịch đa sự kiện (Multi-event):**
   - Trên Ethereum, gas tiêu thụ được tính toán và thanh toán bởi tài khoản EOA khởi tạo cho toàn bộ giao dịch (thể hiện qua trường `gasUsed` trong transaction receipt).
   - Khi Etherscan trả về dữ liệu qua các endpoint khác nhau cho cùng một `tx_hash`:
     * Endpoint `tokentx` trả về receipt `gasUsed` của toàn bộ giao dịch.
     * Endpoint `txlistinternal` trả về lượng gas tiêu thụ riêng của sub-trace đó.
   - *Hậu quả ở phiên bản sơ bộ:* Việc tính `gas_used_total = sub['gas_used'].sum()` đã cộng dồn gas của receipt với gas của trace nội bộ!
     * Ví dụ điển hình tại hợp đồng Positive `0x2e176261...`: Giao dịch `0x4b0f...` có trace create2 tiêu thụ $493.575$ gas, trong khi receipt tổng của giao dịch là $616.275$ gas. Việc cộng dồn tạo ra $1.109.850$ gas (thổi phồng thêm 80% gas!).
     * Tại hợp đồng `0xa9f3...`: Tổng gas bị thổi phồng thêm **9.037.291 gas** (từ 439.243.165 gas lên 448.280.456 gas).
2. **Chuẩn hóa thuật toán Gas:**
   - Nhóm các bản ghi theo `tx_hash` duy nhất và lấy giá trị lớn nhất:
     $$
     \text{tx\_gas}(h) = \max_{e \in \mathcal{E}(C), \, \text{hash}(e) = h, \, \text{gas\_used}(e) \ge 0} \text{gas\_used}(e)
     $$
   - `gas_used_total` là tổng các `tx_gas(h)`, bảo đảm phản ánh chính xác lượng gas on-chain được tiêu thụ, loại bỏ hoàn toàn hiện tượng cộng trùng lặp gas giữa các endpoint.
3. **Chuẩn hóa tỷ lệ lỗi (`error_tx_rate`):**
   - Số giao dịch lỗi được tính theo số mã băm duy nhất bị revert: `error_tx_count = COUNT(DISTINCT tx_hash WHERE is_error == 1)`.
   - Mẫu số được chuẩn hóa thành `max(unique_tx_count, 1)` thay vì chỉ chia cho normal transactions (`tx_count_total`). Nhờ đó, tỷ lệ lỗi của hợp đồng `0xa9f3...` phản ánh đúng: $29 / 2.135 = \mathbf{1.358\%}$ (thay vì con số méo mó $4.69\%$ trước đây).

---

### 2.4 Kiểm toán B4: Phân Định Rõ Bằng Chứng Dữ Liệu, Suy Luận EVM & Giả Thuyết

Để bảo đảm tính khách quan và trung thực của một nghiên cứu khoa học, bảng dưới đây phân định rạch ròi 3 cấp độ thông tin:

| Đối Tượng Kiểm Toán | Bằng Chứng Thực Nghiệm Trực Tiếp (Empirical Evidence) | Suy Luận Kỹ Thuật EVM (Technical Inferences) | Giả Thuyết Chưa Được Xác Minh (Unverified Hypotheses) |
| :--- | :--- | :--- | :--- |
| **4 Bản ghi tiền triển khai ($T_{\text{tx}} < T_{\text{creation}}$)** | - Xuất hiện ở 4 hợp đồng Positive: 3 normal txs gọi `claim(address,uint256)` ở block $B-1$, 1 erc20 tx ở block $B-2$.<br>- Cả 3 normal txs đều tiêu thụ đúng **21.572 gas**.<br>- Cả 3 contract đều được tạo bởi Factory `0xee2a...` qua opcode `CREATE2`. | - Với `CREATE2`, địa chỉ đích là tiền định (counterfactual address).<br>- Gửi ETH/calldata tới tài khoản rỗng (chưa có code) trên EVM được tính là transfer thông thường: $21.000\text{ base} + 572\text{ data} = 21.572\text{ gas}$, trạng thái thành công (`is_error=0`). | - *Giả thuyết:* Kẻ tấn công tạo dựng bẫy airdrop frontend dụ nạn nhân gửi tiền trước khi deploy bytecode để vét cạn tiền.<br>*(Đây là giả thuyết bảo mật off-chain, dữ liệu on-chain không ghi nhận được ý định chủ quan của attacker).* |
| **Hợp đồng Unlabeled `0xa9f3...` (2.859 bản ghi)** | - 100% token transfer trong 7 ngày đầu là token Fintra AI (`FINAI`).<br>- Trước cutoff có **560 cuộc gọi `approve`** và **51 cuộc gọi `transfer`**.<br>- 26 cuộc gọi internal bị revert (`is_error=1`) với 1.614 ETH không chuyển thành công. | - Hợp đồng này là một token ERC-20 trading có thanh khoản trên Uniswap, được triển khai vào giai đoạn sốt token AI tháng 12/2024.<br>- Khối lượng giao dịch lớn do bot và người dùng mua bán swap liên tục sau khi `enableTrading()` được kích hoạt. | - *Giả thuyết:* Liệu `0xa9f3...` có phải là Honeypot hay scam rug-pull hay không?<br>*(Chưa xác minh được vì hợp đồng mang nhãn `unlabeled` theo PU-learning, chưa có phân tích mã nguồn bytecode chuyên sâu).* |
| **Sự khác biệt giữa 926 và 560 cuộc gọi `approve`** | - Tệp cache thô `txlist_page1.json` chứa 1.000 tx có **926 lần gọi `approve`**.<br>- Trong 1.000 tx đó, có **618 tx trước cutoff** và **382 tx sau cutoff**.<br>- Trong 618 tx trước cutoff, có đúng **560 lần gọi `approve`**; 366 lần còn lại diễn ra sau mốc 7 ngày. | - Con số 926 lần gọi `approve` trong báo cáo sơ bộ là do đếm trên toàn bộ trang cache 1 của Etherscan (bao gồm cả tương lai). Sau khi áp dụng lọc Point-in-Time 7 ngày, con số chính xác là 560. | Không có (Đã được chứng minh bằng dữ liệu 100%). |

---

## 3. Bảng Tổng Hợp Số Liệu Chuẩn Hóa Của 20 Hợp Đồng Pilot

Dưới đây là bảng dữ liệu chuẩn hóa cuối cùng sau khi áp dụng toàn bộ các nguyên tắc kiểm toán ngữ nghĩa EVM:

| STT | Địa Chỉ Hợp Đồng | Nhãn PU | Block Deploy | Tổng Records Trước Cutoff | Records Tiền Deploy (Audited) | Records Hợp Lệ Sau Deploy | Unique Tx Sau Deploy | ETH Nhận Hợp Lệ (ETH) | Gas Tiêu Thụ Chuẩn Hóa (Gas) | Tx Lỗi |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | `0x2e176261...434a0e` | Positive | 19,535,568 | 3 | 1 | **2** | **1** | 0.0000 | 616,275 | 0 |
| 2 | `0x0729eef6...494947` | Positive | 19,610,512 | 2 | 1 | **1** | **1** | 0.0000 | 120,389 | 0 |
| 3 | `0x78312c27...c7e96f` | Positive | 19,169,759 | 1 | 0 | **1** | **1** | 0.0000 | 176,466 | 0 |
| 4 | `0x6a8752fe...55c2f4` | Positive | 18,709,394 | 1 | 0 | **1** | **1** | 0.0000 | 493,575 | 0 |
| 5 | `0x60a9aa9f...d7f636` | Positive | 21,381,056 | 1 | 0 | **1** | **1** | 0.0000 | 158,489 | 0 |
| 6 | `0x3aba36f6...02a614` | Positive | 19,883,711 | 2 | 1 | **1** | **1** | 0.0000 | 120,389 | 0 |
| 7 | `0x2a0fc3d3...41d32b` | Positive | 19,102,629 | 1 | 0 | **1** | **1** | 0.0000 | 493,575 | 0 |
| 8 | `0xf2bad1c8...501ed7` | Positive | 19,891,432 | 2 | 1 | **1** | **1** | 0.0000 | 120,389 | 0 |
| 9 | `0x22d1b06c...3f3830` | Positive | 20,299,670 | 1 | 0 | **1** | **1** | 0.0000 | 493,575 | 0 |
| 10 | `0xba182f3f...9d27c1` | Positive | 16,540,986 | 1 | 0 | **1** | **1** | 0.0000 | 226,249 | 0 |
| 11 | `0x511fd45f...b14ee5` | Unlabeled | 19,535,571 | 51 | 0 | **51** | **46** | 0.1533 | 12,492,006 | 0 |
| 12 | `0xf0d04eaf...56a5c0` | Unlabeled | 19,610,514 | 1 | 0 | **1** | **1** | 0.0000 | 833,370 | 0 |
| 13 | `0xe9bb04da...da7bec` | Unlabeled | 19,169,763 | 2 | 0 | **2** | **2** | 0.0100 | 193,912 | 0 |
| 14 | `0xfbf48501...528a0a` | Unlabeled | 18,709,380 | 2 | 0 | **2** | **2** | 0.0000 | 1,917,640 | 0 |
| 15 | `0xa9f3acb5...40effd` | Unlabeled | 21,381,060 | 2,859 | 0 | **2,859** | **2,135** | 25.8892 | 439,243,165 | 29 |
| 16 | `0xcbe97f75...872846` | Unlabeled | 19,883,713 | 25 | 0 | **25** | **20** | 0.0425 | 8,565,046 | 0 |
| 17 | `0x3427d393...a7e79b` | Unlabeled | 19,102,632 | 1 | 0 | **1** | **1** | 0.0000 | 1,588,071 | 0 |
| 18 | `0x0766d4e7...648c1d` | Unlabeled | 19,891,425 | 1 | 0 | **1** | **1** | 0.0000 | 665,836 | 0 |
| 19 | `0x42da77b0...192fe9` | Unlabeled | 20,299,668 | 6 | 0 | **6** | **5** | 0.0300 | 805,181 | 0 |
| 20 | `0x46338412...8649b1` | Unlabeled | 16,540,990 | 2 | 0 | **2** | **2** | 0.0000 | 1,249,018 | 0 |

---

## 4. So Sánh Thống Kê Giữa Hai Nhóm Positive và Unlabeled (P vs U)

| Đặc Trưng Thống Kê | Nhóm Positive (P) — Mean | Nhóm Positive (P) — Median | Nhóm Unlabeled (U) — Mean | Nhóm Unlabeled (U) — Median | Đánh Giá Khác Biệt Hành Vi Chuỗi Khối |
| :--- | :---: | :---: | :---: | :---: | :--- |
| `total_event_count` | 1.10 | 1.00 | 295.00 | 2.00 | Positive có hoạt động sau deploy cực kỳ nghèo nàn; Unlabeled phân tán mạnh |
| `unique_tx_count` | 1.00 | 1.00 | 221.40 | 2.00 | 100% Positive chỉ có đúng 1 transaction sau deploy trong pilot này |
| `internal_tx_count` | 0.90 | 1.00 | 74.70 | 0.00 | 9/10 Positive tạo lập qua factory internal trace (`create2`) |
| `erc20_transfer_count`| 0.10 | 0.00 | 154.00 | 0.00 | Positive không luân chuyển token công khai sau deploy trong cửa sổ 7 ngày |
| `value_total_in_eth` | 0.0000 ETH | 0.0000 ETH | 2.6125 ETH | 0.0000 ETH | Positive không có ETH nhận thành công sau khi trừ giao dịch tiền deploy |
| `gas_used_total` | 301,937 gas | 197,639 gas | 46,755,325 gas | 1,041,194 gas | Positive tiêu thụ ít gas hơn do không có tương tác người dùng sau deploy |
| `error_tx_count` | 0.00 | 0.00 | 2.90 | 0.00 | Chỉ xuất hiện lỗi ở các giao dịch tương tác phức tạp của Unlabeled |
| `error_tx_rate` | 0.0000 | 0.0000 | 0.0014 | 0.0000 | Tỷ lệ lỗi chuẩn hóa trên toàn bộ transaction duy nhất |

---

## 5. Danh Mục Đặc Trưng & Tính Toàn Vẹn Kiểm Thử

### 5.1 Phân Loại 32 Đặc Trưng Trích Xuất và 3 Đặc Trưng Chưa Khả Dụng

- **32 Đặc trưng đã trích xuất hoàn thiện:** `tx_count_total`, `tx_count_in`, `tx_count_out`, `tx_in_out_ratio`, `normal_tx_in`, `normal_tx_out`, `internal_tx_count`, `erc20_transfer_count`, `erc721_transfer_count`, `total_event_count`, `unique_tx_count`, `value_total_in_eth`, `value_total_out_eth`, `value_net_eth`, `value_mean_in_eth`, `value_std_in_eth`, `value_max_in_eth`, `unique_senders`, `unique_receivers`, `unique_counterparties_total`, `unique_counterparty_ratio`, `top_sender_tx_ratio`, `lifespan_seconds`, `active_days`, `active_hours`, `tx_frequency_per_hour`, `event_rate_7d`, `gas_used_mean`, `gas_used_total`, `error_tx_count`, `error_tx_rate`, `method_diversity`.
- **3 Đặc trưng chưa đủ thông tin (`NOT_AVAILABLE`):**
  1. `bytecode_size`: Cần opcode từ `eth_getCode`.
  2. `has_selfdestruct`: Cần quét bytecode tìm opcode `0xFF`.
  3. `deployer_tx_count`: Cần truy vấn toàn bộ lịch sử giao dịch của ví deployer trước cutoff.
  *Nguyên tắc nghiêm ngặt:* Giữ ở trạng thái `NOT_AVAILABLE`, tuyệt đối không điền số 0 giả định vào ma trận đặc trưng $\mathbf{X}$.

### 5.2 Bộ Kiểm Thử Khoa Học (12 Tiêu Chí Tự Động)

Bộ kiểm thử [tests/test_view1.py](file:///d:/KH%C3%93A%20LU%E1%BA%ACN/phishing_contract_sigmetrics25/tests/test_view1.py) đã được nâng cấp bổ sung 3 test chuyên biệt về EVM semantics, đạt kết quả **12/12 PASSED (100%)**:
1. Đủ 20 địa chỉ đầu ra, mỗi địa chỉ 1 dòng.
2. Không có địa chỉ trùng lặp.
3. Ranh giới thời gian nghiêm ngặt ($T_{\text{creation}} \le T_{\text{tx}} < T_{\text{cutoff}}$).
4. Phân tách đơn vị ETH và Token ERC-20/721.
5. Phân biệt sự kiện và kiểm soát double-counting.
6. Xử lý an toàn missing/zero (không có NaN hoặc Inf).
7. Cô lập nhãn tuyệt đối (Vector $\mathbf{X}$ không chứa label hoặc ID định danh).
8. Tính xác định và khả năng tái lập (Determinism / Bitwise-identical).
9. Tính bất biến của dữ liệu thô và dữ liệu pilot trung gian.
10. **Ngữ nghĩa EVM về ETH:** Chỉ tính giao dịch thành công (`is_error == 0`), loại bỏ 1.614 ETH của 26 giao dịch revert.
11. **Khử trùng lặp Gas:** Tính gas theo receipt cấp độ Transaction, bảo đảm không double-count trên các giao dịch đa sự kiện.
12. **Đối chiếu Ground-Truth:** So sánh line-by-line từng đặc trưng với transaction thực tế trên 3 hợp đồng đại diện (`0xba18...`, `0x2e17...`, `0xa9f3...`).

---

## 6. Đánh Giá Khách Quan Mức Độ Sẵn Sàng (Readiness Assessment)

| Hạng Mục | Đánh Giá | Nhận Xét Khoa Học & Kỹ Thuật |
| :--- | :---: | :--- |
| **Pipeline Mã Nguồn View 1** | **XUẤT SẮC** | Đã xử lý đầy đủ các ngóc ngách ngữ nghĩa EVM (Gas deduplication, Revert rollback, Asset separation, Label isolation). |
| **Tính Toàn Vẹn Dữ Liệu** | **BẢO TOÀN 100%** | Dữ liệu gốc và pilot không bị can thiệp; bản lưu trữ cũ được backup tại `backup_v1/`. |
| **Tài Liệu Hướng Dẫn Seminar** | **HOÀN THÀNH** | Đã biên soạn tệp trực quan [docs/VIEW1_PIPELINE_VI.md](file:///d:/KH%C3%93A%20LU%E1%BA%ACN/phishing_contract_sigmetrics25/docs/VIEW1_PIPELINE_VI.md) kèm sơ đồ Mermaid chi tiết. |
| **Mở Rộng Quy Mô (400 Hợp Đồng)** | **ĐỦ ĐIỀU KIỆN KỸ THUẬT** | Pipeline trích xuất đã sẵn sàng để chạy trên tập quy mô lớn khi được phê duyệt. |

> [!CAUTION]
> **Cảnh báo phương pháp luận:** Mặc dù 12/12 unit tests đã vượt qua, kết quả này **chưa chứng minh mô hình ML sẽ phát hiện được phishing**. Đây mới chỉ là bước kiểm chứng tính đúng đắn và toàn vẹn của pipeline trích xuất đặc trưng on-chain. Cần tiếp tục theo dõi chặt chẽ khi mở rộng quy mô dữ liệu.
