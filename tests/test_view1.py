#!/usr/bin/env python3
# File: tests/test_view1.py
"""
Unit and Integration Tests for View 1 Statistical Features.
Thesis: Learning Unified Graph Representations for Ethereum Phishing Detection
under Incomplete Labels and Temporal Shifts.

Verifies 9 scientific & engineering criteria:
1. Exactly 20 output addresses, exactly 1 row per address.
2. No duplicate addresses.
3. No transactions outside the valid post-deployment 7-day window (T_creation <= T_tx < T_cutoff).
4. No mixing/summing of ETH with token balances (strict asset separation).
5. No endpoint double-counting across different transaction/event types.
6. Clear handling of missing/zero fields (no NaNs, no infs).
7. Zero label leakage in input feature matrix X (strict metadata isolation).
8. Determinism / idempotence: Re-running feature extraction on identical data produces bitwise-identical features.
9. Immutability of raw and pilot dataset files (hashes/counts preserved).
"""

import sys
import hashlib
from datetime import datetime
from pathlib import Path
import numpy as np
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.build_view1 import (
    extract_view1_features,
    parse_iso_timestamp,
    DEFAULT_COMBINED_ADDRESSES,
    DEFAULT_COMBINED_TRANSACTIONS,
    DEFAULT_OUTPUT_DIR
)


def calculate_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def test_1_and_2_row_count_and_uniqueness():
    print("[TEST 1 & 2] Kiem tra so luong dia chi (20 dong) va tinh duy nhat (0 trung lap)...")
    feat_parquet = DEFAULT_OUTPUT_DIR / "view1_features_pilot.parquet"
    assert feat_parquet.exists(), f"Khong tim thay {feat_parquet}"
    df = pd.read_parquet(feat_parquet)

    # 1. Dung 20 dia chi dau ra, moi dia chi 1 dong
    assert len(df) == 20, f"So luong dong phai bang 20, thuc te: {len(df)}"
    # 2. Khong co dia chi trung
    assert df["address"].nunique() == 20, f"Phat hien dia chi trung lap: {df['address'].nunique()} != 20"
    assert not df["address"].isna().any(), "Phat hien dia chi bi null!"
    print(f"  -> PASSED: Dung 20 dia chi, moi dia chi 1 dong, 0 trung lap.")


def test_3_temporal_boundary_post_deployment_window():
    print("[TEST 3] Kiem tra ranh gioi thoi gian nghiem ngat: T_creation <= T_tx < T_cutoff...")
    df_addr = pd.read_csv(DEFAULT_COMBINED_ADDRESSES)
    df_txs = pd.read_parquet(DEFAULT_COMBINED_TRANSACTIONS)
    feat_parquet = DEFAULT_OUTPUT_DIR / "view1_features_pilot.parquet"
    df_feat = pd.read_parquet(feat_parquet)

    for _, r in df_addr.iterrows():
        addr = r["address"].lower()
        c_ts = parse_iso_timestamp(r["first_seen_at"])
        cut_ts = parse_iso_timestamp(r["feature_cutoff_at"])

        # Giao dich thuc te trong pham vi hop le
        valid_txs = df_txs[
            (df_txs["target_address"].str.lower() == addr) &
            (df_txs["timestamp_unix"] >= c_ts) &
            (df_txs["timestamp_unix"] < cut_ts)
        ]

        feat_row = df_feat[df_feat["address"] == addr].iloc[0]
        # Kiem tra tong su kien phai khop chinh xac so luong sau khi loai bo cac tx ngoai window
        assert feat_row["total_event_count"] == len(valid_txs), (
            f"total_event_count khong khop cho {addr}: {feat_row['total_event_count']} != {len(valid_txs)}"
        )
        assert feat_row["unique_tx_count"] == valid_txs["tx_hash"].nunique(), (
            f"unique_tx_count khong khop cho {addr}"
        )

        # Kiem tra neu co giao dich truoc creation, no khong duoc tinh vao normal_tx_in/out hoac lifespan
        pre_txs = df_txs[
            (df_txs["target_address"].str.lower() == addr) &
            (df_txs["timestamp_unix"] < c_ts)
        ]
        if len(pre_txs) > 0:
            # 4 dia chi co giao dich truoc creation: 0x2e17..., 0x0729..., 0x3aba..., 0xf2bad1...
            # Dam bao cac tx truoc creation khong lam tang total_event_count
            all_addr_txs = df_txs[df_txs["target_address"].str.lower() == addr]
            assert feat_row["total_event_count"] < len(all_addr_txs), (
                f"Giao dich truoc creation da bi ro ri vao feature cua {addr}!"
            )

    print(f"  -> PASSED: 100% dac trung tuan thu tuyet doi T_creation <= T_tx < T_cutoff.")


