#!/usr/bin/env python3
"""
Unit and Integration Tests for Data Integrity & Structure Conformance.
Tests:
- Raw SIGMETRICS 2025 dataset existence and integrity
- Label schema configuration
- Pilot 10 Positive dataset & parquet format
- Pilot reports & logs
- Manifest SHA-256 verification
"""

import sys
import json
import hashlib
from pathlib import Path
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def calculate_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


import pytest

def test_raw_dataset_integrity():
    print("[TEST] 1. Kiem tra tinh toan ven du lieu goc SIGMETRICS 2025 (data/raw)...")
    raw_dir = PROJECT_ROOT / "data" / "raw"
    contracts_file = raw_dir / "phishing_contracts.log"
    if not contracts_file.exists():
        pytest.skip("Du lieu goc SIGMETRICS 2025 (data/raw/*.log) khong duoc commit vi ban quyen upstream. Xem README de tai.")

    assert contracts_file.exists(), f"{contracts_file} khong ton tai!"
    with open(contracts_file, "r", encoding="utf-8") as f:
        contracts = [line.strip() for line in f if line.strip()]
    assert len(contracts) == 37654, f"So hop dong khong khop: {len(contracts)} != 37654"
    assert len(set(contracts)) == 37654, "Phat hien dia chi trung lap trong phishing_contracts.log!"

    txs_file = raw_dir / "phishing_transactions.log"
    assert txs_file.exists(), f"{txs_file} khong ton tai!"
    with open(txs_file, "r", encoding="utf-8") as f:
        txs = [line.strip() for line in f if line.strip()]
    assert len(txs) == 211319, f"So giao dich khong khop: {len(txs)} != 211319"

    keywords_file = raw_dir / "suspicious_keywords.log"
    assert keywords_file.exists(), f"{keywords_file} khong ton tai!"
    with open(keywords_file, "r", encoding="utf-8") as f:
        keywords = [line.strip() for line in f if line.strip()]
    assert len(keywords) == 35, f"So tu khoa khong khop: {len(keywords)} != 35"
    print(f"  -> PASSED: 37,654 contracts, 211,319 tx hashes, 35 suspicious keywords.")


def test_label_schema_config():
    print("[TEST] 2. Kiem tra cau hinh Label Schema (configs/label_schema.csv)...")
    schema_file = PROJECT_ROOT / "configs" / "label_schema.csv"
    assert schema_file.exists(), f"{schema_file} khong ton tai!"
    df = pd.read_csv(schema_file)
    expected_cols = ["address", "label_status", "first_seen_at", "feature_cutoff_at", "label_observed_at", "label_source"]
    assert list(df.columns) == expected_cols, f"Cot schema khong khop: {list(df.columns)} != {expected_cols}"
    print(f"  -> PASSED: Schema dung 6 cot chuan: {expected_cols}")


def test_pilot_positive_data():
    print("[TEST] 3. Kiem tra du lieu pilot 10 Positive (data/pilot/positive)...")
    pos_dir = PROJECT_ROOT / "data" / "pilot" / "positive"
    assert pos_dir.exists(), f"{pos_dir} khong ton tai!"

    addr_file = pos_dir / "pilot_addresses.csv"
    assert addr_file.exists(), f"{addr_file} khong ton tai!"
    df_addr = pd.read_csv(addr_file)
    assert len(df_addr) == 10, f"So dia chi pilot khong bang 10: {len(df_addr)}"
    assert all(df_addr["label_status"] == "positive"), "Tat ca dia chi pilot phai co label_status='positive'!"
    assert all(df_addr["address"].str.startswith("0x")), "Dia chi phai bat dau bang 0x!"

    parquet_file = pos_dir / "pilot_transactions.parquet"
    assert parquet_file.exists(), f"{parquet_file} khong ton tai!"
    df_txs = pd.read_parquet(parquet_file)
    assert len(df_txs) == 16, f"So giao dich pilot khong bang 16: {len(df_txs)}"
    required_cols = [
        "tx_hash", "block_number", "timestamp_unix", "timestamp_utc", "target_address",
        "tx_type", "from_address", "to_address", "value_eth", "value_raw", "gas_used",
        "gas_price_gwei", "is_error", "method_id", "function_name", "contract_address",
        "token_symbol", "in_sigmetrics_tx_log", "api_source"
    ]
    for col in required_cols:
        assert col in df_txs.columns, f"Thieu cot {col} trong pilot_transactions.parquet!"
    print(f"  -> PASSED: 10 dia chi positive, 16 giao dich normalized da duoc xac minh.")


