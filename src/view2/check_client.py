# File: src/view2/check_client.py
"""Kiem tra nhanh client Etherscan voi 1 hop dong pilot da biet dap an.
Chay: python -m src.view2.check_client
"""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.view2.etherscan_client import EtherscanClient  # noqa: E402

ADDR = "0x0729eef6f3bc6b66070ebe24e71e9b4402494947"
EXPECTED_TS = 1712573987  # tu data/processed/view1/view1_metadata_pilot.csv

load_dotenv(ROOT / ".env")
key = os.getenv("ETHERSCAN_API_KEY")
if not key or key == "your_etherscan_api_key_here":
    sys.exit("Thieu ETHERSCAN_API_KEY trong .env")

c = EtherscanClient(key, ROOT / "data/cache/view2")
info = c.contract_creation([ADDR])
if not info:
    sys.exit("API khong tra ve thong tin tao hop dong")
r = info[0]
ts = int(r["timestamp"])
print("timestamp    :", ts, "(dung)" if ts == EXPECTED_TS else f"(SAI, mong doi {EXPECTED_TS})")
print("block tao    :", r["blockNumber"])
print("factory      :", r.get("contractFactory") or "(rong)")
print("creator      :", r.get("contractCreator"))
print("cutoff block :", c.block_by_time(ts + 7 * 86400))
print("goi mang     :", c.n_network_calls, "| doc cache:", c.n_cache_hits)