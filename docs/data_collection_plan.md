# Data Collection Plan — Pilot Phase

> **Goal:** Recover on-chain temporal & transactional data for a pilot of 100–300 phishing contracts + matched unlabeled contracts, before committing to full-scale collection.

---

## 1. Pilot Sampling Strategy

### 1.1 Phishing contracts (positive class)

Select **200 phishing contracts** from `phishing_contracts.log` using stratified sampling:

| Stratum | Count | Selection method | Rationale |
|---------|-------|-----------------|-----------|
| Head (first 50 sorted) | 50 | First 50 in file | Likely early-deployed (low hex = early CREATE2) |
| Tail (last 50 sorted) | 50 | Last 50 in file | Later deployments |
| Random middle | 100 | Uniform random from remaining | Representative sample |

```python
import random
random.seed(42)

with open("phishing_contracts.log") as f:
    contracts = [line.strip() for line in f if line.strip()]

head = contracts[:50]
tail = contracts[-50:]
middle = random.sample(contracts[50:-50], 100)
pilot_positive = head + tail + middle  # 200 contracts
```

### 1.2 Unlabeled contracts (NOT assumed benign)

> [!IMPORTANT]
> Unlabeled contracts are **not** labeled as benign. They are simply contracts that do not appear in the phishing list. We use them as the "unlabeled" class in a PU (Positive-Unlabeled) learning framework.

**Collection strategy:**
1. For each pilot phishing contract, recover its creation block number
2. Sample 1 contract deployed within ±50 blocks of the same block that is **not** in `phishing_contracts.log`
3. This yields ~200 unlabeled contracts from the same deployment period

**How to find same-period unlabeled contracts:**
```
For each phishing contract:
  1. Get creation tx → creation block B
  2. Query blocks [B-50, B+50] for contract creation txs
  3. Filter out addresses in phishing_contracts.log
  4. Pick one at random → unlabeled sample
```

---

## 2. On-chain Data Recovery Pipeline

### Phase A: Contract Metadata (must do first)

For each of the 400 pilot addresses:

| Data point | API call | Endpoint |
|------------|----------|----------|
| Creation tx hash | Etherscan `getcontractcreation` | `api.etherscan.io/api?module=contract&action=getcontractcreation&contractaddresses=<addr>` |
| Creation block + timestamp | `eth_getTransactionReceipt` → block → `eth_getBlockByNumber` | Alchemy/Infura JSON-RPC |
| Contract bytecode | `eth_getCode` | Alchemy/Infura JSON-RPC |
| Contract creator (deployer) | From creation tx `.from` field | Alchemy/Infura JSON-RPC |

**Estimated API calls for Phase A:** ~400 × 3 = **1,200 calls**

### Phase B: Transaction History

For each of the 400 pilot addresses:

| Data point | API call | Endpoint |
|------------|----------|----------|
| Normal transactions | Etherscan `txlist` | `module=account&action=txlist&address=<addr>&sort=asc` |
| Internal transactions | Etherscan `txlistinternal` | `module=account&action=txlistinternal&address=<addr>` |
| ERC-20 transfers | Etherscan `tokentx` | `module=account&action=tokentx&address=<addr>` |
| ERC-721 transfers | Etherscan `tokennfttx` | `module=account&action=tokennfttx&address=<addr>` |

**Estimated API calls for Phase B:** ~400 × 4 = **1,600 calls**

### Phase C: Neighbor Discovery (for ego-graph, View 3)

For each address that appears in Phase B transactions (1-hop neighbors):

| Data point | API call |
|------------|----------|
| Is contract or EOA? | `eth_getCode` (returns `0x` for EOA) |
| First tx timestamp | Etherscan `txlist` (1 result, sort=asc) |

**Estimated:** ~400 × 10 avg neighbors × 2 = **8,000 calls**

---

## 3. API Provider Comparison

| Provider | Free tier | Rate limit | Best for |
|----------|-----------|------------|----------|
| **Etherscan** | 5 calls/sec, no daily cap | 5/sec | Contract metadata, tx lists |
| **Alchemy** | 300M CU/month free | 330 CU/sec | JSON-RPC calls (eth_getCode, blocks) |
| **Infura** | 100k req/day free | ~10/sec | Backup JSON-RPC |
| **QuickNode** | 50M credits/month | Varies | Bulk archive queries |

### Cost estimate for pilot (400 addresses)

