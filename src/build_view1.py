#!/usr/bin/env python3
# File: src/build_view1.py
"""
Pipeline Trich Xuat Dac Trung View 1 (Statistical Features) cho Ethereum Smart Contracts.
Phuc vu Khoa Luan Tot Nghiep:
"Learning Unified Graph Representations for Ethereum Phishing Detection under Incomplete Labels and Temporal Shifts"

Nguyen tac thiet ke nghiem ngat:
1. Don vi du doan: 1 dong feature cho moi hop dong tai moc point-in-time cutoff.
2. Pham vi thoi gian: T_creation <= T_tx < T_cutoff (voi T_cutoff = T_creation + 7 ngay).
3. Phan biet ro Transaction vs Event:
   - Unique tx_hash vs normal tx vs internal trace vs token transfers (ERC-20/721).
4. Khong cong gia tri ETH voi token balance (tach rieng don vi va metadata).
5. Co lap tuyet doi Nhan (Label Isolation):
   - Vector X chi chua cac dac trung so hoc on-chain.
   - Metadata va thong tin nhan (label_status, label_source, timestamps) luu o bang rieng.
6. Xuat dinh dang ca Parquet va CSV cho ML/GNN pipelines.
"""

import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional

import numpy as np
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_COMBINED_ADDRESSES = PROJECT_ROOT / "data" / "pilot" / "combined" / "pilot_20_addresses.csv"
DEFAULT_COMBINED_TRANSACTIONS = PROJECT_ROOT / "data" / "pilot" / "combined" / "pilot_20_transactions_before_cutoff.parquet"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "processed" / "view1"


def parse_iso_timestamp(iso_str: str) -> int:
    """Chuyen doi chuoi ISO-8601 UTC sang Unix timestamp (giay)."""
    if pd.isna(iso_str) or not isinstance(iso_str, str):
        return 0
    dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
    return int(dt.timestamp())


def audit_pre_creation_transactions(
    df_txs: pd.DataFrame,
    df_addr: pd.DataFrame
) -> pd.DataFrame:
    """
    Xac dinh va kiem toan cac ban ghi co thoi gian truoc creation_timestamp.
    Dieu kien: T_tx < T_creation.
    """
    addr_map = {}
    for _, r in df_addr.iterrows():
        addr = r["address"].lower()
        c_ts = parse_iso_timestamp(r["first_seen_at"])
        addr_map[addr] = {
            "creation_timestamp_unix": c_ts,
            "creation_utc": r["first_seen_at"],
            "label_status": r.get("label_status", "unknown")
        }

    pre_records = []
    for _, tx in df_txs.iterrows():
        tgt = tx["target_address"].lower()
        if tgt not in addr_map:
            continue
        c_ts = addr_map[tgt]["creation_timestamp_unix"]
        tx_ts = int(tx["timestamp_unix"])
        if tx_ts < c_ts:
            delta_sec = tx_ts - c_ts
            pre_records.append({
                "target_address": tgt,
                "label_status": addr_map[tgt]["label_status"],
                "tx_hash": tx["tx_hash"],
                "tx_type": tx["tx_type"],
                "api_source": tx["api_source"],
                "block_number": int(tx["block_number"]),
                "timestamp_unix": tx_ts,
                "timestamp_utc": tx["timestamp_utc"],
                "creation_timestamp_unix": c_ts,
                "creation_timestamp_utc": addr_map[tgt]["creation_utc"],
                "delta_seconds": delta_sec,
                "from_address": tx["from_address"],
                "to_address": tx["to_address"],
                "value_eth": float(tx["value_eth"]),
                "value_raw": str(tx["value_raw"]),
                "gas_used": int(tx["gas_used"]),
                "gas_price_gwei": float(tx["gas_price_gwei"]),
                "is_error": int(tx["is_error"]),
                "method_id": tx["method_id"],
                "function_name": tx["function_name"],
                "contract_address": tx["contract_address"],
                "token_symbol": tx["token_symbol"]
            })

    return pd.DataFrame(pre_records)