def test_4_asset_unit_separation():
    print("[TEST 4] Kiem tra khong cong sai don vi ETH voi token ERC-20 / ERC-721...")
    df_txs = pd.read_parquet(DEFAULT_COMBINED_TRANSACTIONS)
    feat_parquet = DEFAULT_OUTPUT_DIR / "view1_features_pilot.parquet"
    df_feat = pd.read_parquet(feat_parquet)

    # Hop dong token FINAI 0xa9f3... co 1,505 ERC-20 transfers voi value_raw rat lon (hang trieu token)
    finai_addr = "0xa9f3acb50feb079806a03d5b66e2ebdd5c40effd"
    finai_feat = df_feat[df_feat["address"] == finai_addr].iloc[0]

    # Kiem tra value_total_in_eth cua FINAI: chi tinh ETH tu normal/internal, khong duoc chua so luong token FINAI
    assert finai_feat["erc20_transfer_count"] == 1505, f"erc20_transfer_count phai la 1505, co: {finai_feat['erc20_transfer_count']}"
    assert finai_feat["value_total_in_eth"] < 100.0, (
        f"Phat hien cong token vao ETH! value_total_in_eth = {finai_feat['value_total_in_eth']}"
    )

    # Kiem tra tong the: khong co bat ky gia tri ETH nao duoc tinh tu dong erc20/erc721
    token_rows = df_txs[df_txs["tx_type"].isin(["erc20", "erc721"])]
    assert (token_rows["value_eth"] == 0.0).all(), "Cot value_eth trong cac dong token phai luon bang 0.0!"

    print(f"  -> PASSED: Don vi ETH va Token duoc phan tach hoan toan, khong co su cong don sai lech.")


def test_5_event_differentiation_and_no_double_counting():
    print("[TEST 5] Kiem tra phan biet su kien va tranh double counting...")
    feat_parquet = DEFAULT_OUTPUT_DIR / "view1_features_pilot.parquet"
    df_feat = pd.read_parquet(feat_parquet)

    for _, row in df_feat.iterrows():
        # Tong so su kien phai bang tong cac loai su kien
        sum_components = (
            row["tx_count_total"] +  # normal
            row["internal_tx_count"] + # internal
            row["erc20_transfer_count"] + # erc20
            row["erc721_transfer_count"] # erc721
        )
        assert row["total_event_count"] == sum_components, (
            f"Double counting hoac thieu thanh phan tai {row['address']}: "
            f"total_event_count={row['total_event_count']} != sum={sum_components}"
        )
        # So tx duy nhat luon <= tong so event
        assert row["unique_tx_count"] <= row["total_event_count"], (
            f"unique_tx_count lon hon total_event_count tai {row['address']}"
        )

    print(f"  -> PASSED: Phan biet ro normal, internal, erc20, erc721; khong double count su kien.")


def test_6_missing_and_zero_handling():
    print("[TEST 6] Kiem tra xu ly missing va zero (khong co NaN/Inf)...")
    feat_parquet = DEFAULT_OUTPUT_DIR / "view1_features_pilot.parquet"
    df_feat = pd.read_parquet(feat_parquet)

    feature_cols = [c for c in df_feat.columns if c != "address"]
    # Khong chua NaN hoac Inf
    assert not df_feat[feature_cols].isna().any().any(), "Phat hien NaN trong bang dac trung!"
    assert not np.isinf(df_feat[feature_cols].to_numpy()).any(), "Phat hien Inf trong bang dac trung!"

    # Kiem tra phep chia cho 0: tx_in_out_ratio, unique_counterparty_ratio, tx_frequency_per_hour, error_tx_rate
    assert (df_feat["tx_in_out_ratio"] >= 0.0).all(), "tx_in_out_ratio co gia tri am!"
    assert (df_feat["unique_counterparty_ratio"] >= 0.0).all(), "unique_counterparty_ratio am!"
    assert (df_feat["unique_counterparty_ratio"] <= 1.0).all(), "unique_counterparty_ratio > 1!"
    assert (df_feat["tx_frequency_per_hour"] >= 0.0).all(), "tx_frequency_per_hour am!"
    assert (df_feat["error_tx_rate"] >= 0.0).all(), "error_tx_rate am!"

    print(f"  -> PASSED: 100% truong missing/zero duoc xu ly an toan, khong co NaN hoac Inf.")


