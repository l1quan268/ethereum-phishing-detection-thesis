#!/usr/bin/env python3
"""
S00 - Ghi lai nguon bo DaaS da tai (bang chung tai lap, khong goi API).

Ghi: commit cua repo DaaS, so dong va SHA-256 cua tung tep .log.
Khong sao chep du lieu DaaS vao repo (repo goc khong co LICENSE).

Dau vao : data/raw/daas/  (git clone https://github.com/blocksecteam/DaaS_dataset data/raw/daas)
Dau ra  : reports/daas/s00_daas_source.csv
Chay    : python -m scripts.run --name daas_source \
            --outputs reports/daas/s00_daas_source.csv \
            -- scripts.daas.s00_daas_source
"""
import hashlib
import subprocess
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "data/raw/daas"
FILES = ["operator_accounts.log", "affiliate_accounts.log",
         "profit_sharing_contracts.log", "profit_sharing_transactions.log"]


def main():
    try:
        commit = subprocess.check_output(["git", "-C", str(SRC), "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        commit = None
    rows = []
    for f in FILES:
        p = SRC / f
        if not p.exists():
            rows.append({"file": f, "exists": False})
            continue
        data = p.read_bytes()
        lines = [l.strip() for l in data.decode("utf-8", "ignore").splitlines() if l.strip()]
        rows.append({"file": f, "exists": True, "n_lines": len(lines), "n_unique": len(set(x.lower() for x in lines)),
                     "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "daas_commit": commit})
    df = pd.DataFrame(rows)
    out = ROOT / "reports/daas"
    out.mkdir(parents=True, exist_ok=True)
    df.to_csv(out / "s00_daas_source.csv", index=False)
    print("commit DaaS:", commit)
    print(df.drop(columns=["sha256"], errors="ignore").to_string(index=False))
    if not df.get("exists", pd.Series([False])).all():
        raise SystemExit("Thieu tep DaaS: kiem tra lai buoc git clone")


if __name__ == "__main__":
    main()
