#!/usr/bin/env python3
# File: src/collect_etherscan.py
"""
Pipeline thu thap du lieu giao dich Ethereum su dung Etherscan API V2.
Khoa luan tot nghiep: Learning Unified Graph Representations for Ethereum Phishing Detection
under Incomplete Labels and Temporal Shifts.

Thiet ke tuan thu nghiem ngat:
- Etherscan API V2 (chainid=1, Ethereum Mainnet)
- Bao mat tuyet doi: doc ETHERSCAN_API_KEY tu .env, khong log key
- Rate limiting <= 2 req/s (khoang cach >= 0.5s giua cac request)
- Retry co che exponential backoff khi gap 429 hoac rate limit message
- Cache raw JSON de ho tro resume va tranh lang phi quota API
- Khong gia mao du lieu: bao loi thuc te neu endpoint that bai
- Khong suy doan label_observed_at (giu null de tranh temporal leakage)
"""

import os
import sys
import time
import json
import random
import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

import requests
import pandas as pd
from dotenv import load_dotenv

# Reconfigure stdout to UTF-8 for Windows PowerShell support
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_CONTRACTS_FILE = PROJECT_ROOT / "data" / "raw" / "phishing_contracts.log"
DEFAULT_TXS_LOG_FILE = PROJECT_ROOT / "data" / "raw" / "phishing_transactions.log"
DEFAULT_CACHE_DIR = PROJECT_ROOT / "data" / "cache"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "pilot" / "positive"
DEFAULT_REPORT_DIR = PROJECT_ROOT / "reports" / "pilot"

ETHERSCAN_V2_URL = "https://api.etherscan.io/v2/api"


def resolve_path(path: Optional[str | Path], default: Path, base: Path = PROJECT_ROOT) -> Path:
    """Resolve relative path against project root or fallback to default."""
    if path is None:
        return default
    p = Path(path)
    return p if p.is_absolute() else (base / p).resolve()


def sanitize_url(url: str) -> str:
    """Mask apikey in url for safe logging."""
    import re
    return re.sub(r'apikey=[^&]+', 'apikey=***', url)


class RateLimiter:
    """Dam bao toc do goi API khong vuot qua max_rate (requests/second)."""
    def __init__(self, max_rate: float = 2.0):
        self.interval = 1.0 / max_rate if max_rate > 0 else 0.5
        self.last_call = 0.0

    def wait(self):
        elapsed = time.time() - self.last_call
        if elapsed < self.interval:
            time.sleep(self.interval - elapsed)
        self.last_call = time.time()