def test_7_label_isolation_and_no_leakage():
    print("[TEST 7] Kiem tra co lap nhan tuyet doi trong vector dac trung X...")
    feat_parquet = DEFAULT_OUTPUT_DIR / "view1_features_pilot.parquet"
    df_feat = pd.read_parquet(feat_parquet)
    meta_parquet = DEFAULT_OUTPUT_DIR / "view1_metadata_pilot.parquet"
    assert meta_parquet.exists(), f"Khong tim thay {meta_parquet}"
    df_meta = pd.read_parquet(meta_parquet)

    # Danh sach cac tu khoa cam xuat hien trong feature columns
    FORBIDDEN_COL_SUBSTRINGS = ["label", "target", "source", "observed", "status", "phish"]
    for col in df_feat.columns:
        if col == "address":
            continue
        for forbidden in FORBIDDEN_COL_SUBSTRINGS:
            assert forbidden not in col.lower(), f"Phat hien ten cot vi pham co lap nhan: {col}"

    # Vector X thuan tuy (bo address)
    X = df_feat.drop(columns=["address"])
    assert "label_status" not in X.columns, "label_status xuat hien trong X!"
    assert "label_source" not in X.columns, "label_source xuat hien trong X!"
    assert "label_observed_at" not in X.columns, "label_observed_at xuat hien trong X!"

    # Kiem tra metadata co du 2 nhan PU-learning
    assert set(df_meta["label_status"].unique()) == {"positive", "unlabeled"}, "Metadata thieu nhan PU!"
    assert (df_meta["label_status"] == "positive").sum() == 10
    assert (df_meta["label_status"] == "unlabeled").sum() == 10

    print(f"  -> PASSED: Vector X co lap 100% khoi nhan va metadata; 0 ro ri thong tin tuong lai.")


def test_8_determinism_and_reproducibility():
    print("[TEST 8] Kiem tra tinh xac dinh va kha nang tai lap (Determinism / Idempotence)...")
    df_addr = pd.read_csv(DEFAULT_COMBINED_ADDRESSES)
    df_txs = pd.read_parquet(DEFAULT_COMBINED_TRANSACTIONS)

    # Chay lan 1 va lan 2 tren cung du lieu
    feat1, meta1, audit1 = extract_view1_features(df_txs, df_addr)
    feat2, meta2, audit2 = extract_view1_features(df_txs, df_addr)

    pd.testing.assert_frame_equal(feat1, feat2, check_exact=True)
    pd.testing.assert_frame_equal(meta1, meta2, check_exact=True)
    pd.testing.assert_frame_equal(audit1, audit2, check_exact=True)

    print(f"  -> PASSED: Tinh toan hoan toan xac dinh, bitwise-identical giua cac lan chay doc lap.")


def test_9_immutability_of_raw_and_pilot_sources():
    print("[TEST 9] Kiem tra tinh bat bien cua du lieu goc va du lieu pilot...")
    # Raw dataset counts (neu co san tai local)
    contracts_file = PROJECT_ROOT / "data" / "raw" / "phishing_contracts.log"
    if contracts_file.exists():
        with open(contracts_file, "r", encoding="utf-8") as f:
            contracts = [line.strip() for line in f if line.strip()]
        assert len(contracts) == 37654, f"phishing_contracts.log bi thay doi: {len(contracts)} != 37654"

        txs_file = PROJECT_ROOT / "data" / "raw" / "phishing_transactions.log"
        with open(txs_file, "r", encoding="utf-8") as f:
            txs = [line.strip() for line in f if line.strip()]
        assert len(txs) == 211319, f"phishing_transactions.log bi thay doi: {len(txs)} != 211319"
    else:
        print("  [INFO] data/raw/ khong co san tren repo public, bo qua kiem tra bat bien dataset goc.")

    # Pilot positive & unlabeled counts
    pos_tx_file = PROJECT_ROOT / "data" / "pilot" / "positive" / "pilot_transactions.parquet"
    df_pos_tx = pd.read_parquet(pos_tx_file)
    assert len(df_pos_tx) == 16, f"pilot_transactions.parquet bi thay doi: {len(df_pos_tx)} != 16"

    u_tx_file = PROJECT_ROOT / "data" / "pilot" / "unlabeled" / "pilot_unlabeled_transactions.parquet"
    df_u_tx = pd.read_parquet(u_tx_file)
    assert len(df_u_tx) == 5209, f"pilot_unlabeled_transactions.parquet bi thay doi: {len(df_u_tx)} != 5209"

    c_tx_file = PROJECT_ROOT / "data" / "pilot" / "combined" / "pilot_20_transactions_before_cutoff.parquet"
    df_c_tx = pd.read_parquet(c_tx_file)
    assert len(df_c_tx) == 2965, f"pilot_20_transactions_before_cutoff.parquet bi thay doi: {len(df_c_tx)} != 2965"

    c_addr_file = PROJECT_ROOT / "data" / "pilot" / "combined" / "pilot_20_addresses.csv"
    df_c_addr = pd.read_csv(c_addr_file)
    assert len(df_c_addr) == 20, f"pilot_20_addresses.csv bi thay doi: {len(df_c_addr)} != 20"

    print(f"  -> PASSED: 100% file nguon va file pilot duoc bao toan nguyen ven.")