def test_pilot_reports():
    print("[TEST] 4. Kiem tra cac bao cao va nhat ky pilot (reports/pilot)...")
    rep_dir = PROJECT_ROOT / "reports" / "pilot"
    assert rep_dir.exists(), f"{rep_dir} khong ton tai!"

    ts_file = rep_dir / "pilot_timestamp_report.csv"
    assert ts_file.exists(), f"{ts_file} khong ton tai!"
    df_ts = pd.read_csv(ts_file)
    assert len(df_ts) == 10, f"So ban ghi timestamp report khong bang 10: {len(df_ts)}"
    assert all(df_ts["status"] == "SUCCESS"), "Tat ca 10 dia chi phai co status SUCCESS!"

    log_file = rep_dir / "api_collection_log.csv"
    assert log_file.exists(), f"{log_file} khong ton tai!"
    df_log = pd.read_csv(log_file)
    assert len(df_log) == 50, f"So ban ghi API log khong bang 50: {len(df_log)}"
    assert all(df_log["http_status"] == 200), "Tat ca yeu cau API phai co http_status=200!"

    pilot_report = rep_dir / "bao_cao_pilot_vi.md"
    assert pilot_report.exists(), f"{pilot_report} khong ton tai!"
    print(f"  -> PASSED: pilot_timestamp_report (10/10 SUCCESS), api_collection_log (50/50 HTTP 200), bao_cao_pilot_vi.md.")


