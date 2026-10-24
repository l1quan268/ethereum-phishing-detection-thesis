<!-- File: docs/view1_feature_spec.md -->
# Đặc Tả Kỹ Thuật & Mô Hình Hóa Toán Học — View 1 Statistical Features

> **Đề tài:** Learning Unified Graph Representations for Ethereum Phishing Detection under Incomplete Labels and Temporal Shifts  
> **Cấu phần:** View 1 — Statistical Tabular Features (Node-Level Aggregates)  
> **Phiên bản:** 1.0 (Pilot 20 Ethereum Smart Contracts)  
> **Tác giả:** Senior Blockchain Data Engineer & ML Research Engineer  

---

## 1. Định Nghĩa Mô Hình & Khung Toán Học

### 1.1 Đơn vị dự đoán (Unit of Prediction)
Đơn vị dự đoán là **một hợp đồng thông minh Ethereum $C$ tại thời điểm chốt quan sát (Point-in-Time Cutoff) $T_{\text{cutoff}}$**.

Mỗi hợp đồng $C$ được ánh xạ thành duy nhất một dòng đặc trưng trong ma trận thực nghiệm:
$$
\mathbf{x}_C \in \mathbb{R}^D
$$
trong đó $D = 32$ là số chiều đặc trưng thống kê hành vi được tính toán hoàn toàn từ dữ liệu on-chain phát sinh trong cửa sổ quan sát chuẩn hóa.

### 1.2 Cửa sổ quan sát hành vi sau triển khai (Post-Deployment Observation Window)
Để đảm bảo tính công bằng (fairness) giữa các hợp đồng có thời gian tồn tại khác nhau và triệt tiêu nguy cơ rò rỉ thông tin tương lai (Look-ahead Temporal Leakage), mọi đặc trưng hành vi được giới hạn nghiêm ngặt trong khoảng thời gian:
$$
\mathcal{W}(C) = \big[ T_{\text{creation}}(C), \; T_{\text{cutoff}}(C) \big)
$$
với:
$$
T_{\text{cutoff}}(C) = T_{\text{creation}}(C) + \Delta T, \quad \Delta T = 7 \text{ ngày} = 604.800 \text{ giây}
$$

### 1.3 Tập sự kiện hợp lệ (Valid Event Space)
Cho tập tất cả các bản ghi on-chain liên quan đến hợp đồng $C$ là $\mathcal{E}_{\text{all}}(C)$. Tập sự kiện đi vào tính toán View 1 được định nghĩa bởi:
$$
\mathcal{E}(C) = \big\{ e \in \mathcal{E}_{\text{all}}(C) \;\big|\; \text{target}(e) = C \;\land\; T_{\text{creation}}(C) \le \text{timestamp}(e) < T_{\text{cutoff}}(C) \big\}
$$
Các bản ghi có $\text{timestamp}(e) < T_{\text{creation}}(C)$ (tiền triển khai qua CREATE2/counterfactual address) được tách sang bảng kiểm toán riêng $\mathcal{E}_{\text{pre}}(C)$ và **không được đưa vào ma trận đặc trưng sau triển khai** $\mathbf{x}_C$.

---

## 2. Nguyên Tắc Phân Tách Tài Sản & Sự Kiện Blockchain

1. **Phân biệt Giao dịch (Transaction) và Sự kiện (Event):**
   - Một giao dịch Ethereum (`tx_hash`) có thể kích hoạt nhiều sự kiện nội bộ (`internal_trace`), sự kiện chuyển token (`erc20`, `erc721`).
   - `unique_tx_count` = số lượng mã băm `tx_hash` phân biệt.
   - `total_event_count` = tổng số dòng bản ghi sự kiện on-chain thu thập được.
2. **Nguyên tắc phân tách tài sản tuyệt đối (Asset Separation Invariant):**
   - Giá trị ETH (`value_eth`) chỉ được tính từ các giao dịch trực tiếp (`normal`) và giao dịch nội bộ (`internal`).
   - Số lượng token ERC-20 và ERC-721 (`value_raw`) **tuyệt đối không được cộng gộp vào giá trị ETH**, vì token có số chữ số thập phân (decimals) và tỷ giá hối đoái hoàn toàn khác biệt.
