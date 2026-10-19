# Báo Cáo Đánh Giá Chất Lượng Tập Dữ Liệu Pilot 20 Địa Chỉ (10 Positive + 10 Unlabeled)

> **Dự án:** Learning Unified Graph Representations for Ethereum Phishing Detection under Incomplete Labels and Temporal Shifts  
> **Thời điểm thực hiện:** 2026-10-16 02:27:31 UTC  
> **Khung lý thuyết:** Positive-Unlabeled Learning (PU-Learning) & Point-in-Time Temporal Invariance  
> **Phương pháp lấy mẫu:** Matched Block Sampling (phạm vi $\pm 50$ blocks từ Creation Block)  

---

## 1. Tóm Tắt Kết Quả Chính

- **Số lượng hợp đồng:** **20 địa chỉ** (10 Positive + 10 Unlabeled, tỷ lệ 1:1).
- **Độ lệch khối trung bình:** Khảo sát cho thấy 100% hợp đồng Unlabeled đều tìm thấy trong vòng $\pm 50$ blocks, bảo đảm kiểm soát dịch chuyển thời gian (Covariate Shift).
- **Độ trùng lặp địa chỉ giữa 2 tập:** **0 địa chỉ** (Tuyệt đối không có trùng lặp).
- **Tổng số giao dịch thu thập thô:** **5225 giao dịch** (16 Positive + 5209 Unlabeled).
- **Tổng số giao dịch còn lại sau Điểm Cắt Thời Gian 7 ngày (`feature_cutoff_at`):** **2965 giao dịch** (Đã lọc bỏ an toàn 2260 giao dịch rò rỉ tương lai).

---

## 2. Bảng Đối Chiếu Cặp Ghép Thời Kỳ Triển Khai (Matched Pairs)

| Cặp # | Hợp đồng Positive | Khối Pos | Hợp đồng Unlabeled (Đối chứng) | Khối U | Độ lệch khối | Độ lệch thời gian | Creator Unlabeled |
| :---: | :--- | :---: | :--- | :---: | :---: | :---: | :--- |
| 1 | `0x2e176261...434a0e` | 19,535,568 | `0x511fd45f...b14ee5` | 19,535,571 | +3 | +36s | `0x78dc68dd...` |
| 2 | `0x0729eef6...494947` | 19,610,512 | `0xf0d04eaf...56a5c0` | 19,610,514 | +2 | +24s | `0x024b59e6...` |
| 3 | `0x78312c27...c7e96f` | 19,169,759 | `0xe9bb04da...da7bec` | 19,169,763 | +4 | +48s | `0x4f3c8ff7...` |
| 4 | `0x6a8752fe...55c2f4` | 18,709,394 | `0xfbf48501...528a0a` | 18,709,380 | -14 | -168s | `0xefb62472...` |
| 5 | `0x60a9aa9f...d7f636` | 21,381,056 | `0xa9f3acb5...40effd` | 21,381,060 | +4 | +48s | `0x57c62099...` |
| 6 | `0x3aba36f6...02a614` | 19,883,711 | `0xcbe97f75...872846` | 19,883,713 | +2 | +24s | `0x1de36696...` |
| 7 | `0x2a0fc3d3...41d32b` | 19,102,629 | `0x3427d393...a7e79b` | 19,102,632 | +3 | +36s | `0x222d81f2...` |
| 8 | `0xf2bad1c8...501ed7` | 19,891,432 | `0x0766d4e7...648c1d` | 19,891,425 | -7 | -84s | `0xa254f35f...` |
| 9 | `0x22d1b06c...3f3830` | 20,299,670 | `0x42da77b0...192fe9` | 20,299,668 | -2 | -24s | `0x1c671423...` |
| 10 | `0xba182f3f...9d27c1` | 16,540,986 | `0x46338412...8649b1` | 16,540,990 | +4 | +48s | `0xe3ff61b4...` |

---

## 3. Đánh Giá Chất Lượng Theo 8 Tiêu Chí Khoa Học

### 3.1 Có lấy được 10 Unlabeled hợp lệ hay không?
- **Kết quả:** **10/10 hợp đồng Unlabeled (100%)** được xác thực là smart contract thực tế trên Ethereum Mainnet.
- Mỗi hợp đồng đều có transaction tạo lập cụ thể, có bytecode được triển khai trên chuỗi, có `contractCreator` và `creation_timestamp` chính xác qua Etherscan API V2.

