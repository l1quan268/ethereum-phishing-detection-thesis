#!/usr/bin/env python3
# File: src/view2/adapt_pilot.py
"""
Chuyen du lieu pilot da thu (schema cu cua src/collect_etherscan.py) sang schema giai doan A
de chay thu giai doan B ma khong can goi API.

Han che cua du lieu cu (ghi ro de khong nham la ket qua cuoi):
- Khong co transactionIndex, traceId -> order_uncertain co the = 1.
- Khong co creation tx hash -> suy ra tu su kien create/create2 (internal) hoac normal co `to` rong.
- File *_before_cutoff da cat theo T_creation + 7 ngay -> khong co su kien sau moc do.

  python -m src.view2.adapt_pilot
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "data/pilot/combined/pilot_20_transactions_before_cutoff.parquet"
META = ROOT / "data/processed/view1/view1_metadata_pilot.csv"
OUT = ROOT / "data/interim/view2_pilot"


def adapt(tx: pd.DataFrame, meta: pd.DataFrame):
    t = tx.copy()
    for c in ["target_address", "from_address", "to_address", "contract_address", "tx_hash"]:
        t[c] = t[c].fillna("").str.lower()
    is_create = ((t["tx_type"] == "internal") & t["function_name"].isin(["create", "create2"])) | \
                ((t["tx_type"] == "normal") & (t["to_address"] == ""))
    ev = pd.DataFrame({
        "target_address": t["target_address"],
        "source": t["tx_type"],
        "tx_hash": t["tx_hash"],
        "block_number": t["block_number"].astype("int64"),
        "timestamp": t["timestamp_unix"].astype("int64"),
        "tx_index": pd.array([pd.NA] * len(t), dtype="Int64"),
        "trace_id": None,
        "from_address": t["from_address"],
        "to_address": t["to_address"],
        "value_raw": t["value_raw"].fillna("0").astype(str),
        "token_address": t["contract_address"].where(t["tx_type"].isin(["erc20", "erc721"]), ""),
        "token_decimal": pd.array([pd.NA] * len(t), dtype="Int64"),
        "method_id": t["method_id"].fillna("").where(t["tx_type"] == "normal", ""),
        "function_name": t["function_name"].fillna(""),
        "call_type": t["function_name"].where(t["tx_type"] == "internal", ""),
        "is_error": t["is_error"].fillna(0).astype(int),
        "contract_created": t["target_address"].where(is_create, ""),
        "gas_used": t["gas_used"].where((t["tx_type"] == "normal") & (t["gas_used"] >= 0)).astype("Int64"),
        "in_sigmetrics_tx_log": t["in_sigmetrics_tx_log"].astype(bool),
    })
    ev = ev[ev["source"].isin(["normal", "internal", "erc20", "erc721"])]
    m = meta.assign(address=meta["address"].str.lower())
    ctx = ev[ev["contract_created"] != ""].groupby("target_address")["tx_hash"].first()
    creation = pd.DataFrame({
        "address": m["address"],
        "creation_tx": m["address"].map(ctx).fillna(""),
        "creator": "", "factory": "", "creation_block": -1,
        "creation_ts": m["creation_timestamp_unix"].astype("int64"),
        "creation_in_sigmetrics_tx_log": False,
    })
    return creation, ev


def main():
    creation, ev = adapt(pd.read_parquet(SRC), pd.read_csv(META))
    OUT.mkdir(parents=True, exist_ok=True)
    creation.to_parquet(OUT / "creation.parquet", index=False)
    ev.to_parquet(OUT / "events.parquet", index=False)
    print(f"[OK] {len(creation)} dia chi, {len(ev)} su kien -> {OUT}")


if __name__ == "__main__":
    main()