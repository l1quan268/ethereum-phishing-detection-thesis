#!/usr/bin/env python3
"""
S04 - Lam giau accounts.csv (khong goi API): so giao dich truoc evidence_time, trong 24h dau,
      phan phoi evidence_time theo thang.

Dau vao : data/interim/daas_accounts/accounts.csv, events.parquet   (tu src.daas.collect_account_events = S03)
Dau ra  : data/interim/daas_accounts/accounts_enriched.csv          (chi tiet, khong commit)
          reports/daas/s04_tx_before_evidence.csv                    (role x nhom so giao dich, commit)
          reports/daas/s04_evidence_by_month.csv                     (n, % tich luy theo thang, commit)
Chay    : python -m scripts.run --name daas_enrich_accounts \
            --inputs data/interim/daas_accounts/accounts.csv \
            --outputs reports/daas/s04_tx_before_evidence.csv reports/daas/s04_evidence_by_month.csv \
            -- scripts.daas.s04_enrich_accounts
"""
import argparse
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--in-dir", default=str(ROOT / "data/interim/daas_accounts"))
    ap.add_argument("--out-dir", default=str(ROOT / "reports/daas"))
    a = ap.parse_args(argv)
    IN, OUT = Path(a.in_dir), Path(a.out_dir)
    acc = pd.read_csv(IN / "accounts.csv")
    ev = pd.read_parquet(IN / "events.parquet", columns=["target_address", "tx_hash", "timestamp"])
    m = ev.merge(acc[["address", "evidence_ts"]], left_on="target_address", right_on="address")
    pre = m[m.timestamp < m.evidence_ts].groupby("address").tx_hash.nunique()
    day1 = m[(m.timestamp >= m.evidence_ts) & (m.timestamp < m.evidence_ts + 86400)].groupby("address").tx_hash.nunique()
    acc["n_tx_before"] = acc.address.map(pre).fillna(0).astype(int)
    acc["n_tx_first_day"] = acc.address.map(day1).fillna(0).astype(int)
    acc["ev_month"] = pd.to_datetime(acc.evidence_ts, unit="s", utc=True).dt.strftime("%Y-%m")
    acc.to_csv(IN / "accounts_enriched.csv", index=False)

    OUT.mkdir(parents=True, exist_ok=True)
    bins = pd.cut(acc.n_tx_before, [-1, 0, 2, 9, 99, 10**9], labels=["0", "1-2", "3-9", "10-99", "100+"])
    tab = pd.crosstab(acc.role, bins, margins=True)
    tab.to_csv(OUT / "s04_tx_before_evidence.csv")
    vc = acc.ev_month.value_counts().sort_index()
    by_m = pd.DataFrame({"n_P": vc, "cum_pct": (vc.cumsum() / len(acc) * 100).round(1)})
    by_m.to_csv(OUT / "s04_evidence_by_month.csv", index_label="month")

    print("=== So giao dich TRUOC evidence_time ===")
    print(acc.n_tx_before.describe(percentiles=[.25, .5, .75, .9]).round(1).to_string())
    print(tab.to_string())
    print("\n=== So giao dich trong 24h dau ===")
    print(acc.n_tx_first_day.describe(percentiles=[.5, .9]).round(1).to_string())
    print("\n=== evidence_time theo thang ===")
    print(by_m.to_string())


if __name__ == "__main__":
    main()