3. **Cô lập nhãn tuyệt đối (Label Isolation Invariant):**
   - Ma trận đặc trưng $\mathbf{X}$ tuyệt đối không chứa `label_status`, `label_source`, `first_seen_at`, `feature_cutoff_at`, `label_observed_at`.
   - Toàn bộ metadata nhãn được lưu trữ ở bảng riêng biệt để phục vụ Positive-Unlabeled (PU) Learning.

---

## 3. Bảng Danh Mục 32 Đặc Trưng Thống Kê View 1

| STT | Tên Đặc Trưng | Kiểu | Nhóm | Ý Nghĩa Kỹ Thuật |
| :---: | :--- | :---: | :---: | :--- |
| **1** | `tx_count_total` | `int` | Volume | Tổng số giao dịch thông thường (`tx_type == 'normal'`) |
| **2** | `tx_count_in` | `int` | Direction | Tổng số sự kiện nhận (`to_address == C`) |
| **3** | `tx_count_out` | `int` | Direction | Tổng số sự kiện gửi (`from_address == C`) |
| **4** | `tx_in_out_ratio` | `float` | Direction | Tỷ lệ nhận / gửi: `tx_count_in / max(tx_count_out, 1)` |
| **5** | `normal_tx_in` | `int` | Direction | Số giao dịch thông thường nhận |
| **6** | `normal_tx_out` | `int` | Direction | Số giao dịch thông thường gửi |
| **7** | `internal_tx_count` | `int` | Volume | Số giao dịch nội bộ (`tx_type == 'internal'`) |
| **8** | `erc20_transfer_count` | `int` | Volume | Số sự kiện chuyển token ERC-20 (`tx_type == 'erc20'`) |
| **9** | `erc721_transfer_count` | `int` | Volume | Số sự kiện chuyển NFT ERC-721 (`tx_type == 'erc721'`) |
| **10** | `total_event_count` | `int` | Volume | Tổng số bản ghi sự kiện on-chain hợp lệ trong 7 ngày |
| **11** | `unique_tx_count` | `int` | Volume | Số lượng mã băm giao dịch phân biệt (`COUNT(DISTINCT tx_hash)`) |
| **12** | `value_total_in_eth` | `float` | Value | Tổng lượng ETH nhận được (ETH) |
| **13** | `value_total_out_eth` | `float` | Value | Tổng lượng ETH gửi đi (ETH) |
| **14** | `value_net_eth` | `float` | Value | Biến động ròng ETH: `value_total_in_eth - value_total_out_eth` |
| **15** | `value_mean_in_eth` | `float` | Value | Giá trị ETH nhận trung bình mỗi sự kiện nhận |
| **16** | `value_std_in_eth` | `float` | Value | Độ lệch chuẩn giá trị ETH nhận |
| **17** | `value_max_in_eth` | `float` | Value | Giá trị ETH nhận lớn nhất trong 1 giao dịch |
| **18** | `unique_senders` | `int` | Network | Số địa chỉ đối tác gửi duy nhất tới $C$ |
| **19** | `unique_receivers` | `int` | Network | Số địa chỉ đối tác nhận duy nhất từ $C$ |
| **20** | `unique_counterparties_total` | `int` | Network | Tổng số đối tác phân biệt tương tác với $C$ |
| **21** | `unique_counterparty_ratio` | `float` | Network | Tỷ lệ đa dạng người gửi: `unique_senders / max(tx_count_in, 1)` |
| **22** | `top_sender_tx_ratio` | `float` | Network | Tỷ trọng giao dịch của đối tác gửi nhiều nhất |
| **23** | `lifespan_seconds` | `int` | Temporal | Khoảng cách thời gian từ sự kiện đầu đến sự kiện cuối (giây) |
| **24** | `active_days` | `int` | Temporal | Số ngày phân biệt có phát sinh hoạt động on-chain trong 7 ngày |
| **25** | `active_hours` | `int` | Temporal | Số giờ phân biệt có phát sinh hoạt động on-chain |
| **26** | `tx_frequency_per_hour` | `float` | Temporal | Tần suất giao dịch normal trên mỗi giờ hoạt động thực tế |
| **27** | `event_rate_7d` | `float` | Temporal | Tần suất sự kiện trung bình trên mỗi ngày trong cửa sổ chuẩn hóa |
| **28** | `gas_used_mean` | `float` | Execution | Lượng gas tiêu thụ trung bình (cho các giao dịch có gas hợp lệ) |
| **29** | `gas_used_total` | `float` | Execution | Tổng lượng gas tiêu thụ đã ghi nhận |
| **30** | `error_tx_count` | `int` | Execution | Số lượng giao dịch gặp lỗi thực thi (`is_error == 1`) |
| **31** | `error_tx_rate` | `float` | Execution | Tỷ lệ giao dịch lỗi: `error_tx_count / max(tx_count_total, 1)` |
| **32** | `method_diversity` | `int` | Execution | Số lượng hàm / phương thức phân biệt được gọi (`DISTINCT method_id`) |