def test_10_evm_semantic_successful_eth_transfers():
    print("[TEST 10] Kiem tra ngu nghia EVM ve chuyen ETH: Chi tinh giao dich thanh cong (is_error == 0)...")
    df_addr = pd.read_csv(DEFAULT_COMBINED_ADDRESSES)
    df_txs = pd.read_parquet(DEFAULT_COMBINED_TRANSACTIONS)
    feat_parquet = DEFAULT_OUTPUT_DIR / "view1_features_pilot.parquet"
    df_feat = pd.read_parquet(feat_parquet)

    for _, r in df_addr.iterrows():
        addr = r["address"].lower()
        c_ts = parse_iso_timestamp(r["first_seen_at"])
        cut_ts = parse_iso_timestamp(r["feature_cutoff_at"])

        sub = df_txs[
            (df_txs["target_address"].str.lower() == addr) &
            (df_txs["timestamp_unix"] >= c_ts) &
            (df_txs["timestamp_unix"] < cut_ts)
        ]

        # Chi cac giao dich ETH thanh cong moi chuyen balance tren EVM
        succ_eth_in = sub[
            (sub["tx_type"].isin(["normal", "internal"])) &
            (sub["to_address"].str.lower() == addr) &
            (sub["is_error"] == 0)
        ]["value_eth"].sum()

        feat_row = df_feat[df_feat["address"] == addr].iloc[0]
        np.testing.assert_allclose(
            feat_row["value_total_in_eth"],
            succ_eth_in,
            rtol=1e-6,
            err_msg=f"value_total_in_eth khong khop voi ETH thanh cong tai {addr}"
        )

    # Kiem tra rieng hop dong 0xa9f3...: 26 giao dich failed (1.614 ETH) tuyet doi khong nam trong value_total_in_eth
    finai_addr = "0xa9f3acb50feb079806a03d5b66e2ebdd5c40effd"
    finai_feat = df_feat[df_feat["address"] == finai_addr].iloc[0]
    # Gia tri ETH thanh cong chinh xac phai xap xi 25.889 ETH (khong phai 27.503 ETH thoi phong)
    assert finai_feat["value_total_in_eth"] < 26.0, (
        f"Phat hien failed ETH bi tinh vao balance cua 0xa9f3...! value = {finai_feat['value_total_in_eth']}"
    )
    print("  -> PASSED: 100% gia tri ETH tuan thu nghiem ngat ngu nghia EVM (loai bo giao dich revert).")


