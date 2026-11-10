#!/usr/bin/env python3
"""
Thu lich su giao dich cua tai khoan DaaS (operator / affiliate) va tinh evidence_time.

evidence_time = thoi diem SOM NHAT tai khoan tham gia mot giao dich co tx_hash nam trong
                profit_sharing_transactions.log (DaaS, IMC 2025).
  - Truong hop ETH  : tien chia di qua giao dich noi bo (txlistinternal cua tai khoan).
  - Truong hop token: transferFrom thang tu nan nhan -> tai khoan (tokentx cua tai khoan).
  -> Lay ca normal + internal + erc20 cua CHINH tai khoan thi bat duoc ca hai.

Dau vao : data/interim/daas_account_types.csv   (tu buoc kiem tra EOA)
          data/raw/daas/profit_sharing_transactions.log
Dau ra  : <out-dir>/events.parquet   su kien tho (schema giong src/view2/collect_events.py)
          <out-dir>/accounts.csv     1 dong / tai khoan: first_seen, evidence_time, khoang cach, trang thai

Chay thu 30 tai khoan:
  python -m src.daas.collect_account_events --sample 30
Chay toan bo:
  python -m src.daas.collect_account_events --sample 0
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.view2.etherscan_client import EtherscanClient, EtherscanError  # noqa: E402
from src.view2.collect_events import SOURCE_ACTION, EVENT_COLUMNS, normalize_rows  # noqa: E402


def iso_to_ts(s: str) -> int:
    return int(datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc).timestamp())


def read_set(p: Path) -> set:
    return {l.strip().lower() for l in p.read_text(encoding="utf-8").splitlines() if l.strip()}


def pick_accounts(types: pd.DataFrame, sample: int, seed: int) -> pd.DataFrame:
    eoa = types[types.kind.isin(["eoa", "eoa_7702"])].copy()
    if sample <= 0 or sample >= len(eoa):
        return eoa
    n_op = min(max(1, sample // 6), (eoa.role == "operator").sum())
    op = eoa[eoa.role == "operator"].sample(n_op, random_state=seed)
    af = eoa[eoa.role == "affiliate"].sample(sample - n_op, random_state=seed)
    return pd.concat([op, af])


def summarize_account(addr: str, ev: pd.DataFrame) -> dict:
    if ev.empty:
        return {"first_seen_ts": None, "evidence_ts": None, "evidence_source": None,
                "n_events": 0, "n_tx": 0, "n_ps_tx": 0}
    ps = ev[ev.is_profit_sharing_tx]
    first = ps.sort_values("timestamp").iloc[0] if len(ps) else None
    return {
        "first_seen_ts": int(ev.timestamp.min()),
        "evidence_ts": int(first.timestamp) if first is not None else None,
        "evidence_source": first.source if first is not None else None,
        "n_events": len(ev),
        "n_tx": ev.tx_hash.nunique(),
        "n_ps_tx": ps.tx_hash.nunique(),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--types", default=str(ROOT / "data/interim/daas_account_types.csv"))
    ap.add_argument("--ps-tx", default=str(ROOT / "data/raw/daas/profit_sharing_transactions.log"))
    ap.add_argument("--sample", type=int, default=30, help="so tai khoan; 0 = tat ca")
    ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument("--end", default="2025-04-08T00:00:00Z",
                    help="moc cuoi lay du lieu (UTC). Mac dinh = 01/04/2025 + 7 ngay")
    ap.add_argument("--sources", default="normal,internal,erc20")
    ap.add_argument("--cache-dir", default=str(ROOT / "data/cache/view2"))
    ap.add_argument("--out-dir", default=str(ROOT / "data/interim/daas_accounts"))
    ap.add_argument("--rate-limit", type=float, default=2.0)
    a = ap.parse_args()

    try:
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env")
    except ImportError:
        pass
    key = os.getenv("ETHERSCAN_API_KEY")
    if not key or key == "your_etherscan_api_key_here":
        sys.exit("[CRITICAL] Thieu ETHERSCAN_API_KEY trong .env")

    sources = [s.strip() for s in a.sources.split(",") if s.strip()]
    ps_set = read_set(Path(a.ps_tx))
    accts = pick_accounts(pd.read_csv(a.types), a.sample, a.seed)
    print(f"[OK] {len(ps_set):,} profit-sharing tx | {len(accts)} tai khoan "
          f"({(accts.role == 'operator').sum()} operator, {(accts.role == 'affiliate').sum()} affiliate)")

    c = EtherscanClient(key, Path(a.cache_dir), rate_limit=a.rate_limit)
    end_block = c.block_by_time(iso_to_ts(a.end), closest="before")
    print(f"[OK] lay du lieu tu block 0 den block {end_block} ({a.end})")

    all_ev, rows = [], []
    for n, (addr, role, kind) in enumerate(zip(accts.address, accts.role, accts.kind), 1):
        t0 = time.time()
        rec = {"address": addr, "role": role, "kind": kind, "status": "ok", "saturated": ""}
        try:
            ev_rows = []
            for s in sources:
                res = c.list_range(SOURCE_ACTION[s], addr, 0, end_block)
                if res["saturated_ranges"]:
                    rec["saturated"] += f"{s}:{res['saturated_ranges']};"
                ev_rows += normalize_rows(addr, s, res["rows"], set())
        except EtherscanError as ex:
            rec["status"] = f"error: {ex}"
            rows.append(rec)
            print(f"[{n}/{len(accts)}] {addr}: LOI {ex}")
            continue
        ev = pd.DataFrame(ev_rows, columns=EVENT_COLUMNS).drop(columns=["in_sigmetrics_tx_log"])
        ev["is_profit_sharing_tx"] = ev.tx_hash.isin(ps_set)
        rec.update(summarize_account(addr, ev))
        rows.append(rec)
        all_ev.append(ev)
        ev_s = "chua thay" if rec["evidence_ts"] is None else \
            datetime.fromtimestamp(rec["evidence_ts"], timezone.utc).strftime("%Y-%m-%d")
        print(f"[{n}/{len(accts)}] {addr} {role:9s} su kien={rec['n_events']:6d} "
              f"ps_tx={rec['n_ps_tx']:5d} evidence={ev_s}  ({time.time() - t0:.1f}s)")

    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    ev_all = pd.concat(all_ev, ignore_index=True) if all_ev else pd.DataFrame(columns=EVENT_COLUMNS)
    for col in ["tx_index", "token_decimal", "gas_used"]:
        if col in ev_all:
            ev_all[col] = ev_all[col].astype("Int64")
    ev_all.to_parquet(out / "events.parquet", index=False)

    acc = pd.DataFrame(rows)
    for col in ["first_seen_ts", "evidence_ts"]:
        acc[col.replace("_ts", "_utc")] = pd.to_datetime(acc[col], unit="s", utc=True)
    acc["gap_days"] = (acc.evidence_ts - acc.first_seen_ts) / 86400
    acc.to_csv(out / "accounts.csv", index=False)

    ok = acc[acc.status == "ok"]
    has = ok.evidence_ts.notna()
    print("\n===== TOM TAT =====")
    print(f"thanh cong: {len(ok)}/{len(acc)} | co evidence_time: {has.sum()}/{len(ok)} ({has.mean() * 100:.1f}%)")
    print(pd.crosstab(ok.role, has.map({True: "co", False: "chua"})).to_string())
    print("\nnguon cua giao dich evidence:", ok.evidence_source.value_counts().to_dict())
    print("\nso su kien moi tai khoan:")
    print(ok.n_events.describe(percentiles=[.5, .9]).round(1).to_string())
    print("\nkhoang cach first_seen -> evidence (ngay):")
    print(ok.gap_days.describe(percentiles=[.25, .5, .75, .9]).round(1).to_string())
    print(f"  = 0 ngay (vi moi tao de lua): {(ok.gap_days < 1).sum()} | > 30 ngay: {(ok.gap_days > 30).sum()} "
          f"| > 365 ngay: {(ok.gap_days > 365).sum()}")
    if acc.saturated.str.len().gt(0).any():
        print("\n[CANH BAO] khoang khoi cham tran:", acc[acc.saturated.str.len() > 0].address.tolist())
    print(f"\ngoi mang: {c.n_network_calls} | cache: {c.n_cache_hits} -> {out}")


if __name__ == "__main__":
    main()