---

## 4. Đặc Tả Chi Tiết Từng Nhóm Đặc Trưng

### Nhóm 1: Khối lượng và Cấu trúc Sự kiện (Event & Transaction Volume)

#### 1. `tx_count_total`
- **Công thức:**
  $$
  \text{tx\_count\_total} = \sum_{e \in \mathcal{E}(C)} \mathbb{I}\big(\text{type}(e) = \text{'normal'}\big)
  $$
- **Ý nghĩa:** Đo lường số lượng giao dịch cấp độ người dùng (EOA) tương tác trực tiếp với hợp đồng.
- **Dữ liệu nguồn:** Cột `tx_type == 'normal'`.
- **Xử lý zero:** Bằng 0 nếu không có giao dịch normal nào.

#### 2. `internal_tx_count`
- **Công thức:**
  $$
  \text{internal\_tx\_count} = \sum_{e \in \mathcal{E}(C)} \mathbb{I}\big(\text{type}(e) = \text{'internal'}\big)
  $$
- **Ý nghĩa:** Đo lường mức độ tương tác giữa hợp đồng với hợp đồng (Contract-to-Contract calls), phản ánh cấu trúc DeFi/Router hoặc dấu hiệu tạo lập qua factory `create2`.
- **Dữ liệu nguồn:** Cột `tx_type == 'internal'`.

#### 3. `erc20_transfer_count` & `erc721_transfer_count`
- **Công thức:**
  $$
  \text{erc20\_transfer\_count} = \sum_{e \in \mathcal{E}(C)} \mathbb{I}\big(\text{type}(e) = \text{'erc20'}\big)
  $$
  $$
  \text{erc721\_transfer\_count} = \sum_{e \in \mathcal{E}(C)} \mathbb{I}\big(\text{type}(e) = \text{'erc721'}\big)
  $$
- **Ý nghĩa:** Đo lường hoạt động luân chuyển tài sản token có thể thay thế (ERC-20) hoặc NFT (ERC-721).
- **Dữ liệu nguồn:** Cột `tx_type == 'erc20'` và `tx_type == 'erc721'`.

#### 4. `total_event_count` & `unique_tx_count`
- **Công thức:**
  $$
  \text{total\_event\_count} = |\mathcal{E}(C)|
  $$
  $$
  \text{unique\_tx\_count} = \big| \big\{ \text{hash}(e) \;\big|\; e \in \mathcal{E}(C) \big\} \big|
  $$
- **Ý nghĩa:** Đo lường sự phức tạp của các giao dịch on-chain. Nếu $\text{total\_event\_count} \gg \text{unique\_tx\_count}$, mỗi giao dịch chứa nhiều bước gọi nội bộ và chuyển token (đặc trưng của bot trading, arbitrage hoặc router phức tạp).

---

### Nhóm 2: Hướng Giao Dịch và Tỷ Lệ Dòng Chảy (Directional Flow & In/Out Ratios)

#### 5. `tx_count_in`, `tx_count_out`, `tx_in_out_ratio`
- **Công thức:**
  $$
  \text{tx\_count\_in} = \sum_{e \in \mathcal{E}(C)} \mathbb{I}\big(\text{to}(e) = C\big)
  $$
  $$
  \text{tx\_count\_out} = \sum_{e \in \mathcal{E}(C)} \mathbb{I}\big(\text{from}(e) = C\big)
  $$
  $$
  \text{tx\_in\_out\_ratio} = \frac{\text{tx\_count\_in}}{\max(\text{tx\_count\_out}, 1)}
  $$