### 3.2 Positive và Unlabeled có được ghép cùng giai đoạn triển khai không?
- **Kết quả:** **100% các cặp đều nằm trong phạm vi $\pm 50$ blocks** (tương đương khoảng thời gian chênh lệch dưới 10 phút trên Ethereum PoS/PoW).
- Điều này bảo đảm triệt tiêu độ chệch thời gian (Temporal Bias / Macro Market Regimes) khi so sánh hành vi on-chain giữa hai nhóm.

### 3.3 Có địa chỉ trùng giữa hai nhóm không?
- **Kết quả:** **0 địa chỉ trùng lặp** (10 Positive độc lập và 10 Unlabeled độc lập).
- Toàn bộ 10 địa chỉ Unlabeled đều đã được kiểm tra chéo và loại trừ 100% khỏi danh sách 37.654 hợp đồng trong `phishing_contracts.log`.

### 3.4 Số giao dịch trước và sau Cutoff 7 ngày của từng nhóm
- **Tập Positive:** 16 giao dịch thô -> còn lại **15 giao dịch** trước cutoff (loại bỏ 1 giao dịch sau 7 ngày).
- **Tập Unlabeled:** 5209 giao dịch thô -> còn lại **2950 giao dịch** trước cutoff (loại bỏ 2259 giao dịch sau 7 ngày).
- **Ý nghĩa bảo vệ rò rỉ thời gian:** Giao dịch năm 2025 của hợp đồng Positive `0x6a87...` đã bị loại bỏ hoàn toàn, bảo đảm mô hình không học trước tương lai.

### 3.5 Bao nhiêu địa chỉ không có giao dịch trong 7 ngày đầu?
- **Positive không có tx trong 7 ngày:** 0 địa chỉ.
- **Unlabeled không có tx trong 7 ngày:** 0 địa chỉ.
- *Lưu ý:* Giao dịch khởi tạo hợp đồng (`contract_creation`) được tính là giao dịch tại mốc thời gian $T=0$ nên mọi hợp đồng đều có tối thiểu 1 bản ghi khởi tạo.

### 3.6 Phân bố loại giao dịch trước Cutoff
- **erc20:** 1542 giao dịch (52.0%)
- **internal:** 756 giao dịch (25.5%)
- **normal:** 667 giao dịch (22.5%)

### 3.7 Các hợp đồng có dùng chung Creator hoặc Factory không?
- **Số creator bên Positive:** 5 unique creators (trong đó có các syndicate deployer như `0x0000db5c...` và `0x000099b4...`).
- **Số creator bên Unlabeled:** 10 unique creators.
- **Creator dùng chung giữa Positive và Unlabeled:** 0 creator.
- Nhóm Unlabeled phản ánh phân bố tự nhiên của các deployer thông thường, tạo độ tương phản mạnh mẽ với cấu trúc tập trung của syndicate lừa đảo.

### 3.8 Đã đủ điều kiện bắt đầu xây dựng View 1 chưa?
- **Đánh giá:** **ĐÃ ĐỦ ĐIỀU KIỆN VỀ MẶT KỸ THUẬT VÀ PIPELINE KIỂM THỬ**.
- Dữ liệu đã có đủ 2 lớp nhãn theo PU-learning (`positive` và `unlabeled`).
- Ranh giới Point-in-Time đã được thiết lập nghiêm ngặt, cho phép tính toán 17 đặc trưng thống kê của View 1 (như tần suất giao dịch, khối lượng ETH, số lượng counterparty) mà không sợ rò rỉ thông tin.
- Tuy nhiên, ở quy mô pilot 20 mẫu, đây là bước kiểm chứng tính đúng của mã nguồn trích xuất đặc trưng trước khi mở rộng lên 400 mẫu.

---

## 4. Danh Sách Các Tệp Đã Sinh Ra

1. `data/pilot/unlabeled/pilot_unlabeled_addresses.csv`: 10 địa chỉ Unlabeled kèm cutoff 7 ngày.
2. `data/pilot/unlabeled/pilot_unlabeled_transactions.parquet`: Toàn bộ giao dịch on-chain thô của 10 Unlabeled.
3. `data/pilot/combined/pilot_20_addresses.csv`: Bảng tổng hợp 20 địa chỉ (10 Positive + 10 Unlabeled).
4. `data/pilot/combined/pilot_20_transactions_before_cutoff.parquet`: Toàn bộ giao dịch trước `feature_cutoff_at`.
5. `reports/pilot/pilot_20_quality_report.md`: Báo cáo thẩm định chất lượng khoa học này.
