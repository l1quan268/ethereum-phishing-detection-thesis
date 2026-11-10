#!/usr/bin/env python3
"""
S06 - t* = evidence_time + Delta co "du som" khong? (khong goi API)

Do moi vi P: cac giao dich chia loi nhuan (GDCLN) trai dai bao lau, va voi tung Delta
bao nhieu phan GDCLN DA XAY RA truoc t* (khong ngan duoc) / CON LAI sau t* (con ngan duoc).

Dau vao : data/interim/daas_accounts/accounts.csv, events.parquet (cot is_profit_sharing_tx, tu S03)
Dau ra  : reports/daas/s06_ps_span_by_role.csv        so GDCLN va thoi gian hoat dong (ngay) theo vai tro
          reports/daas/s06_ps_share_by_delta.csv      theo Delta: ty le GDCLN con lai sau t*
Chay    : python -m scripts.run --name daas_ps_timing \
            --inputs data/interim/daas_accounts/accounts.csv data/interim/daas_accounts/events.parquet \
            --outputs reports/daas/s06_ps_span_by_role.csv reports/daas/s06_ps_share_by_delta.csv \
            -- scripts.daas.s06_ps_timing
Luu y   : dem theo SO GIAO DICH, chua tinh gia tri tien (nhieu loai token, can quy doi).
"""
import argparse
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DELTAS = {"0": 0, "1h": 3600, "1d": 86400, "7d": 7 * 86400, "30d": 30 * 86400}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--in-dir", default=str(ROOT / "data/interim/daas_accounts"))
    ap.add_argument("--out-dir", default=str(ROOT / "reports/daas"))
    a = ap.parse_args(argv)
    IN, OUT = Path(a.in_dir), Path(a.out_dir)
    OUT.mkdir(parents=True, exist_ok=True)

    acc = pd.read_csv(IN / "accounts.csv")[["address", "role", "evidence_ts"]].dropna()
    ev = pd.read_parquet(IN / "events.parquet", columns=["target_address", "tx_hash", "timestamp",
                                                          "is_profit_sharing_tx"])
    ps = (ev[ev.is_profit_sharing_tx].drop_duplicates(["target_address", "tx_hash"])
          .merge(acc, left_on="target_address", right_on="address"))

    # 1) moi vi: so GDCLN va khoang hoat dong (lan dau -> lan cuoi)
    w = ps.groupby(["address", "role"]).agg(n_ps=("tx_hash", "size"), first=("timestamp", "min"),
                                           last=("timestamp", "max")).reset_index()
    w["span_days"] = (w["last"] - w["first"]) / 86400
    q = [0.25, 0.5, 0.75, 0.9]
    rows = []
    for role, g in list(w.groupby("role")) + [("tat_ca", w)]:
        r = {"role": role, "n_vi": len(g), "pct_chi_1_GDCLN": round((g.n_ps == 1).mean() * 100, 1)}
        for c in ["n_ps", "span_days"]:
            for p in q:
                r[f"{c}_p{int(p * 100)}"] = round(g[c].quantile(p), 2)
        rows.append(r)
    t1 = pd.DataFrame(rows)
    t1.to_csv(OUT / "s06_ps_span_by_role.csv", index=False)
    print("=== So GDCLN va thoi gian hoat dong (ngay) moi vi ===\n" + t1.T.to_string(header=False))

    # 2) theo Delta: phan GDCLN da xay ra truoc t* va con lai sau t*
    rows = []
    for name, d in DELTAS.items():
        before = ps.timestamp < ps.evidence_ts + d
        per_w = before.groupby(ps.address).mean()
        rows.append({
            "delta": name,
            "pct_GDCLN_con_lai_sau_tstar_gop": round((~before).mean() * 100, 1),
            "trung_vi_pct_con_lai_moi_vi": round((1 - per_w).median() * 100, 1),
            "pct_vi_khong_con_GDCLN_sau_tstar": round((per_w == 1).mean() * 100, 1),
        })
    t2 = pd.DataFrame(rows)
    t2.to_csv(OUT / "s06_ps_share_by_delta.csv", index=False)
    print("\n=== Theo Delta: GDCLN con lai SAU t* (con ngan duoc) ===\n" + t2.to_string(index=False))


if __name__ == "__main__":
    main()
