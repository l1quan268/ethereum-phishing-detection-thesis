#!/usr/bin/env python3
"""
S07 - Trong khoang [evidence_time, evidence_time + 1 ngay) vi co nhung giao dich gi (khong goi API).

Tach theo nhom: vi dung mot lan (khong co giao dich truoc evidence_time) va vi co lich su.
Dem so giao dich (tx_hash khac nhau) trong 24 gio dau, chia thanh:
  n_ps      giao dich chia loi nhuan (co trong danh sach DaaS)
  n_non_ps  giao dich khac
Vi "rong sau ablation" = n_non_ps == 0 VA khong co giao dich nao truoc evidence_time.

Dau vao : data/interim/daas_accounts/accounts.csv, events.parquet (tu S03)
Dau ra  : reports/daas/s07_first_day_summary.csv     thong ke theo nhom
          reports/daas/s07_first_day_non_ps_dist.csv  phan bo n_non_ps theo nhom (0, 1, 2, 3-9, 10+)
Chay    : python -m scripts.run --name daas_first_day_content \
            --inputs data/interim/daas_accounts/accounts.csv data/interim/daas_accounts/events.parquet \
            --outputs reports/daas/s07_first_day_summary.csv reports/daas/s07_first_day_non_ps_dist.csv \
            -- scripts.daas.s07_first_day_content
"""
import argparse
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DAY = 86400


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--in-dir", default=str(ROOT / "data/interim/daas_accounts"))
    ap.add_argument("--out-dir", default=str(ROOT / "reports/daas"))
    a = ap.parse_args(argv)
    IN, OUT = Path(a.in_dir), Path(a.out_dir)
    OUT.mkdir(parents=True, exist_ok=True)

    acc = pd.read_csv(IN / "accounts.csv")[["address", "role", "evidence_ts"]].dropna()
    ev = pd.read_parquet(IN / "events.parquet",
                         columns=["target_address", "tx_hash", "timestamp", "is_profit_sharing_tx"])
    ev = ev.merge(acc, left_on="target_address", right_on="address")
    # mot giao dich = mot tx_hash; la chia loi nhuan neu bat ky su kien nao cua no duoc danh dau
    tx = ev.groupby(["address", "tx_hash"]).agg(ts=("timestamp", "min"), ps=("is_profit_sharing_tx", "max"),
                                                ev_ts=("evidence_ts", "first")).reset_index()
    before = tx[tx.ts < tx.ev_ts].groupby("address").size()
    win = tx[(tx.ts >= tx.ev_ts) & (tx.ts < tx.ev_ts + DAY)]
    acc["n_before"] = acc.address.map(before).fillna(0).astype(int)
    acc["n_ps_day1"] = acc.address.map(win[win.ps].groupby("address").size()).fillna(0).astype(int)
    acc["n_non_ps_day1"] = acc.address.map(win[~win.ps].groupby("address").size()).fillna(0).astype(int)
    acc["nhom"] = acc.n_before.eq(0).map({True: "dung_mot_lan", False: "co_lich_su"})
    acc["rong_sau_ablation"] = (acc.n_before == 0) & (acc.n_non_ps_day1 == 0)

    rows = []
    for nhom, g in list(acc.groupby("nhom")) + [("tat_ca", acc)]:
        rows.append({
            "nhom": nhom, "n_vi": len(g),
            "trung_vi_n_ps_day1": g.n_ps_day1.median(),
            "trung_vi_n_non_ps_day1": g.n_non_ps_day1.median(),
            "p90_n_non_ps_day1": g.n_non_ps_day1.quantile(0.9),
            "pct_khong_co_gd_khac_day1": round((g.n_non_ps_day1 == 0).mean() * 100, 1),
            "n_rong_sau_ablation": int(g.rong_sau_ablation.sum()),
            "pct_rong_sau_ablation": round(g.rong_sau_ablation.mean() * 100, 1),
        })
    t1 = pd.DataFrame(rows)
    t1.to_csv(OUT / "s07_first_day_summary.csv", index=False)
    print("=== 24 gio dau ke tu evidence_time ===\n" + t1.T.to_string(header=False))

    bins = pd.cut(acc.n_non_ps_day1, [-1, 0, 1, 2, 9, 10**9], labels=["0", "1", "2", "3-9", "10+"])
    t2 = pd.crosstab(acc.nhom, bins, margins=True)
    t2.to_csv(OUT / "s07_first_day_non_ps_dist.csv")
    print("\n=== So giao dich KHONG phai chia loi nhuan trong 24 gio dau ===\n" + t2.to_string())


if __name__ == "__main__":
    main()
