#!/usr/bin/env python3
"""
S01 - Thoi diem tao cua 1.910 profit-sharing contract (DaaS) -> phan phoi theo thang.

Dau vao : data/raw/daas/profit_sharing_contracts.log
Dau ra  : data/interim/daas_contract_creation.csv          (chi tiet, khong commit)
          reports/daas/s01_contract_creation_by_month.csv   (tom tat, commit lam bang chung)
Chay    : python -m scripts.run --name daas_contract_creation \
            --inputs data/raw/daas/profit_sharing_contracts.log \
            --outputs data/interim/daas_contract_creation.csv reports/daas/s01_contract_creation_by_month.csv \
            -- scripts.daas.s01_contract_creation
Chi phi : khoang 382 luot goi (doc cache neu da chay truoc do).
"""
import os
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.view2.etherscan_client import EtherscanClient  # noqa: E402


def main():
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    c = EtherscanClient(os.getenv("ETHERSCAN_API_KEY"), ROOT / "data/cache/view2")
    addrs = [l.strip().lower() for l in open(ROOT / "data/raw/daas/profit_sharing_contracts.log") if l.strip()]
    rows = []
    for i in range(0, len(addrs), 5):
        for r in c.contract_creation(addrs[i:i + 5]):
            rows.append({"address": r["contractAddress"].lower(), "creation_ts": int(r["timestamp"]),
                         "creation_block": int(r["blockNumber"]), "creator": (r.get("contractCreator") or "").lower()})
        if (i // 5) % 50 == 0:
            print(f"{min(i + 5, len(addrs))}/{len(addrs)}")
    df = pd.DataFrame(rows)
    df["month"] = pd.to_datetime(df.creation_ts, unit="s", utc=True).dt.strftime("%Y-%m")
    (ROOT / "data/interim").mkdir(parents=True, exist_ok=True)
    df.to_csv(ROOT / "data/interim/daas_contract_creation.csv", index=False)

    vc = df.month.value_counts().sort_index()
    summary = pd.DataFrame({"n_contracts": vc, "cum_pct": (vc.cumsum() / len(df) * 100).round(1)})
    (ROOT / "reports/daas").mkdir(parents=True, exist_ok=True)
    summary.to_csv(ROOT / "reports/daas/s01_contract_creation_by_month.csv", index_label="month")

    print("khong lay duoc:", len(set(addrs) - set(df.address)))
    print("som nhat:", pd.to_datetime(df.creation_ts.min(), unit="s", utc=True),
          "| muon nhat:", pd.to_datetime(df.creation_ts.max(), unit="s", utc=True))
    print(summary.to_string())
    print(f"goi mang: {c.n_network_calls} | cache: {c.n_cache_hits}")


if __name__ == "__main__":
    main()
