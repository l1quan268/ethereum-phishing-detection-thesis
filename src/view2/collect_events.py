#!/usr/bin/env python3
# File: src/view2/collect_events.py
"""
View 2 - Giai doan A: thu thap su kien on-chain cho tung dia chi hop dong.

Dau vao : mot hay nhieu CSV co cot `address` (vd. danh sach P lay tu phishing_contracts.log,
          danh sach U tu src/sample_unlabeled.py). Cot nhan (neu co) BI BO QUA o giai doan nay.
Dau ra  : data/interim/view2/
          creation.parquet          1 dong / dia chi: creation tx, creator, factory, block, timestamp
          events.parquet            bang dai, 1 dong / su kien tho (normal | internal | erc20 | erc721)
          collection_report.csv     trang thai thu thap tung dia chi

Quy tac:
- Khoang khoi lay = [0, block(T_creation + window)]. Bat dau tu 0 (khong phai block tao)
  vi dia chi CREATE2 co the nhan giao dich TRUOC khi hop dong ton tai.
  Moc observation_start / cutoff duoc tinh o giai doan B, khong o day.
- Mac dinh lay normal + internal (positive tao qua factory chi xuat hien trong internal).
  Token (erc20, erc721) la tuy chon.
- Giao dich chi co su kien internal/token khong co transactionIndex trong ket qua
  txlistinternal -> tra them eth_getTransactionByHash (tuy chon --resolve-tx-index).
- `in_sigmetrics_tx_log` chi de KIEM TRA, khong duoc dung lam dac trung (ro ri nhan).

Vi du:
  python -m src.view2.collect_events \
      --addresses data/pilot/combined/pilot_20_addresses.csv \
      --sources normal,internal,erc20 --window-days 7
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Dict, List, Set

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.view2.etherscan_client import EtherscanClient, EtherscanError  # noqa: E402

SOURCE_ACTION = {"normal": "txlist", "internal": "txlistinternal",
                 "erc20": "tokentx", "erc721": "tokennfttx"}

EVENT_COLUMNS = [
    "target_address", "source", "tx_hash", "block_number", "timestamp", "tx_index",
    "trace_id", "from_address", "to_address", "value_raw", "token_address", "token_decimal",
    "method_id", "function_name", "call_type", "is_error", "contract_created",
    "gas_used", "in_sigmetrics_tx_log",
]


def _lower(x) -> str:
    return (x or "").lower()


def _int_or_none(x):
    try:
        return int(x) if x not in (None, "") else None
    except (TypeError, ValueError):
        return None


def normalize_rows(target: str, source: str, rows: List[dict], sig_tx: Set[str]) -> List[dict]:
    """Chuan hoa ban ghi tho Etherscan ve schema EVENT_COLUMNS. Giu gia tri goc dang chuoi."""
    out = []
    for r in rows:
        h = _lower(r.get("hash"))
        inp = r.get("input") or ""
        if source == "normal":
            method_id = inp[:10].lower() if inp.startswith("0x") and len(inp) >= 10 else ""
        else:
            method_id = ""
        out.append({
            "target_address": target,
            "source": source,
            "tx_hash": h,
            "block_number": int(r.get("blockNumber")),
            "timestamp": int(r.get("timeStamp")),
            "tx_index": _int_or_none(r.get("transactionIndex")),
            "trace_id": r.get("traceId") if source == "internal" else None,
            "from_address": _lower(r.get("from")),
            "to_address": _lower(r.get("to")),
            "value_raw": str(r.get("value") or "0"),
            "token_address": _lower(r.get("contractAddress")) if source in ("erc20", "erc721") else "",
            "token_decimal": _int_or_none(r.get("tokenDecimal")) if source == "erc20" else None,
            "method_id": method_id,
            "function_name": r.get("functionName") or "",
            "call_type": (r.get("type") or "") if source == "internal" else "",
            "is_error": int(r.get("isError") or 0) if source in ("normal", "internal") else 0,
            "contract_created": _lower(r.get("contractAddress")) if source in ("normal", "internal") else "",
            "gas_used": _int_or_none(r.get("gasUsed")) if source == "normal" else None,
            "in_sigmetrics_tx_log": h in sig_tx,
        })
    return out


def load_addresses(paths: List[str]) -> List[str]:
    seen, out = set(), []
    for p in paths:
        df = pd.read_csv(p)
        for a in df["address"].astype(str).str.lower():
            if a not in seen:
                seen.add(a); out.append(a)
    return out


def load_sig_tx(path: Path) -> Set[str]:
    if not path.exists():
        print(f"[WARN] Khong thay {path}; in_sigmetrics_tx_log se = False")
        return set()
    return {l.strip().lower() for l in path.read_text(encoding="utf-8").splitlines() if l.strip()}


def collect(client: EtherscanClient, addresses: List[str], sources: List[str], window_days: int,
            sig_tx: Set[str], resolve_tx_index: bool, max_tx_index_lookups: int):
    window = window_days * 86400
    creation_rows, event_rows, report = [], [], []

    # 1) creation info, theo lo 5 dia chi
    created: Dict[str, dict] = {}
    for i in range(0, len(addresses), 5):
        batch = addresses[i:i + 5]
        try:
            for r in client.contract_creation(batch):
                created[_lower(r.get("contractAddress"))] = r
        except EtherscanError as ex:
            print(f"[ERROR] getcontractcreation {batch}: {ex}")

    lookups = 0
    for n, addr in enumerate(addresses, 1):
        rec = {"address": addr, "status": "ok", "saturated_ranges": "", "n_events": 0}
        c = created.get(addr)
        if not c or not c.get("timestamp"):
            rec["status"] = "no_creation_info"
            report.append(rec); print(f"[{n}/{len(addresses)}] {addr}: khong co creation info -> bo qua")
            continue
        c_ts, c_block = int(c["timestamp"]), int(c["blockNumber"])
        creation_rows.append({
            "address": addr, "creation_tx": _lower(c.get("txHash")), "creator": _lower(c.get("contractCreator")),
            "factory": _lower(c.get("contractFactory")), "creation_block": c_block, "creation_ts": c_ts,
            "creation_in_sigmetrics_tx_log": _lower(c.get("txHash")) in sig_tx,
        })
        try:
            end_block = client.block_by_time(c_ts + window, closest="before")
            rows_addr = []
            for s in sources:
                res = client.list_range(SOURCE_ACTION[s], addr, 0, end_block)
                if res["saturated_ranges"]:
                    rec["saturated_ranges"] += f"{s}:{res['saturated_ranges']};"
                rows_addr += normalize_rows(addr, s, res["rows"], sig_tx)
        except EtherscanError as ex:
            rec["status"] = f"error: {ex}"
            report.append(rec); print(f"[{n}/{len(addresses)}] {addr}: LOI {ex}")
            continue

        # 2) bo sung tx_index cho giao dich khong co (internal-only)
        if resolve_tx_index:
            known = {r["tx_hash"]: r["tx_index"] for r in rows_addr if r["tx_index"] is not None}
            for r in rows_addr:
                if r["tx_index"] is None:
                    if r["tx_hash"] not in known and lookups < max_tx_index_lookups:
                        tx = client.tx_by_hash(r["tx_hash"]); lookups += 1
                        known[r["tx_hash"]] = int(tx["transactionIndex"], 16) if tx and tx.get("transactionIndex") else None
                    r["tx_index"] = known.get(r["tx_hash"])

        event_rows += rows_addr
        rec["n_events"] = len(rows_addr)
        report.append(rec)
        print(f"[{n}/{len(addresses)}] {addr}: {len(rows_addr)} su kien (den block {end_block})")

    ev = pd.DataFrame(event_rows, columns=EVENT_COLUMNS)
    ev["tx_index"] = ev["tx_index"].astype("Int64")
    ev["token_decimal"] = ev["token_decimal"].astype("Int64")
    ev["gas_used"] = ev["gas_used"].astype("Int64")
    return pd.DataFrame(creation_rows), ev, pd.DataFrame(report)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--addresses", nargs="+", required=True, help="CSV co cot address (P va/hoac U)")
    ap.add_argument("--sources", default="normal,internal", help="normal,internal,erc20,erc721")
    ap.add_argument("--window-days", type=int, default=7)
    ap.add_argument("--sig-tx-log", default=str(ROOT / "data/raw/phishing_transactions.log"))
    ap.add_argument("--cache-dir", default=str(ROOT / "data/cache/view2"))
    ap.add_argument("--out-dir", default=str(ROOT / "data/interim/view2"))
    ap.add_argument("--rate-limit", type=float, default=2.0)
    ap.add_argument("--no-resolve-tx-index", action="store_true")
    ap.add_argument("--max-tx-index-lookups", type=int, default=100000)
    a = ap.parse_args()

    try:
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env")
    except ImportError:
        pass
    key = os.getenv("ETHERSCAN_API_KEY")
    if not key or key == "your_etherscan_api_key_here":
        sys.exit("[CRITICAL] Thieu ETHERSCAN_API_KEY trong .env")

    sources = [s.strip() for s in a.sources.split(",") if s.strip()]
    bad = set(sources) - set(SOURCE_ACTION)
    if bad:
        sys.exit(f"Nguon khong hop le: {bad}")
    if "internal" not in sources:
        print("[WARN] Khong lay 'internal': hop dong tao qua factory (CREATE2) se co chuoi rong.")

    client = EtherscanClient(key, Path(a.cache_dir), rate_limit=a.rate_limit)
    creation, events, report = collect(client, load_addresses(a.addresses), sources, a.window_days,
                                       load_sig_tx(Path(a.sig_tx_log)), not a.no_resolve_tx_index,
                                       a.max_tx_index_lookups)
    out = Path(a.out_dir); out.mkdir(parents=True, exist_ok=True)
    creation.to_parquet(out / "creation.parquet", index=False)
    events.to_parquet(out / "events.parquet", index=False)
    report.to_csv(out / "collection_report.csv", index=False)
    print(f"[OK] {len(creation)} dia chi, {len(events)} su kien -> {out}  "
          f"(goi mang: {client.n_network_calls}, cache: {client.n_cache_hits})")


if __name__ == "__main__":
    main()