| Phase | Calls | Provider | Cost |
|-------|-------|----------|------|
| A: Metadata | 1,200 | Etherscan Free | $0 |
| B: Tx History | 1,600 | Etherscan Free | $0 |
| C: Neighbors | 8,000 | Etherscan Free | $0 |
| **Total** | **~10,800** | | **$0 (free tier)** |

> [!NOTE]
> At 5 calls/sec, 10,800 calls takes ~36 minutes. This is very feasible for a pilot.

### Cost estimate for full scale (37,654 addresses)

| Phase | Calls | Time at 5/sec | Cost |
|-------|-------|---------------|------|
| A | ~113K | ~6.3 hours | $0 (free tier) |
| B | ~150K | ~8.3 hours | $0 |
| C | ~3.7M (est.) | ~8.6 days | ⚠️ May need paid tier |
| **Total** | **~4M** | | **Etherscan Pro ($199/mo) recommended** |

---

## 4. Data Storage Schema

### 4.1 File structure

```
data/
├── pilot/
│   ├── addresses.csv              # 400 rows: address, label_status, ...
│   ├── contract_metadata.parquet  # creation info
│   ├── transactions/
│   │   ├── normal_txs.parquet
│   │   ├── internal_txs.parquet
│   │   ├── erc20_transfers.parquet
│   │   └── erc721_transfers.parquet
│   ├── neighbors/
│   │   └── neighbor_info.parquet
│   └── raw_api_responses/        # JSON cache for reproducibility
│       └── ...
└── full/                          # Same structure, populated after pilot validation
```

### 4.2 Key fields per table

**contract_metadata.parquet:**
```
address, creation_tx_hash, creation_block, creation_timestamp,
deployer_address, bytecode_hash, bytecode_size, has_selfdestruct
```

**normal_txs.parquet:**
```
tx_hash, block_number, timestamp, from_address, to_address,
value_wei, gas_used, is_error, method_id, contract_address
```

---

## 5. Execution Checklist

### Before starting (prerequisites):
- [ ] Create Etherscan API key (free registration)
- [ ] Create Alchemy API key (free tier)
- [ ] Install Python dependencies: `requests`, `web3`, `pandas`, `pyarrow`
- [ ] Verify at least 3 addresses manually on Etherscan to confirm format

### Pilot execution order:
1. [ ] Generate pilot sample (200 positive + 200 unlabeled)
2. [ ] **Phase A:** Recover contract creation timestamps (all 400)
3. [ ] **Validate:** Confirm creation timestamps fall within Dec 2022 – Jan 2025
4. [ ] **Phase B:** Download transaction histories
5. [ ] **Quality check:** Compare recovered tx hashes against `phishing_transactions.log`
6. [ ] **Phase C:** Discover and classify 1-hop neighbors
7. [ ] **Build address table:** Fill in `label_schema.csv` with recovered timestamps
8. [ ] **Analysis:** Compute View 1 (statistics) for pilot data
9. [ ] **Go/No-Go decision** for full-scale collection

### Go/No-Go criteria:
| Criterion | Threshold | Action if fail |
|-----------|-----------|----------------|
| % of addresses with valid creation time | ≥ 95% | Investigate failures, check if contracts self-destructed |
| Avg tx per contract | ≥ 3 | May need broader tx search |
| % recovered txs matching phishing_transactions.log | ≥ 80% | Re-examine tx-contract mapping strategy |
| API errors | < 5% | Switch providers or add retry logic |
| Free tier budget consumption | < 50% monthly limit | Proceed to full scale |

---

## 6. Timeline Estimate

| Step | Duration | Dependencies |
|------|----------|-------------|
| API key setup | 1 day | None |
| Write collection scripts | 2–3 days | API keys ready |
| Pilot Phase A (metadata) | 1 day | Scripts ready |
| Pilot Phase B (transactions) | 1 day | Phase A done |
| Pilot Phase C (neighbors) | 2 days | Phase B done |
| Quality analysis | 1–2 days | All phases done |
| **Total pilot** | **~8–10 days** | |
| Full-scale (if Go) | 2–3 weeks | Pilot validated |

---

## 7. What NOT To Do Yet

> [!CAUTION]
> - ❌ Do NOT start batch-collecting all 37,654 contracts before pilot validation
> - ❌ Do NOT train any GNN or classifier
> - ❌ Do NOT infer labels for unlabeled addresses
> - ❌ Do NOT use paid API tiers before verifying free tier sufficiency
> - ❌ Do NOT assume unlabeled = benign