def extract_view1_features(
    df_txs: pd.DataFrame,
    df_addr: pd.DataFrame
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Trich xuat dac trung thong ke View 1 cho moi hop dong tai thoi diem cutoff.
    
    Tra ve:
    1. df_features: DataFrame chua 'address' va cac dac trung so hoc (khong co label).
    2. df_metadata: DataFrame co lap luu metadata va label (label_status, label_source, timestamps).
    3. df_precreation_audit: DataFrame kiem toan cac ban ghi truoc creation.
    """
    df_precreation_audit = audit_pre_creation_transactions(df_txs, df_addr)

    feature_rows: List[Dict[str, Any]] = []
    metadata_rows: List[Dict[str, Any]] = []

    for _, r in df_addr.iterrows():
        addr = r["address"].lower()
        c_ts = parse_iso_timestamp(r["first_seen_at"])
        cut_ts = parse_iso_timestamp(r["feature_cutoff_at"])
        lbl_status = r["label_status"]
        lbl_source = r.get("label_source", "")

        # 1. Metadata co lap hoan toan khoi feature vector
        metadata_rows.append({
            "address": addr,
            "label_status": lbl_status,
            "label_source": lbl_source,
            "first_seen_at": r["first_seen_at"],
            "feature_cutoff_at": r["feature_cutoff_at"],
            "creation_timestamp_unix": c_ts,
            "cutoff_timestamp_unix": cut_ts,
            "label_observed_at": r.get("label_observed_at", "null")
        })

        # 2. Loc nghiem ngat tap du lieu sau trien khai: T_creation <= T_tx < T_cutoff
        sub = df_txs[
            (df_txs["target_address"].str.lower() == addr) &
            (df_txs["timestamp_unix"] >= c_ts) &
            (df_txs["timestamp_unix"] < cut_ts)
        ]

        # Phan nhom theo loai giao dich / su kien
        normal_sub = sub[sub["tx_type"] == "normal"]
        internal_sub = sub[sub["tx_type"] == "internal"]
        erc20_sub = sub[sub["tx_type"] == "erc20"]
        erc721_sub = sub[sub["tx_type"] == "erc721"]

        # Nhom 1: So luong giao dich va su kien
        tx_count_total = int(len(normal_sub))
        internal_tx_count = int(len(internal_sub))
        erc20_transfer_count = int(len(erc20_sub))
        erc721_transfer_count = int(len(erc721_sub))
        total_event_count = int(len(sub))
        unique_tx_count = int(sub["tx_hash"].nunique()) if len(sub) > 0 else 0

        # Nhom 2: Huong giao dich va su kien (In / Out)
        # Target address la nguoi nhan (in) hoac nguoi gui (out)
        in_events = sub[sub["to_address"].str.lower() == addr]
        out_events = sub[sub["from_address"].str.lower() == addr]
        tx_count_in = int(len(in_events))
        tx_count_out = int(len(out_events))

        normal_tx_in = int(len(normal_sub[normal_sub["to_address"].str.lower() == addr]))
        normal_tx_out = int(len(normal_sub[normal_sub["from_address"].str.lower() == addr]))

        # Nhom 3: Ty le in / out
        tx_in_out_ratio = float(tx_count_in) / float(max(tx_count_out, 1))

        # Nhom 4: Gia tri ETH (Chi tinh tu normal va internal co is_error == 0, TUYET DOI KHONG CONG TOKEN)
        # Theo ngu nghia EVM, giao dich revert (is_error == 1) thi state change bi rollback,
        # ETH khong thuc su duoc chuyen giao tren chuoi.
        successful_eth_events = sub[(sub["tx_type"].isin(["normal", "internal"])) & (sub["is_error"] == 0)]
        eth_in = successful_eth_events[successful_eth_events["to_address"].str.lower() == addr]
        eth_out = successful_eth_events[successful_eth_events["from_address"].str.lower() == addr]

        value_total_in_eth = float(eth_in["value_eth"].sum()) if len(eth_in) > 0 else 0.0
        value_total_out_eth = float(eth_out["value_eth"].sum()) if len(eth_out) > 0 else 0.0
        value_net_eth = float(value_total_in_eth - value_total_out_eth)
        value_mean_in_eth = float(eth_in["value_eth"].mean()) if len(eth_in) > 0 else 0.0
        value_std_in_eth = float(eth_in["value_eth"].std(ddof=1)) if len(eth_in) > 1 else 0.0
        if np.isnan(value_std_in_eth):
            value_std_in_eth = 0.0
        value_max_in_eth = float(eth_in["value_eth"].max()) if len(eth_in) > 0 else 0.0

        # Nhom 5: Doi tac duy nhat (Counterparties)
        raw_senders = set(in_events["from_address"].str.lower().unique())
        raw_receivers = set(out_events["to_address"].str.lower().unique())
        raw_senders.discard(addr)
        raw_senders.discard("")
        raw_receivers.discard(addr)
        raw_receivers.discard("")

        unique_senders = int(len(raw_senders))
        unique_receivers = int(len(raw_receivers))
        unique_counterparties_total = int(len(raw_senders | raw_receivers))
        unique_counterparty_ratio = float(unique_senders) / float(max(tx_count_in, 1))

        # Nhom 6: Thoi gian hoat dong (Lifespan & Active Periods)
        if len(sub) > 0:
            lifespan_seconds = int(sub["timestamp_unix"].max() - sub["timestamp_unix"].min())
            dt_series = pd.to_datetime(sub["timestamp_unix"], unit="s", utc=True)
            active_days = int(dt_series.dt.date.nunique())
            active_hours = int(dt_series.dt.floor("h").nunique())
        else:
            lifespan_seconds = 0
            active_days = 0
            active_hours = 0

        lifespan_hours = float(max(lifespan_seconds / 3600.0, 1.0))

        # Nhom 7: Tan suat hoat dong (Frequency)
        tx_frequency_per_hour = float(tx_count_total) / lifespan_hours
        event_rate_7d = float(total_event_count) / 7.0

        # Nhom 8: Do tap trung nguoi gui (Concentration)
        if tx_count_in > 0:
            top_sender_counts = in_events[in_events["from_address"].str.lower() != addr]["from_address"].value_counts()
            top_sender_count = int(top_sender_counts.max()) if len(top_sender_counts) > 0 else 0
            top_sender_tx_ratio = float(top_sender_count) / float(tx_count_in)
        else:
            top_sender_tx_ratio = 0.0

        # Nhom 9: Gas, Loi va Method Diversity
        # Theo ngu nghia Ethereum, Gas duoc tieu thu o cap do Transaction (receipt gasUsed).
        # Khi mot giao dich phat sinh nhieu su kien (normal + internal + token),
        # viec cong don gas cua tung su kien se lam thoi phong (double-count) luong gas.
        # Do do, ta tinh gas theo cap do transaction duy nhat (tx_hash) bang cach lay max(gas_used):
        valid_gas_events = sub[sub["gas_used"] >= 0]
        if len(valid_gas_events) > 0:
            tx_gas_series = valid_gas_events.groupby("tx_hash")["gas_used"].max()
            gas_used_total = float(tx_gas_series.sum())
            gas_used_mean = float(tx_gas_series.mean())
        else:
            gas_used_total = 0.0
            gas_used_mean = 0.0

        # Error transactions: Dem so transaction duy nhat gap loi revert
        failed_tx_hashes = sub[sub["is_error"] == 1]["tx_hash"].unique()
        error_tx_count = int(len(failed_tx_hashes))
        # Error rate: Ty le giao dich loi tren tong so giao dich duy nhat (chuan hoa [0, 1])
        error_tx_rate = float(error_tx_count) / float(max(unique_tx_count, 1))

        # Method diversity: Loc cac selector 4-byte hop le (vd: 0xa9059cbb)
        valid_methods = set()
        for m in sub["method_id"]:
            if isinstance(m, str) and m.startswith("0x") and len(m) >= 10 and m != "0x":
                valid_methods.add(m.lower())
        method_diversity = int(len(valid_methods))

        feature_rows.append({
            "address": addr,
            "tx_count_total": tx_count_total,
            "tx_count_in": tx_count_in,
            "tx_count_out": tx_count_out,
            "tx_in_out_ratio": tx_in_out_ratio,
            "normal_tx_in": normal_tx_in,
            "normal_tx_out": normal_tx_out,
            "internal_tx_count": internal_tx_count,
            "erc20_transfer_count": erc20_transfer_count,
            "erc721_transfer_count": erc721_transfer_count,
            "total_event_count": total_event_count,
            "unique_tx_count": unique_tx_count,
            "value_total_in_eth": value_total_in_eth,
            "value_total_out_eth": value_total_out_eth,
            "value_net_eth": value_net_eth,
            "value_mean_in_eth": value_mean_in_eth,
            "value_std_in_eth": value_std_in_eth,
            "value_max_in_eth": value_max_in_eth,
            "unique_senders": unique_senders,
            "unique_receivers": unique_receivers,
            "unique_counterparties_total": unique_counterparties_total,
            "unique_counterparty_ratio": unique_counterparty_ratio,
            "top_sender_tx_ratio": top_sender_tx_ratio,
            "lifespan_seconds": lifespan_seconds,
            "active_days": active_days,
            "active_hours": active_hours,
            "tx_frequency_per_hour": tx_frequency_per_hour,
            "event_rate_7d": event_rate_7d,
            "gas_used_mean": gas_used_mean,
            "gas_used_total": gas_used_total,
            "error_tx_count": error_tx_count,
            "error_tx_rate": error_tx_rate,
            "method_diversity": method_diversity
        })

    df_features = pd.DataFrame(feature_rows)
    df_metadata = pd.DataFrame(metadata_rows)

    return df_features, df_metadata, df_precreation_audit


def main():
    print("=" * 80)
    print("VIEW 1 STATISTICAL FEATURE EXTRACTION PIPELINE (PILOT 20)")
    print("=" * 80)

    # 1. Kiem tra file dau vao
    if not DEFAULT_COMBINED_ADDRESSES.exists():
        print(f"[CRITICAL] Khong tim thay file {DEFAULT_COMBINED_ADDRESSES}")
        sys.exit(1)
    if not DEFAULT_COMBINED_TRANSACTIONS.exists():
        print(f"[CRITICAL] Khong tim thay file {DEFAULT_COMBINED_TRANSACTIONS}")
        sys.exit(1)

    df_addr = pd.read_csv(DEFAULT_COMBINED_ADDRESSES)
    df_txs = pd.read_parquet(DEFAULT_COMBINED_TRANSACTIONS)
    print(f"[OK] Da nap {len(df_addr)} dia chi tu {DEFAULT_COMBINED_ADDRESSES}")
    print(f"[OK] Da nap {len(df_txs):,} ban ghi giao dich tu {DEFAULT_COMBINED_TRANSACTIONS}")

    # 2. Trich xuat features
    df_features, df_metadata, df_pre_audit = extract_view1_features(df_txs, df_addr)
    print(f"\n[OK] Trich xuat thanh cong:")
    print(f"  + Features table: {df_features.shape[0]} dong, {df_features.shape[1]} cot (1 id + {df_features.shape[1]-1} features)")
    print(f"  + Metadata table: {df_metadata.shape[0]} dong, {df_metadata.shape[1]} cot (Co lap nhan)")
    print(f"  + Pre-creation audit table: {len(df_pre_audit)} ban ghi truoc thoi diem deploy")

    # 3. Xuat file
    DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    features_parquet = DEFAULT_OUTPUT_DIR / "view1_features_pilot.parquet"
    features_csv = DEFAULT_OUTPUT_DIR / "view1_features_pilot.csv"
    metadata_parquet = DEFAULT_OUTPUT_DIR / "view1_metadata_pilot.parquet"
    metadata_csv = DEFAULT_OUTPUT_DIR / "view1_metadata_pilot.csv"
    audit_pre_csv = DEFAULT_OUTPUT_DIR / "view1_precreation_audit_pilot.csv"

    df_features.to_parquet(features_parquet, index=False, engine="pyarrow")
    df_features.to_csv(features_csv, index=False)
    df_metadata.to_parquet(metadata_parquet, index=False, engine="pyarrow")
    df_metadata.to_csv(metadata_csv, index=False)
    df_pre_audit.to_csv(audit_pre_csv, index=False)

    print(f"\n[OK] Da luu View 1 features Parquet: {features_parquet}")
    print(f"[OK] Da luu View 1 features CSV: {features_csv}")
    print(f"[OK] Da luu View 1 metadata Parquet: {metadata_parquet}")
    print(f"[OK] Da luu View 1 metadata CSV: {metadata_csv}")
    print(f"[OK] Da luu View 1 pre-creation audit CSV: {audit_pre_csv}")
    print("\n" + "=" * 80)
    print("HOAN THANH TRICH XUAT VIEW 1 STATISTICAL FEATURES!")
    print("=" * 80)


if __name__ == "__main__":
    main()