- **Ý nghĩa:** Phản ánh tính chất "hố đen" (blackhole / honeypot) hay "bơm xả" (distributor). Hợp đồng phishing thường có tỷ lệ nhận áp đảo so với gửi.

---

### Nhóm 3: Giá Trị Kinh Tế ETH (ETH Monetary Dynamics)

#### 6. `value_total_in_eth`, `value_total_out_eth`, `value_net_eth`
- **Tập con ETH hợp lệ:** Chỉ các giao dịch native chuyển tiền thành công trên EVM (`is_error == 0`):
  $$
  \mathcal{E}_{\text{eth\_succ}}(C) = \{ e \in \mathcal{E}(C) \mid \text{type}(e) \in \{\text{'normal'}, \text{'internal'}\} \land \text{is\_error}(e) = 0 \}
  $$
- **Công thức:**
  $$
  \text{value\_total\_in\_eth} = \sum_{e \in \mathcal{E}_{\text{eth\_succ}}(C), \, \text{to}(e) = C} \text{value\_eth}(e)
  $$
  $$
  \text{value\_total\_out\_eth} = \sum_{e \in \mathcal{E}_{\text{eth\_succ}}(C), \, \text{from}(e) = C} \text{value\_eth}(e)
  $$
  $$
  \text{value\_net\_eth} = \text{value\_total\_in\_eth} - \text{value\_total\_out\_eth}
  $$
- **Ràng buộc:** Chỉ cộng giá trị ETH từ các giao dịch native thành công. Giao dịch revert (`is_error == 1`) bị EVM rollback state nên không làm thay đổi số dư thực tế. Tuyệt đối không quy đổi token ERC-20 thành ETH nếu chưa có oracle giá.

#### 7. `value_mean_in_eth`, `value_std_in_eth`, `value_max_in_eth`
- **Công thức:**
  $$
  \text{value\_mean\_in\_eth} = \frac{1}{|\mathcal{E}_{\text{in}}|} \sum_{e \in \mathcal{E}_{\text{in}}} \text{value\_eth}(e)
  $$
  $$
  \text{value\_std\_in\_eth} = \sqrt{\frac{1}{|\mathcal{E}_{\text{in}}| - 1} \sum_{e \in \mathcal{E}_{\text{in}}} \big(\text{value\_eth}(e) - \text{value\_mean\_in\_eth}\big)^2} \quad (\text{nếu } |\mathcal{E}_{\text{in}}| > 1, \text{ngược lại } 0)
  $$
  $$
  \text{value\_max\_in\_eth} = \max_{e \in \mathcal{E}_{\text{in}}} \text{value\_eth}(e)
  $$
  với $\mathcal{E}_{\text{in}} = \{ e \in \mathcal{E}_{\text{eth}}(C) \mid \text{to}(e) = C \}$.

---

### Nhóm 4: Mạng Lưới Đối Tác & Độ Tập Trung (Counterparty Network & Concentration)

#### 8. `unique_senders`, `unique_receivers`, `unique_counterparties_total`
- **Công thức:**
  $$
  \mathcal{S}(C) = \big\{ \text{from}(e) \;\big|\; e \in \mathcal{E}(C) \land \text{to}(e) = C \land \text{from}(e) \neq C \land \text{from}(e) \neq \emptyset \big\}
  $$
  $$
  \mathcal{R}(C) = \big\{ \text{to}(e) \;\big|\; e \in \mathcal{E}(C) \land \text{from}(e) = C \land \text{to}(e) \neq C \land \text{to}(e) \neq \emptyset \big\}
  $$
  $$
  \text{unique\_senders} = |\mathcal{S}(C)|, \quad \text{unique\_receivers} = |\mathcal{R}(C)|, \quad \text{unique\_counterparties\_total} = |\mathcal{S}(C) \cup \mathcal{R}(C)|
  $$

