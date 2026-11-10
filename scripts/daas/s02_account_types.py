#!/usr/bin/env python3
"""
S02 - Phan loai 6.143 tai khoan DaaS: eoa / eoa_7702 / contract / unknown.

Quy tac: co creation info -> contract; khong co va eth_getCode = 0x -> eoa;
         ma 0xef0100||address (23 byte, EIP-7702) -> eoa_7702; con lai -> unknown.
Luu y  : eth_getCode tra trang thai HIEN TAI -> chi dung de loc, KHONG lam dac trung.

Dau vao : data/raw/daas/operator_accounts.log, affiliate_accounts.log
Dau ra  : data/interim/daas_account_types.csv          (chi tiet, khong commit)
          reports/daas/s02_account_types_summary.csv   (bang cheo role x kind, commit)
          reports/daas/s02_non_eoa.csv                 (danh sach dia chi khong phai EOA, commit)
Chay    : python -m scripts.run --name daas_account_types \
            --inputs data/raw/daas/operator_accounts.log data/raw/daas/affiliate_accounts.log \
            --outputs data/interim/daas_account_types.csv reports/daas/s02_account_types_summary.csv \
            -- scripts.daas.s02_account_types
Chi phi : khoang 1.229 + 6.143 luot goi lan dau.
"""
import os
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.view2.etherscan_client import EtherscanClient, EtherscanError  # noqa: E402


def read(p):
    return [l.strip().lower() for l in open(p) if l.strip()]


def classify(code: str) -> str:
    code = (code or "0x").lower()
    if code in ("0x", ""):
        return "eoa"
    if code.startswith("0xef0100") and len(code) == 2 + 23 * 2:
        return "eoa_7702"
    return "unknown"


def main():
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    c = EtherscanClient(os.getenv("ETHERSCAN_API_KEY"), ROOT / "data/cache/view2")
    roles = {a: "operator" for a in read(ROOT / "data/raw/daas/operator_accounts.log")}
    roles.update({a: "affiliate" for a in read(ROOT / "data/raw/daas/affiliate_accounts.log")})
    addrs = sorted(roles)
    print("tong dia chi:", len(addrs))

    created, msgs = {}, set()
    for i in range(0, len(addrs), 5):
        try:
            for r in c.contract_creation(addrs[i:i + 5]):
                created[r["contractAddress"].lower()] = int(r["timestamp"])
        except EtherscanError as ex:
            msgs.add(str(ex)[:120])
        if (i // 5) % 200 == 0:
            print(f"[1] {min(i + 5, len(addrs))}/{len(addrs)}")
    if msgs:
        print("thong bao loi / khong co du lieu:", msgs)

    rows = []
    rest = [a for a in addrs if a not in created]
    for k, a in enumerate(rest):
        code = (c.query(module="proxy", action="eth_getCode", address=a, tag="latest").get("result") or "0x").lower()
        rows.append({"address": a, "role": roles[a], "kind": classify(code),
                     "code_len": (len(code) - 2) // 2, "creation_ts": None})
        if k % 500 == 0:
            print(f"[2] {k}/{len(rest)}")
    rows += [{"address": a, "role": roles[a], "kind": "contract", "code_len": None, "creation_ts": t}
             for a, t in created.items()]

    df = pd.DataFrame(rows)
    (ROOT / "data/interim").mkdir(parents=True, exist_ok=True)
    df.to_csv(ROOT / "data/interim/daas_account_types.csv", index=False)
    tab = pd.crosstab(df.role, df.kind, margins=True)
    (ROOT / "reports/daas").mkdir(parents=True, exist_ok=True)
    tab.to_csv(ROOT / "reports/daas/s02_account_types_summary.csv")
    non = df[~df.kind.isin(["eoa", "eoa_7702"])][["address", "role", "kind", "code_len", "creation_ts"]]
    non.to_csv(ROOT / "reports/daas/s02_non_eoa.csv", index=False)
    print(tab.to_string())
    print("\nkhong phai EOA:\n" + non.to_string(index=False))
    print(f"\ngoi mang: {c.n_network_calls} | cache: {c.n_cache_hits}")


if __name__ == "__main__":
    main()