class EtherscanV2Collector:
    def __init__(
        self,
        api_key: str,
        cache_dir: Path,
        rate_limit: float = 2.0,
        timeout: int = 15,
        max_retries: int = 5,
        force_refresh: bool = False
    ):
        if not api_key:
            raise ValueError("ETHERSCAN_API_KEY khong duoc de trong!")
        self.api_key = api_key
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.limiter = RateLimiter(max_rate=rate_limit)
        self.timeout = timeout
        self.max_retries = max_retries
        self.force_refresh = force_refresh
        self.session = requests.Session()
        self.api_logs: List[Dict[str, Any]] = []

    def _get_cache_path(self, address: str, action: str, page: int = 1) -> Path:
        addr_dir = self.cache_dir / address.lower()
        addr_dir.mkdir(parents=True, exist_ok=True)
        return addr_dir / f"{action}_page{page}.json"

    def _query(self, address: str, module: str, action: str, extra_params: Dict[str, Any], page: int = 1) -> Tuple[Optional[Dict[str, Any]], bool]:
        """
        Gui yeu cau den Etherscan API V2 hoac doc tu cache.
        Tra ve (response_dict, cache_hit).
        """
        cache_file = self._get_cache_path(address, action, page)
        if not self.force_refresh and cache_file.exists():
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.api_logs.append({
                    "request_id": len(self.api_logs) + 1,
                    "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "address": address.lower(),
                    "endpoint_action": action,
                    "page": page,
                    "http_status": 200,
                    "api_status": str(data.get("status", "")),
                    "api_message": str(data.get("message", "")),
                    "result_count": len(data.get("result", [])) if isinstance(data.get("result"), list) else 0,
                    "duration_sec": 0.0,
                    "cache_hit": True,
                    "error_message": ""
                })
                return data, True
            except Exception as e:
                pass  # Neu cache hong thi query lai

        params = {
            "chainid": 1,
            "module": module,
            "action": action,
            "apikey": self.api_key
        }
        params.update(extra_params)

        attempt = 0
        backoff = 2.0
        while attempt < self.max_retries:
            attempt += 1
            self.limiter.wait()
            start_time = time.time()
            try:
                resp = self.session.get(ETHERSCAN_V2_URL, params=params, timeout=self.timeout)
                duration = round(time.time() - start_time, 3)
                http_status = resp.status_code

                if http_status in (429, 500, 502, 503, 504):
                    print(f"  [WARN] HTTP {http_status} for {action} on {address}. Retry {attempt}/{self.max_retries} sau {backoff}s...")
                    time.sleep(backoff + random.uniform(0.1, 0.5))
                    backoff *= 2
                    continue

                data = resp.json()
                api_status = str(data.get("status", ""))
                api_message = str(data.get("message", ""))
                result = data.get("result")

                # Kiem tra rate limit trong body cua Etherscan
                if api_status == "0" and isinstance(result, str) and ("rate limit" in result.lower() or "limit reached" in result.lower()):
                    print(f"  [WARN] Rate limit message tu Etherscan: '{result}'. Retry {attempt}/{self.max_retries} sau {backoff}s...")
                    time.sleep(backoff + random.uniform(0.2, 0.8))
                    backoff *= 2
                    continue

                # Luu vao cache
                with open(cache_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)

                self.api_logs.append({
                    "request_id": len(self.api_logs) + 1,
                    "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "address": address.lower(),
                    "endpoint_action": action,
                    "page": page,
                    "http_status": http_status,
                    "api_status": api_status,
                    "api_message": api_message,
                    "result_count": len(result) if isinstance(result, list) else 0,
                    "duration_sec": duration,
                    "cache_hit": False,
                    "error_message": "" if api_status == "1" or api_message == "No transactions found" else str(result)[:200]
                })
                return data, False

            except Exception as ex:
                duration = round(time.time() - start_time, 3)
                if attempt >= self.max_retries:
                    self.api_logs.append({
                        "request_id": len(self.api_logs) + 1,
                        "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "address": address.lower(),
                        "endpoint_action": action,
                        "page": page,
                        "http_status": 0,
                        "api_status": "ERR",
                        "api_message": "EXCEPTION",
                        "result_count": 0,
                        "duration_sec": duration,
                        "cache_hit": False,
                        "error_message": str(ex)[:200]
                    })
                    print(f"  [ERROR] Loi truy van sau {self.max_retries} lan: {ex}")
                    return None, False
                time.sleep(backoff)
                backoff *= 2

        return None, False

    def get_contract_creation(self, address: str) -> Optional[Dict[str, Any]]:
        """Lay thong tin contract creation qua getcontractcreation."""
        data, _ = self._query(
            address=address,
            module="contract",
            action="getcontractcreation",
            extra_params={"contractaddresses": address.lower()},
            page=1
        )
        if data and data.get("status") == "1":
            res = data.get("result", [])
            if isinstance(res, list) and len(res) > 0:
                return res[0]
        return None

    def get_paginated_transactions(self, address: str, action: str, offset: int = 1000) -> List[Dict[str, Any]]:
        """
        Lay toan bo danh sach giao dich co ho tro pagination.
        Cac action: txlist, txlistinternal, tokentx, tokennfttx.
        """
        all_txs: List[Dict[str, Any]] = []
        page = 1
        while True:
            params = {
                "address": address.lower(),
                "startblock": 0,
                "endblock": 99999999,
                "page": page,
                "offset": offset,
                "sort": "asc"
            }
            data, _ = self._query(
                address=address,
                module="account",
                action=action,
                extra_params=params,
                page=page
            )
            if not data:
                break
            api_status = str(data.get("status", ""))
            res = data.get("result", [])

            if api_status == "1" and isinstance(res, list):
                all_txs.extend(res)
                if len(res) < offset:
                    break
                page += 1
                if page > 10:  # Bao ve chong lap vo tan
                    print(f"  [INFO] Dat toi da 10 trang ({offset * 10} txs) cho {action} tai {address}")
                    break
            else:
                # status == '0' (No transactions found hoac loi)
                break
        return all_txs