#### 9. `unique_counterparty_ratio` & `top_sender_tx_ratio`
- **Công thức:**
  $$
  \text{unique\_counterparty\_ratio} = \frac{\text{unique\_senders}}{\max(\text{tx\_count\_in}, 1)}
  $$
  $$
  \text{top\_sender\_tx\_ratio} = \frac{\max_{s \in \mathcal{S}(C)} \text{COUNT}(e \in \mathcal{E}_{\text{in}} \mid \text{from}(e) = s)}{\max(\text{tx\_count\_in}, 1)}
  $$
- **Ý nghĩa:** Đo lường sự phân tán hay tập trung của nguồn tiền gửi đến. Phishing lừa đảo quy mô lớn thường có nhiều nạn nhân gửi đến (tỷ số đa dạng cao), trong khi hợp đồng thử nghiệm cá nhân có độ tập trung 100% từ 1 địa chỉ duy nhất.

---

### Nhóm 5: Động Học Thời Gian (Temporal Dynamics & Frequency)

#### 10. `lifespan_seconds`, `active_days`, `active_hours`
- **Công thức:**
  $$
  \text{lifespan\_seconds} = \max_{e \in \mathcal{E}(C)} \text{timestamp}(e) - \min_{e \in \mathcal{E}(C)} \text{timestamp}(e) \quad (\text{nếu } |\mathcal{E}(C)| > 0, \text{ngược lại } 0)
  $$
  $$
  \text{active\_days} = \big| \big\{ \text{date}(\text{timestamp}(e)) \;\big|\; e \in \mathcal{E}(C) \big\} \big|
  $$
  $$
  \text{active\_hours} = \big| \big\{ \text{floor\_hour}(\text{timestamp}(e)) \;\big|\; e \in \mathcal{E}(C) \big\} \big|
  $$
- **Ý nghĩa:** Phản ánh chu kỳ sống on-chain của hợp đồng. Hợp đồng phishing thường "chớp nhoáng" (hoạt động chỉ trong vài giờ hoặc 1 ngày), khác với các giao thức duy trì hoạt động đều đặn qua các ngày.

#### 11. `tx_frequency_per_hour` & `event_rate_7d`
- **Công thức:**
  $$
  \text{lifespan\_hours} = \max\left(\frac{\text{lifespan\_seconds}}{3600.0}, 1.0\right)
  $$
  $$
  \text{tx\_frequency\_per_hour} = \frac{\text{tx\_count\_total}}{\text{lifespan\_hours}}
  $$
  $$
  \text{event\_rate\_7d} = \frac{\text{total\_event\_count}}{7.0}
  $$

---

### Nhóm 6: Thực Thi EVM, Gas & Phương Thức Gọi (EVM Execution, Gas & Interfaces)

#### 12. `gas_used_mean` & `gas_used_total`
- **Khử trùng lặp ở cấp độ Transaction:** Trong EVM, gas tiêu thụ được ghi nhận tại receipt của transaction. Một transaction đa sự kiện (multi-event) có thể phát sinh nhiều bản ghi (normal, internal, token) cùng chia sẻ gas. Để tránh double-counting, ta nhóm theo `tx_hash` và lấy giá trị lớn nhất:
  $$
  \text{tx\_gas}(h) = \max_{e \in \mathcal{E}(C), \, \text{hash}(e) = h, \, \text{gas\_used}(e) \ge 0} \text{gas\_used}(e)
  $$
- **Công thức:**
  $$
  \text{gas\_used\_total} = \sum_{h \in \mathcal{H}(C)} \text{tx\_gas}(h)
  $$
  $$
  \text{gas\_used\_mean} = \frac{1}{|\mathcal{H}(C)|} \sum_{h \in \mathcal{H}(C)} \text{tx\_gas}(h) \quad (\text{nếu } |\mathcal{H}(C)| > 0, \text{ngược lại } 0)
  $$
  với $\mathcal{H}(C)$ là tập các `tx_hash` duy nhất có gas hợp lệ trong $\mathcal{E}(C)$.

