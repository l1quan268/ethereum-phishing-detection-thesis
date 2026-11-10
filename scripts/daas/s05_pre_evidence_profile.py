#!/usr/bin/env python3
"""
S05 - Giao dich TRUOC evidence_time cua vi P la giao dich gi (khong goi API).

Phan loai moi su kien truoc evidence_time theo vai tro cua vi trong su kien:
  tao_hop_dong   vi gui giao dich tao hop dong
  goi_ham        vi gui giao dich goi ham hop dong (co method_id)
  gui_eth        vi gui ETH thuong (khong goi ham)
  nhan_eth       vi nhan ETH (giao dich thuong hoac noi bo)
  gui_token      vi gui token ERC-20
  nhan_token     vi nhan token ERC-20
  khac           con lai (vd giao dich 0 ETH vi nhan, loi)

Dau vao : data/interim/daas_accounts/accounts.csv, events.parquet   (tu S03)
Dau ra  : reports/daas/s05_pre_category_by_role.csv     so su kien theo loai x vai tro
          reports/daas/s05_pre_wallet_pattern.csv       so vi theo "mau" cac loai co truoc evidence
          reports/daas/s05_pre_top_functions.csv        top 30 ham vi tu goi truoc evidence
          reports/daas/s05_pre_first_event.csv          loai cua su kien DAU TIEN (vi co gap > 0)
Chay    : python -m scripts.run --name daas_pre_evidence_profile \
            --inputs data/interim/daas_accounts/accounts.csv data/interim/daas_accounts/events.parquet \
            --outputs reports/daas/s05_pre_category_by_role.csv reports/daas/s05_pre_wallet_pattern.csv \
                      reports/daas/s05_pre_top_functions.csv reports/daas/s05_pre_first_event.csv \
            -- scripts.daas.s05_pre_evidence_profile
Luu y   : chi la phan tich mo ta, KHONG tao dac trung cho mo hinh.
"""
import argparse
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
ORDER = ["tao_hop_dong", "goi_ham", "gui_eth", "nhan_eth", "gui_token", "nhan_token", "khac"]


def categorize(ev: pd.DataFrame) -> pd.Series:
    acc = ev["target_address"]
    out = ev["from_address"] == acc
    inc = ev["to_address"] == acc
    val = pd.to_numeric(ev["value_raw"], errors="coerce").fillna(0) > 0
    is_tok = ev["source"] == "erc20"
    is_eth = ev["source"].isin(["normal", "internal"])
    created = ev["contract_created"].fillna("") != ""
    has_fn = ev["method_id"].fillna("") != ""
    cat = pd.Series("khac", index=ev.index)
    cat[is_tok & inc] = "nhan_token"
    cat[is_tok & out] = "gui_token"
    cat[is_eth & inc & val] = "nhan_eth"
    cat[is_eth & out & val & ~has_fn] = "gui_eth"
    cat[(ev["source"] == "normal") & out & has_fn] = "goi_ham"
    cat[(ev["source"] == "normal") & out & created] = "tao_hop_dong"
    return cat


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--in-dir", default=str(ROOT / "data/interim/daas_accounts"))
    ap.add_argument("--out-dir", default=str(ROOT / "reports/daas"))
    a = ap.parse_args(argv)
    IN, OUT = Path(a.in_dir), Path(a.out_dir)
    OUT.mkdir(parents=True, exist_ok=True)

    acc = pd.read_csv(IN / "accounts.csv")[["address", "role", "evidence_ts"]].dropna()
    cols = ["target_address", "source", "tx_hash", "timestamp", "from_address", "to_address",
            "value_raw", "method_id", "function_name", "contract_created"]
    ev = pd.read_parquet(IN / "events.parquet", columns=cols)
    ev = ev.merge(acc, left_on="target_address", right_on="address")
    pre = ev[ev.timestamp < ev.evidence_ts].copy()
    pre["cat"] = categorize(pre)

    n_wallets = pre.target_address.nunique()
    print(f"vi co su kien truoc evidence_time: {n_wallets}/{len(acc)}  | so su kien: {len(pre)}")

    # 1) loai su kien x vai tro
    t1 = pd.crosstab(pre.cat, pre.role, margins=True).reindex(ORDER + ["All"]).fillna(0).astype(int)
    t1.to_csv(OUT / "s05_pre_category_by_role.csv")
    print("\n=== So su kien truoc evidence_time theo loai ===\n" + t1.to_string())

    # 2) mau cua tung vi: tap cac loai xuat hien
    pat = (pre.groupby("target_address").cat
           .agg(lambda s: "+".join(c for c in ORDER if c in set(s))))
    t2 = pat.value_counts().rename("n_vi").to_frame()
    t2["pct"] = (t2.n_vi / n_wallets * 100).round(1)
    t2.to_csv(OUT / "s05_pre_wallet_pattern.csv", index_label="mau")
    print("\n=== Mau hoat dong truoc evidence_time (top 15) ===\n" + t2.head(15).to_string())

    # 3) ham vi tu goi
    fn = pre[pre.cat == "goi_ham"].function_name.fillna("").str.split("(").str[0]
    fn = fn.where(fn != "", pre.loc[fn.index, "method_id"])
    t3 = (pd.DataFrame({"fn": fn, "w": pre.loc[fn.index, "target_address"]})
          .groupby("fn").agg(n_su_kien=("w", "size"), n_vi=("w", "nunique"))
          .sort_values("n_vi", ascending=False).head(30))
    t3.to_csv(OUT / "s05_pre_top_functions.csv", index_label="ham")
    print("\n=== Ham vi tu goi truoc evidence_time (top 30 theo so vi) ===\n" + t3.to_string())

    # 4) su kien dau tien cua vi
    first = pre.sort_values("timestamp").groupby("target_address").head(1)
    t4 = first.cat.value_counts().reindex(ORDER).fillna(0).astype(int).rename("n_vi").to_frame()
    t4["pct"] = (t4.n_vi / max(len(first), 1) * 100).round(1)
    t4.to_csv(OUT / "s05_pre_first_event.csv", index_label="loai")
    print("\n=== Loai cua su kien DAU TIEN (vi co gap > 0) ===\n" + t4.to_string())


if __name__ == "__main__":
    main()