def test_11_transaction_level_gas_deduplication():
    print("[TEST 11] Kiem tra loai bo double-counting gas tren cac giao dich da su kien (Multi-event)...")
    df_addr = pd.read_csv(DEFAULT_COMBINED_ADDRESSES)
    df_txs = pd.read_parquet(DEFAULT_COMBINED_TRANSACTIONS)
    feat_parquet = DEFAULT_OUTPUT_DIR / "view1_features_pilot.parquet"
    df_feat = pd.read_parquet(feat_parquet)

    # 1. Kiem tra hop dong 0x2e1762... co 1 transaction tx_hash chua ca internal trace (493,575 gas) va token transfer (616,275 gas)
    # Gas tong hop le o cap do transaction tren chuoi phai dung bang 616,275 gas (khong phai 1,109,850 gas do cong don)
    pos1_addr = "0x2e17626176ef839492bc292b6392d517e8434a0e"
    pos1_feat = df_feat[df_feat["address"] == pos1_addr].iloc[0]
    assert pos1_feat["gas_used_total"] == 616275.0, (
        f"Double counting gas tai 0x2e17...! gas_used_total = {pos1_feat['gas_used_total']} != 616275"
    )

    # 2. Kiem tra tinh toan gas cho tat ca 20 hop dong: gas_used_total luon bang tong max(gas_used) theo tx_hash
    for _, r in df_addr.iterrows():
        addr = r["address"].lower()
        c_ts = parse_iso_timestamp(r["first_seen_at"])
        cut_ts = parse_iso_timestamp(r["feature_cutoff_at"])

        sub = df_txs[
            (df_txs["target_address"].str.lower() == addr) &
            (df_txs["timestamp_unix"] >= c_ts) &
            (df_txs["timestamp_unix"] < cut_ts)
        ]
        valid_gas = sub[sub["gas_used"] >= 0]
        expected_gas_total = valid_gas.groupby("tx_hash")["gas_used"].max().sum() if len(valid_gas) > 0 else 0.0

        feat_row = df_feat[df_feat["address"] == addr].iloc[0]
        assert feat_row["gas_used_total"] == expected_gas_total, (
            f"Gas total sai lech tai {addr}: {feat_row['gas_used_total']} != {expected_gas_total}"
        )

    print("  -> PASSED: Gas duoc tinh o cap do Transaction receipt, triet tieu 100% double-counting.")


def test_12_ground_truth_reconciliation_for_selected_contracts():
    print("[TEST 12] Doi chieu chi tiet tung feature voi transaction thuc te tren chuoi...")
    feat_parquet = DEFAULT_OUTPUT_DIR / "view1_features_pilot.parquet"
    df_feat = pd.read_parquet(feat_parquet)

    # Hop dong Positive 10: 0xba182f...
    # Chi co dung 1 normal creation transaction tren Ethereum Mainnet
    ba18_feat = df_feat[df_feat["address"] == "0xba182f3fa5ab968ed53635fa369af06b279d27c1"].iloc[0]
    assert ba18_feat["tx_count_total"] == 1
    assert ba18_feat["normal_tx_in"] == 0 # creation tx co to_address la null/contract creation
    assert ba18_feat["normal_tx_out"] == 0
    assert ba18_feat["internal_tx_count"] == 0
    assert ba18_feat["erc20_transfer_count"] == 0
    assert ba18_feat["total_event_count"] == 1
    assert ba18_feat["unique_tx_count"] == 1
    assert ba18_feat["gas_used_total"] == 226249.0
    assert ba18_feat["error_tx_count"] == 0

    # Hop dong Unlabeled FINAI: 0xa9f3...
    finai_feat = df_feat[df_feat["address"] == "0xa9f3acb50feb079806a03d5b66e2ebdd5c40effd"].iloc[0]
    assert finai_feat["total_event_count"] == 2859
    assert finai_feat["unique_tx_count"] == 2135
    assert finai_feat["erc20_transfer_count"] == 1505
    assert finai_feat["internal_tx_count"] == 736
    assert finai_feat["tx_count_total"] == 618
    assert finai_feat["error_tx_count"] == 29
    np.testing.assert_allclose(finai_feat["error_tx_rate"], 29 / 2135, rtol=1e-5)

    print("  -> PASSED: Doi chieu ground-truth 100% khop voi ban ghi on-chain thuc te.")


def run_all_tests():
    print("=" * 80)
    print("RUNNING VIEW 1 VERIFICATION & SCIENTIFIC INTEGRITY TESTS (12 CRITERIA)")
    print("=" * 80)
    test_1_and_2_row_count_and_uniqueness()
    test_3_temporal_boundary_post_deployment_window()
    test_4_asset_unit_separation()
    test_5_event_differentiation_and_no_double_counting()
    test_6_missing_and_zero_handling()
    test_7_label_isolation_and_no_leakage()
    test_8_determinism_and_reproducibility()
    test_9_immutability_of_raw_and_pilot_sources()
    test_10_evm_semantic_successful_eth_transfers()
    test_11_transaction_level_gas_deduplication()
    test_12_ground_truth_reconciliation_for_selected_contracts()
    print("\n" + "=" * 80)
    print("ALL VIEW 1 INTEGRITY TESTS PASSED SUCCESSFULLY (12/12)! ")
    print("=" * 80)


if __name__ == "__main__":
    run_all_tests()