#### 13. `error_tx_count` & `error_tx_rate`
- **Công thức:**
  $$
  \text{error\_tx\_count} = \sum_{h \in \mathcal{H}_{\text{all}}(C)} \mathbb{I}\big(\exists e \in \mathcal{E}(C): \text{hash}(e) = h \land \text{is\_error}(e) = 1\big)
  $$
  $$
  \text{error\_tx\_rate} = \frac{\text{error\_tx\_count}}{\max(\text{unique\_tx\_count}, 1)}
  $$
- **Ý nghĩa:** Tỷ lệ giao dịch thất bại trên tổng số giao dịch duy nhất. Biến số này chuẩn hóa trong đoạn $[0, 1]$, phản ánh mức độ bất thường trong thực thi mã bytecode.

#### 14. `method_diversity`
- **Công thức:**
  $$
  \mathcal{M}(C) = \big\{ \text{method\_id}(e) \;\big|\; e \in \mathcal{E}(C) \land \text{len}(\text{method\_id}) \ge 10 \land \text{method\_id} \neq \text{'0x'} \land \text{method\_id} \neq \emptyset \big\}
  $$
  $$
  \text{method\_diversity} = |\mathcal{M}(C)|
  $$
- **Ý nghĩa:** Số hàm khác nhau được gọi vào hợp đồng. Hợp đồng phishing chuyên dụng thường chỉ có 1 hoặc 2 hàm (như `claim`, `transfer`, `multicall`), trong khi router và token hoàn chỉnh có giao diện phong phú hơn.

---

## 5. Danh Mục Các Đặc Trưng Chưa Đủ Thông Tin (`NOT_AVAILABLE`)

Theo nguyên tắc minh bạch khoa học của khóa luận, các đặc trưng được nêu trong tài liệu quy hoạch ban đầu (`docs/three_views_spec.md`) nhưng chưa được thu thập trong dữ liệu pilot được liệt kê minh bạch dưới đây:

| STT | Tên Đặc Trưng | Trạng Thái | Nguyên Nhân Chưa Khả Dụng | Kế Hoạch Bổ Sung |
| :---: | :--- | :---: | :--- | :--- |
| **1** | `bytecode_size` | `NOT_AVAILABLE` | 5 endpoint pilot Etherscan API (`txlist`, `txlistinternal`, `tokentx`, `tokennfttx`, `getcontractcreation`) không trả về runtime bytecode (`eth_getCode`). | Sẽ bổ sung endpoint `eth_getCode` khi mở rộng quy mô thu thập 400 địa chỉ. |
| **2** | `has_selfdestruct` | `NOT_AVAILABLE` | Cần phân tích opcode từ runtime bytecode để quét lệnh `0xFF` (`SELFDESTRUCT`). | Tích hợp sau khi tải bytecode hoàn chỉnh. |
| **3** | `deployer_tx_count`| `NOT_AVAILABLE` | Cần truy vấn toàn bộ lịch sử giao dịch của ví triển khai (`contractCreator`) trước thời điểm cutoff. | Sẽ thực hiện trong pipeline làm giàu dữ liệu deployer syndicate. |

> [!IMPORTANT]
> Toàn bộ các đặc trưng `NOT_AVAILABLE` **không được phép điền số 0 giả định** vào vector $\mathbf{x}_C$ vì việc gán giá trị 0 ngụy tạo sẽ làm sai lệch mô hình học máy. Chúng được giữ ngoài ma trận đặc trưng cho đến khi có dữ liệu xác thực.

---

## 6. Tính Bất Biến & Kiểm Tra Toàn Vẹn

1. **Tính xác định (Determinism):** Hàm `extract_view1_features` là hàm toán học thuần túy (pure function). Cho cùng tập đầu vào `(df_txs, df_addr)`, hàm đảm bảo cho ra kết quả đồng nhất 100% về mặt bitwise giữa các lần chạy độc lập.
2. **Không phụ thuộc vào nhãn (Unsupervised Feature Extraction):** Quá trình tính toán không sử dụng bất kỳ thông tin nhãn nào, bảo đảm áp dụng bình đẳng cho cả Positive và Unlabeled.
3. **Bảo toàn dữ liệu nguồn:** Quá trình trích xuất chỉ đọc (read-only), không chỉnh sửa bất kỳ tệp dữ liệu thô nào trong `data/raw` hay `data/pilot`.