def test_migration_manifest():
    print("[TEST] 5. Kiem tra toan ven tat ca file da di chuyen qua Manifest (reports/migration_manifest.json)...")
    manifest_file = PROJECT_ROOT / "reports" / "migration_manifest.json"
    assert manifest_file.exists(), f"{manifest_file} khong ton tai!"
    with open(manifest_file, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    UPDATED_DOC_OR_CODE_FILES = {
        "src/collect_etherscan.py",
        "docs/README_PILOT_VI.md",
        "reports/audit/dataset_audit.md",
        "reports/pilot/bao_cao_pilot_vi.md"
    }

    RAW_DATASET_FILES = {
        "data/raw/phishing_contracts.log",
        "data/raw/phishing_transactions.log",
        "data/raw/suspicious_keywords.log"
    }

    for item in manifest["files"]:
        new_path = PROJECT_ROOT / item["new_path"]
        if item["new_path"] in RAW_DATASET_FILES and not new_path.exists():
            print(f"  [SKIP RAW] {item['new_path']} | Khong co tren public repo (ban quyen upstream).")
            continue
        assert new_path.exists(), f"File dich khong ton tai: {item['new_path']}"
        actual_size = new_path.stat().st_size
        actual_hash = calculate_sha256(new_path)
        if item["new_path"] in UPDATED_DOC_OR_CODE_FILES:
            assert actual_size > 0, f"{item['new_path']} bi rong!"
            print(f"  [OK] {item['new_path']} | {actual_size:,} B | Standardized post-migration code/doc")
        else:
            assert actual_size == item["size_bytes"], f"Size khong khop cho {item['new_path']}: {actual_size} != {item['size_bytes']}"
            assert actual_hash == item["sha256_original"], f"SHA256 khong khop cho {item['new_path']}"
            print(f"  [OK] {item['new_path']} | {actual_size:,} B | SHA256 matches original manifest 100%")
    print(f"  -> PASSED: Cac file hien dien trong manifest da duoc kiem tra toan ven.")


def test_pilot_20_unlabeled_and_combined():
    print("[TEST] 6. Kiem tra tap du lieu pilot 10 Unlabeled & Combined 20 dia chi...")
    # 1. Unlabeled addresses
    u_addr_file = PROJECT_ROOT / "data" / "pilot" / "unlabeled" / "pilot_unlabeled_addresses.csv"
    assert u_addr_file.exists(), f"{u_addr_file} khong ton tai!"
    df_u = pd.read_csv(u_addr_file)
    assert len(df_u) == 10, f"So luong Unlabeled khong bang 10: {len(df_u)}"
    assert all(df_u["label_status"] == "unlabeled"), "Tat ca Unlabeled phai co label_status='unlabeled'!"

    # Kiem tra khong trung lap voi phishing_contracts.log neu co file raw
    raw_phish_file = PROJECT_ROOT / "data" / "raw" / "phishing_contracts.log"
    if raw_phish_file.exists():
        with open(raw_phish_file, "r", encoding="utf-8") as f:
            phishing_set = set(line.strip().lower() for line in f if line.strip())
        assert not any(a.lower() in phishing_set for a in df_u["address"]), "Co Unlabeled trung voi phishing_contracts.log!"
    else:
        print("  [INFO] data/raw/phishing_contracts.log chua duoc tai, bo qua cross-check trung lap voi tap goc.")

    # 2. Unlabeled transactions
    u_txs_file = PROJECT_ROOT / "data" / "pilot" / "unlabeled" / "pilot_unlabeled_transactions.parquet"
    assert u_txs_file.exists(), f"{u_txs_file} khong ton tai!"
    df_u_txs = pd.read_parquet(u_txs_file)
    assert len(df_u_txs) > 0, "Unlabeled transactions khong duoc rong!"

    # 3. Combined 20 addresses
    c_addr_file = PROJECT_ROOT / "data" / "pilot" / "combined" / "pilot_20_addresses.csv"
    assert c_addr_file.exists(), f"{c_addr_file} khong ton tai!"
    df_c = pd.read_csv(c_addr_file)
    assert len(df_c) == 20, f"So luong combined addresses: {len(df_c)} != 20"
    assert (df_c["label_status"] == "positive").sum() == 10, "Thieu nhan positive trong tap 20!"
    assert (df_c["label_status"] == "unlabeled").sum() == 10, "Thieu nhan unlabeled trong tap 20!"
    assert not df_c["feature_cutoff_at"].isna().any(), "feature_cutoff_at khong duoc null trong tap 20!"

    # 4. Combined transactions before cutoff
    c_txs_file = PROJECT_ROOT / "data" / "pilot" / "combined" / "pilot_20_transactions_before_cutoff.parquet"
    assert c_txs_file.exists(), f"{c_txs_file} khong ton tai!"
    df_c_txs = pd.read_parquet(c_txs_file)
    assert len(df_c_txs) > 0, "Combined transactions before cutoff khong duoc rong!"

    # Kiem tra nghiem ngat Point-in-Time: moi transaction phai truoc cutoff_at
    from datetime import datetime, timezone
    cutoff_map = {}
    for _, r in df_c.iterrows():
        dt = datetime.fromisoformat(r["feature_cutoff_at"].replace("Z", "+00:00"))
        cutoff_map[r["address"].lower()] = int(dt.timestamp())

    for _, tx in df_c_txs.iterrows():
        target = tx["target_address"].lower()
        assert tx["timestamp_unix"] < cutoff_map[target], f"Rò rỉ thời gian phát hiện tại tx {tx['tx_hash']} cho {target}!"

    # 5. Quality report
    q_rep = PROJECT_ROOT / "reports" / "pilot" / "pilot_20_quality_report.md"
    assert q_rep.exists() and q_rep.stat().st_size > 0, f"{q_rep} khong ton tai hoac rong!"

    print(f"  -> PASSED: 10 Unlabeled, 20 Combined addresses, {len(df_c_txs):,} txs before cutoff (0 rò rỉ thời gian).")


if __name__ == "__main__":
    print("=" * 70)
    print("RUNNING DATA INTEGRITY TESTS")
    print("=" * 70)
    test_raw_dataset_integrity()
    test_label_schema_config()
    test_pilot_positive_data()
    test_pilot_reports()
    test_migration_manifest()
    test_pilot_20_unlabeled_and_combined()
    print("\n" + "=" * 70)
    print("ALL DATA INTEGRITY TESTS PASSED SUCCESSFULLY (6/6)!")
    print("=" * 70)