def format_timestamp_utc(unix_ts: Any) -> Optional[str]:
    """Chuyen Unix timestamp thanh chuoi UTC ISO-8601 (YYYY-MM-DDTHH:MM:SSZ)."""
    if unix_ts is None:
        return None
    try:
        ts = int(unix_ts)
        if ts <= 0:
            return None
        return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except (ValueError, TypeError):
        return None


def run_pilot_pipeline(
    limit: int = 10,
    seed: int = 42,
    rate_limit: float = 2.0,
    cache_dir: Optional[str | Path] = None,
    output_dir: Optional[str | Path] = None,
    report_dir: Optional[str | Path] = None,
    contracts_file: Optional[str | Path] = None,
    txs_log_file: Optional[str | Path] = None,
    force_refresh: bool = False
):
    print("=" * 70)
    print("ETHEREUM PHISHING DETECTION — PILOT DATA COLLECTION (ETHERSCAN V2)")
    print("=" * 70)

    # Resolve paths relative to PROJECT_ROOT
    contracts_path = resolve_path(contracts_file, DEFAULT_CONTRACTS_FILE)
    txs_path = resolve_path(txs_log_file, DEFAULT_TXS_LOG_FILE)
    cache_path = resolve_path(cache_dir, DEFAULT_CACHE_DIR)
    out_path = resolve_path(output_dir, DEFAULT_OUTPUT_DIR)
    rep_path = resolve_path(report_dir, DEFAULT_REPORT_DIR)

    # 1. Kiem tra va doc .env
    env_file = PROJECT_ROOT / ".env"
    load_dotenv(env_file)
    api_key = os.getenv("ETHERSCAN_API_KEY")
    if not api_key:
        print("[CRITICAL] Khong tim thay ETHERSCAN_API_KEY trong file .env!")
        print("Vui long tao file .env voi noi dung: ETHERSCAN_API_KEY=your_key_here")
        sys.exit(1)
    print(f"[OK] Da tai ETHERSCAN_API_KEY (chieu dai: {len(api_key)} ky tu). Khong hien thi khoa.")

    # 2. Doc danh sach phishing_contracts.log
    if not contracts_path.exists():
        print(f"[CRITICAL] Khong tim thay {contracts_path}!")
        sys.exit(1)

    with open(contracts_path, "r", encoding="utf-8") as f:
        all_contracts = [line.strip().lower() for line in f if line.strip()]

    print(f"[OK] Tong so hop dong trong {contracts_path.name}: {len(all_contracts):,}")

    # 3. Chon 10 dia chi ngau nhien bang seed co dinh
    random.seed(seed)
    selected_addresses = random.sample(all_contracts, limit)
    print(f"[OK] Da chon {limit} dia chi ngau nhien voi random seed = {seed}:")
    for idx, addr in enumerate(selected_addresses, 1):
        print(f"  {idx:2d}. {addr}")

    # 4. Doc phishing_transactions.log de cross-check
    sigmetrics_tx_set = set()
    if txs_path.exists():
        with open(txs_path, "r", encoding="utf-8") as f:
            sigmetrics_tx_set = set(line.strip().lower() for line in f if line.strip())
        print(f"[OK] Da tai {len(sigmetrics_tx_set):,} tx hashes tu {txs_path.name} de doi chieu.")

    # 5. Khoi tao collector
    collector = EtherscanV2Collector(
        api_key=api_key,
        cache_dir=cache_path,
        rate_limit=rate_limit,
        force_refresh=force_refresh
    )

    address_records = []
    timestamp_report_records = []
    all_normalized_transactions: List[Dict[str, Any]] = []

    out_path.mkdir(parents=True, exist_ok=True)
    rep_path.mkdir(parents=True, exist_ok=True)

    print("\n" + "-" * 70)
    print(f"BAT DAU TRUY VAN {len(selected_addresses)} DIA CHI QUA ETHERSCAN API V2 (MAINNET chainid=1)...")
    print("-" * 70)

    for i, address in enumerate(selected_addresses, 1):
        print(f"\n[{i}/{len(selected_addresses)}] Xu ly dia chi: {address}")
        
        # A. Contract Creation
        creation_data = collector.get_contract_creation(address)
        has_creation = creation_data is not None

        creation_tx = creation_data.get("txHash") if has_creation else None
        creator = creation_data.get("contractCreator") if has_creation else None
        factory = creation_data.get("contractFactory") if has_creation else None
        creation_block = int(creation_data.get("blockNumber")) if (has_creation and creation_data.get("blockNumber")) else None
        creation_ts = int(creation_data.get("timestamp")) if (has_creation and creation_data.get("timestamp")) else None
        creation_utc = format_timestamp_utc(creation_ts)

        if has_creation:
            print(f"  + Creation Block: {creation_block:,} | UTC: {creation_utc} | Creator: {creator}")
            print(f"  + Creation Tx: {creation_tx}")
        else:
            print("  ! [WARN] Khong lay duoc contract creation tu Etherscan getcontractcreation")

        # B. Normal Transactions (txlist)
        normal_txs = collector.get_paginated_transactions(address, "txlist")
        print(f"  + Normal Transactions (txlist): {len(normal_txs)}")

        # C. Internal Transactions (txlistinternal)
        internal_txs = collector.get_paginated_transactions(address, "txlistinternal")
        print(f"  + Internal Transactions (txlistinternal): {len(internal_txs)}")

        # D. ERC-20 Token Transfers (tokentx)
        token_txs = collector.get_paginated_transactions(address, "tokentx")
        print(f"  + ERC-20 Transfers (tokentx): {len(token_txs)}")

        # E. ERC-721 Token Transfers (tokennfttx)
        nft_txs = collector.get_paginated_transactions(address, "tokennfttx")
        print(f"  + ERC-721 Transfers (tokennfttx): {len(nft_txs)}")

        # Tong hop giao dich cho dia chi nay
        addr_tx_timestamps: List[int] = []
        if creation_ts:
            addr_tx_timestamps.append(creation_ts)

        # Chuyen doi normal txs
        for tx in normal_txs:
            ts = int(tx.get("timeStamp", 0))
            if ts > 0:
                addr_tx_timestamps.append(ts)
            h = (tx.get("hash") or "").lower()
            val_eth = float(tx.get("value", 0)) / 1e18 if tx.get("value") else 0.0
            all_normalized_transactions.append({
                "tx_hash": h,
                "block_number": int(tx.get("blockNumber", 0)),
                "timestamp_unix": ts,
                "timestamp_utc": format_timestamp_utc(ts),
                "target_address": address,
                "tx_type": "normal",
                "from_address": (tx.get("from") or "").lower(),
                "to_address": (tx.get("to") or "").lower(),
                "value_eth": val_eth,
                "value_raw": str(tx.get("value", "")),
                "gas_used": int(tx.get("gasUsed", -1)),
                "gas_price_gwei": float(tx.get("gasPrice", 0)) / 1e9 if tx.get("gasPrice") else -1.0,
                "is_error": int(tx.get("isError", 0)),
                "method_id": tx.get("methodId", ""),
                "function_name": tx.get("functionName", ""),
                "contract_address": (tx.get("contractAddress") or "").lower(),
                "token_symbol": "",
                "in_sigmetrics_tx_log": h in sigmetrics_tx_set,
                "api_source": "etherscan_v2"
            })

        # Chuyen doi internal txs
        for tx in internal_txs:
            ts = int(tx.get("timeStamp", 0))
            if ts > 0:
                addr_tx_timestamps.append(ts)
            h = (tx.get("hash") or "").lower()
            val_eth = float(tx.get("value", 0)) / 1e18 if tx.get("value") else 0.0
            all_normalized_transactions.append({
                "tx_hash": h,
                "block_number": int(tx.get("blockNumber", 0)),
                "timestamp_unix": ts,
                "timestamp_utc": format_timestamp_utc(ts),
                "target_address": address,
                "tx_type": "internal",
                "from_address": (tx.get("from") or "").lower(),
                "to_address": (tx.get("to") or "").lower(),
                "value_eth": val_eth,
                "value_raw": str(tx.get("value", "")),
                "gas_used": int(tx.get("gasUsed", -1)),
                "gas_price_gwei": -1.0,
                "is_error": int(tx.get("isError", 0)),
                "method_id": "",
                "function_name": tx.get("type", ""),  # create2, call, etc.
                "contract_address": (tx.get("contractAddress") or "").lower(),
                "token_symbol": "",
                "in_sigmetrics_tx_log": h in sigmetrics_tx_set,
                "api_source": "etherscan_v2"
            })

        # Chuyen doi token ERC-20 txs
        for tx in token_txs:
            ts = int(tx.get("timeStamp", 0))
            if ts > 0:
                addr_tx_timestamps.append(ts)
            h = (tx.get("hash") or "").lower()
            all_normalized_transactions.append({
                "tx_hash": h,
                "block_number": int(tx.get("blockNumber", 0)),
                "timestamp_unix": ts,
                "timestamp_utc": format_timestamp_utc(ts),
                "target_address": address,
                "tx_type": "erc20",
                "from_address": (tx.get("from") or "").lower(),
                "to_address": (tx.get("to") or "").lower(),
                "value_eth": 0.0,
                "value_raw": str(tx.get("value", "")),
                "gas_used": int(tx.get("gasUsed", -1)),
                "gas_price_gwei": float(tx.get("gasPrice", 0)) / 1e9 if tx.get("gasPrice") else -1.0,
                "is_error": 0,
                "method_id": tx.get("methodId", ""),
                "function_name": tx.get("functionName", ""),
                "contract_address": (tx.get("contractAddress") or "").lower(),
                "token_symbol": tx.get("tokenSymbol", ""),
                "in_sigmetrics_tx_log": h in sigmetrics_tx_set,
                "api_source": "etherscan_v2"
            })

        # Chuyen doi NFT ERC-721 txs
        for tx in nft_txs:
            ts = int(tx.get("timeStamp", 0))
            if ts > 0:
                addr_tx_timestamps.append(ts)
            h = (tx.get("hash") or "").lower()
            all_normalized_transactions.append({
                "tx_hash": h,
                "block_number": int(tx.get("blockNumber", 0)),
                "timestamp_unix": ts,
                "timestamp_utc": format_timestamp_utc(ts),
                "target_address": address,
                "tx_type": "erc721",
                "from_address": (tx.get("from") or "").lower(),
                "to_address": (tx.get("to") or "").lower(),
                "value_eth": 0.0,
                "value_raw": str(tx.get("tokenID", "")),
                "gas_used": int(tx.get("gasUsed", -1)),
                "gas_price_gwei": float(tx.get("gasPrice", 0)) / 1e9 if tx.get("gasPrice") else -1.0,
                "is_error": 0,
                "method_id": tx.get("methodId", ""),
                "function_name": tx.get("functionName", ""),
                "contract_address": (tx.get("contractAddress") or "").lower(),
                "token_symbol": tx.get("tokenSymbol", ""),
                "in_sigmetrics_tx_log": h in sigmetrics_tx_set,
                "api_source": "etherscan_v2"
            })

        # Cung cap ban ghi creation tx neu chua co trong danh sach
        if creation_tx and not any(t["tx_hash"] == creation_tx.lower() for t in all_normalized_transactions if t["target_address"] == address):
            all_normalized_transactions.append({
                "tx_hash": creation_tx.lower(),
                "block_number": creation_block if creation_block else -1,
                "timestamp_unix": creation_ts if creation_ts else -1,
                "timestamp_utc": creation_utc,
                "target_address": address,
                "tx_type": "creation",
                "from_address": (creator or "").lower(),
                "to_address": (factory or "").lower(),
                "value_eth": 0.0,
                "value_raw": "0",
                "gas_used": -1,
                "gas_price_gwei": -1.0,
                "is_error": 0,
                "method_id": "",
                "function_name": "contract_creation",
                "contract_address": address,
                "token_symbol": "",
                "in_sigmetrics_tx_log": creation_tx.lower() in sigmetrics_tx_set,
                "api_source": "etherscan_v2"
            })

        # Tinh toan thoi gian
        earliest_ts = min(addr_tx_timestamps) if addr_tx_timestamps else None
        latest_ts = max(addr_tx_timestamps) if addr_tx_timestamps else None
        lifespan = (latest_ts - earliest_ts) if (earliest_ts and latest_ts) else 0

        # Tinh so luong tx trung voi SIGMETRICS
        addr_tx_hashes = {t["tx_hash"] for t in all_normalized_transactions if t["target_address"] == address}
        match_sigmetrics_count = sum(1 for h in addr_tx_hashes if h in sigmetrics_tx_set)

        total_txs_this_addr = len(normal_txs) + len(internal_txs) + len(token_txs) + len(nft_txs)

        timestamp_report_records.append({
            "address": address,
            "contract_creator": creator,
            "creation_tx_hash": creation_tx,
            "creation_block": creation_block,
            "creation_timestamp_unix": creation_ts,
            "creation_timestamp_utc": creation_utc,
            "earliest_tx_timestamp_unix": earliest_ts,
            "earliest_tx_timestamp_utc": format_timestamp_utc(earliest_ts),
            "latest_tx_timestamp_unix": latest_ts,
            "latest_tx_timestamp_utc": format_timestamp_utc(latest_ts),
            "tx_count_normal": len(normal_txs),
            "tx_count_internal": len(internal_txs),
            "tx_count_erc20": len(token_txs),
            "tx_count_erc721": len(nft_txs),
            "tx_count_total": total_txs_this_addr,
            "lifespan_seconds": lifespan,
            "matches_sigmetrics_tx_log_count": match_sigmetrics_count,
            "status": "SUCCESS" if has_creation else "PARTIAL_NO_CREATION"
        })

        # Bang pilot_addresses.csv theo chuan label_schema.csv
        # address,label_status,first_seen_at,feature_cutoff_at,label_observed_at,label_source
        address_records.append({
            "address": address,
            "label_status": "positive",
            "first_seen_at": creation_utc if creation_utc else (format_timestamp_utc(earliest_ts) if earliest_ts else "null"),
            "feature_cutoff_at": "null",
            "label_observed_at": "null",
            "label_source": "sigmetrics25_phishing_contracts"
        })

    # =========================================================================
    # XUAT FILE KET QUA
    # =========================================================================
    print("\n" + "=" * 70)
    print("XUAT CAC TEP TIN KET QUA...")
    print("=" * 70)

    # 1. pilot_addresses.csv
    df_addr = pd.DataFrame(address_records)
    addr_file = out_path / "pilot_addresses.csv"
    df_addr.to_csv(addr_file, index=False)
    print(f"[OK] Da luu pilot_addresses.csv ({len(df_addr)} dong) -> {addr_file}")

    # 2. pilot_timestamp_report.csv
    df_ts = pd.DataFrame(timestamp_report_records)
    ts_file = rep_path / "pilot_timestamp_report.csv"
    df_ts.to_csv(ts_file, index=False)
    print(f"[OK] Da luu pilot_timestamp_report.csv ({len(df_ts)} dong) -> {ts_file}")

    # 3. pilot_transactions.parquet
    df_txs = pd.DataFrame(all_normalized_transactions)
    parquet_file = out_path / "pilot_transactions.parquet"
    if not df_txs.empty:
        # Loai bo trung lap hash cung loai tren cung target_address neu co
        df_txs = df_txs.drop_duplicates(subset=["tx_hash", "target_address", "tx_type"])
        df_txs.to_parquet(parquet_file, index=False, engine="pyarrow")
        print(f"[OK] Da luu pilot_transactions.parquet ({len(df_txs)} giao dich) -> {parquet_file}")
    else:
        # Tao file parquet rong voi schema dung
        schema_df = pd.DataFrame(columns=[
            "tx_hash", "block_number", "timestamp_unix", "timestamp_utc", "target_address",
            "tx_type", "from_address", "to_address", "value_eth", "value_raw", "gas_used",
            "gas_price_gwei", "is_error", "method_id", "function_name", "contract_address",
            "token_symbol", "in_sigmetrics_tx_log", "api_source"
        ])
        schema_df.to_parquet(parquet_file, index=False, engine="pyarrow")
        print(f"[OK] Da luu pilot_transactions.parquet (0 giao dich) -> {parquet_file}")

    # 4. api_collection_log.csv
    df_log = pd.DataFrame(collector.api_logs)
    log_file = rep_path / "api_collection_log.csv"
    df_log.to_csv(log_file, index=False)
    print(f"[OK] Da luu api_collection_log.csv ({len(df_log)} request logs) -> {log_file}")

    print("\n" + "=" * 70)
    print("HOAN THANH PILOT DATA COLLECTION!")
    print("=" * 70)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Thu thap giao dich Ethereum qua Etherscan API V2")
    parser.add_argument("--limit", type=int, default=10, help="So dia chi can thu thap (mac dinh: 10)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed (mac dinh: 42)")
    parser.add_argument("--rate-limit", type=float, default=2.0, help="Gioi han request/giay (mac dinh: 2.0)")
    parser.add_argument("--cache-dir", type=str, default="data/cache", help="Thu muc luu cache JSON (mac dinh: data/cache)")
    parser.add_argument("--output-dir", type=str, default="data/pilot/positive", help="Thu muc xuat dataset (mac dinh: data/pilot/positive)")
    parser.add_argument("--report-dir", type=str, default="reports/pilot", help="Thu muc xuat bao cao (mac dinh: reports/pilot)")
    parser.add_argument("--contracts-file", type=str, default="data/raw/phishing_contracts.log", help="Duong dan phishing_contracts.log")
    parser.add_argument("--txs-log-file", type=str, default="data/raw/phishing_transactions.log", help="Duong dan phishing_transactions.log")
    parser.add_argument("--force-refresh", action="store_true", help="Bo qua cache va tai lai moi")
    args = parser.parse_args()

    run_pilot_pipeline(
        limit=args.limit,
        seed=args.seed,
        rate_limit=args.rate_limit,
        cache_dir=args.cache_dir,
        output_dir=args.output_dir,
        report_dir=args.report_dir,
        contracts_file=args.contracts_file,
        txs_log_file=args.txs_log_file,
        force_refresh=args.force_refresh
    )
