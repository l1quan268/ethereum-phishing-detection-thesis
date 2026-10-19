#!/usr/bin/env python3
"""
Unit and Integration Tests for Cache & Resume Mechanism.
Ensures:
- 10 pilot addresses have complete cache files (5 actions per address)
- Cache loader returns cache_hit=True
- ZERO network/API calls are performed when cache exists (strict mock assertion)
"""

import sys
import json
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.collect_etherscan import EtherscanV2Collector

EXPECTED_ACTIONS = [
    "getcontractcreation",
    "txlist",
    "txlistinternal",
    "tokentx",
    "tokennfttx"
]


import pytest

def test_cache_structure_and_files():
    print("[TEST] 1. Kiem tra cau truc thu muc cache (data/cache)...")
    cache_dir = PROJECT_ROOT / "data" / "cache"
    if not cache_dir.exists():
        pytest.skip("Thu muc data/cache khong co san tren repo public (duoc ignore boi .gitignore; can chia se rieng hoac tu dong tao khi chay collector).")

    addr_dirs = [d for d in cache_dir.iterdir() if d.is_dir() and d.name.startswith("0x")]
    if len(addr_dirs) == 0:
        pytest.skip("data/cache rong, bo qua kiem tra cache files.")
    assert len(addr_dirs) == 20, f"So luong thu muc dia chi trong cache: {len(addr_dirs)} != 20"

    total_files = 0
    for addr_dir in addr_dirs:
        for action in EXPECTED_ACTIONS:
            cache_file = addr_dir / f"{action}_page1.json"
            assert cache_file.exists(), f"Thieu file cache: {cache_file}"
            assert cache_file.stat().st_size > 0, f"File cache bi rong: {cache_file}"
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            assert isinstance(data, dict), f"Noi dung {cache_file} khong phai la JSON object hop le!"
            total_files += 1

    assert total_files == 100, f"Tong so file cache: {total_files} != 100"
    print(f"  -> PASSED: 20/20 dia chi day du 5 file cache (tong cong 100 file JSON hop le).")


def test_cache_hit_without_network():
    print("[TEST] 2. Kiem tra co che Cache/Resume (Chan hoan toan mang, bao dam cache_hit=True)...")
    cache_dir = PROJECT_ROOT / "data" / "cache"
    if not cache_dir.exists():
        pytest.skip("Thu muc data/cache khong co san, bo qua test cache hit.")
    addr_dirs = [d.name.lower() for d in cache_dir.iterdir() if d.is_dir() and d.name.startswith("0x")]
    if len(addr_dirs) == 0:
        pytest.skip("data/cache khong co dia chi, bo qua test cache hit.")
    
    # Su dung dummy API key de chung minh khong can dung den API key thuc
    collector = EtherscanV2Collector(
        api_key="DUMMY_KEY_FOR_TESTING_ZERO_NETWORK_CALLS",
        cache_dir=cache_dir,
        rate_limit=10.0,
        force_refresh=False
    )

    # Monkeypatch session.get de nem Exception neu co bat ky cuoc goi mang nao phat sinh
    def forbid_network_call(*args, **kwargs):
        raise RuntimeError("VI PHAM: Co cuoc goi mang phat sinh khi le ra phai doc tu Cache!")

    collector.session.get = forbid_network_call

    test_address = addr_dirs[0]

    # Test query tung action
    for action in EXPECTED_ACTIONS:
        module = "account" if action != "getcontractcreation" else "contract"
        data, cache_hit = collector._query(
            address=test_address,
            module=module,
            action=action,
            extra_params={},
            page=1
        )
        assert cache_hit is True, f"Cache miss khong mong muon tai {action} cho {test_address}!"
        assert data is not None, f"Data doc tu cache bi None tai {action}!"
        assert "status" in data or "message" in data, f"Phan hoi cache thieu truong chuan!"

    print(f"  -> PASSED: 100% request duoc phuc hoi tu Cache, session.get khong bi kich hoat.")


def test_collector_pipeline_methods():
    print("[TEST] 3. Kiem tra cac phuong thuc cap cao get_contract_creation & get_paginated_transactions tu Cache...")
    cache_dir = PROJECT_ROOT / "data" / "cache"
    if not cache_dir.exists():
        pytest.skip("Thu muc data/cache khong co san, bo qua test collector methods.")
    addr_dirs = [d.name.lower() for d in cache_dir.iterdir() if d.is_dir() and d.name.startswith("0x")]
    if len(addr_dirs) == 0:
        pytest.skip("data/cache khong co dia chi, bo qua test collector methods.")

    collector = EtherscanV2Collector(
        api_key="DUMMY_KEY_FOR_TESTING_ZERO_NETWORK_CALLS",
        cache_dir=cache_dir,
        rate_limit=10.0,
        force_refresh=False
    )

    def forbid_network_call(*args, **kwargs):
        raise RuntimeError("VI PHAM: Goi mang khi doc cache qua ham cap cao!")

    collector.session.get = forbid_network_call

    assert len(addr_dirs) == 20, f"So luong dia chi: {len(addr_dirs)} != 20"
    for addr in addr_dirs:
        creation = collector.get_contract_creation(addr)
        assert creation is not None, f"Khong lay duoc creation tu cache cho {addr}"
        assert "contractAddress" in creation, f"Creation thieu contractAddress cho {addr}"

        txlist = collector.get_paginated_transactions(addr, "txlist")
        assert isinstance(txlist, list), f"txlist phai la list cho {addr}"

    print(f"  -> PASSED: get_contract_creation va get_paginated_transactions hoat dong 100% tren Cache.")


if __name__ == "__main__":
    print("=" * 70)
    print("RUNNING CACHE & RESUME INTEGRATION TESTS")
    print("=" * 70)
    test_cache_structure_and_files()
    test_cache_hit_without_network()
    test_collector_pipeline_methods()
    print("\n" + "=" * 70)
    print("ALL CACHE & RESUME TESTS PASSED SUCCESSFULLY (3/3)!")
    print("=" * 70)
