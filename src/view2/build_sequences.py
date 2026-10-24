#!/usr/bin/env python3
# File: src/view2/build_sequences.py
"""
View 2 - Giai doan B: su kien tho -> chuoi giao dich point-in-time.

Dau vao : creation.parquet, events.parquet (giai doan A), labels CSV (address,label_status[,label_source])
Dau ra  : data/processed/view2/
          view2_sequences.npz   X_num [N,L,F] float32, X_dir [N,L] int64, X_method [N,L] int64,
                                mask [N,L] uint8   (KHONG chua nhan)
          view2_metadata.csv    address, split, label_status, obs_start, cutoff, seq_len, ...
          view2_spec.json       ten dac trung, tu vung, tham so chuan hoa (fit tren train)
          view2_report.md       thong ke do dai chuoi theo nhan + tieu chi dung

Quy tac (xem docs/VIEW2_PIPELINE_VI.md):
 1. observation_start = min(T_creation, su kien dau tien cham toi dia chi)
    cutoff            = observation_start + window      ; giu su kien obs_start <= t < cutoff
 2. Moi phan tu chuoi = 1 GIAO DICH (tx_hash). Su kien internal/token cua cung giao dich
    duoc tong hop thanh dac trung cua giao dich do; KHONG cong ETH voi so luong token.
 3. Thu tu: block_number -> tx_index. Thieu tx_index trong block co >1 giao dich => order_uncertain=1.
 4. Delta t cua phan tu dau = 0 kem dt_mask=0 (khong nham voi khoang cach that = 0).
 5. log1p cho so tien/khoang cach/so dem; chuan hoa z-score CHI fit tren split=train.
 6. method_id: tu vung fit tren train; --method-policy keep|drop|mask_keywords
    (positive SIGMETRICS duoc phat hien nho ten ham khop tu khoa => can ablation).
 7. Nhan chi nam trong metadata, khong nam trong tensor.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]

DIR_VOCAB = {"<pad>": 0, "in": 1, "out": 2, "self": 3, "create": 4, "indirect": 5}
METHOD_SPECIAL = {"<pad>": 0, "<none>": 1, "<unk>": 2}
CONT_FEATS = ["log_eth_in", "log_eth_out", "log_dt", "log_age", "log_gas",
              "log_n_internal", "log_n_tok_in", "log_n_tok_out", "log_n_tok_distinct"]
BIN_FEATS = ["is_error", "is_pre_deploy", "dt_mask", "gas_known", "order_uncertain"]
NUM_FEATS = CONT_FEATS + BIN_FEATS
# dac trung lien tuc chi co nghia khi co co tuong ung = 1
COND_MASK = {"log_dt": "dt_mask", "log_gas": "gas_known"}


# ----------------------------------------------------------------- windows
def compute_windows(creation: pd.DataFrame, events: pd.DataFrame, window_s: int,
                    max_lookback_s: Optional[int] = None) -> pd.DataFrame:
    first = events.groupby("target_address")["timestamp"].min().rename("first_event_ts")
    w = creation[["address", "creation_tx", "creation_ts"]].merge(
        first, left_on="address", right_index=True, how="left")
    w["obs_start"] = w[["creation_ts", "first_event_ts"]].min(axis=1).astype("int64")
    if max_lookback_s is not None:
        w["obs_start"] = np.maximum(w["obs_start"], w["creation_ts"] - max_lookback_s)
    w["cutoff"] = w["obs_start"] + window_s
    w["pre_deploy_lead_s"] = w["creation_ts"] - w["obs_start"]
    return w


def filter_window(events: pd.DataFrame, windows: pd.DataFrame) -> pd.DataFrame:
    e = events.merge(windows[["address", "obs_start", "cutoff", "creation_ts", "creation_tx"]],
                     left_on="target_address", right_on="address", how="inner")
    keep = (e["timestamp"] >= e["obs_start"]) & (e["timestamp"] < e["cutoff"])
    return e[keep].drop(columns=["address"]).reset_index(drop=True)


DEDUP_KEYS = {
    "normal": ["target_address", "tx_hash"],
    "internal": ["target_address", "tx_hash", "trace_id", "from_address", "to_address", "value_raw", "call_type"],
    "erc20": ["target_address", "tx_hash", "token_address", "from_address", "to_address", "value_raw"],
    "erc721": ["target_address", "tx_hash", "token_address", "from_address", "to_address", "value_raw"],
}


def dedupe(events: pd.DataFrame):
    parts, dropped = [], 0
    for src, g in events.groupby("source", sort=False):
        keys = [k for k in DEDUP_KEYS.get(src, ["target_address", "tx_hash"]) if k in g.columns]
        d = g.drop_duplicates(subset=keys)
        dropped += len(g) - len(d)
        parts.append(d)
    out = pd.concat(parts, ignore_index=True) if parts else events.iloc[0:0]
    return out, dropped


# ---------------------------------------------------------------- elements
def _wei_to_eth(v) -> float:
    try:
        return int(str(v)) / 1e18
    except (TypeError, ValueError):
        return 0.0


def build_elements(ev: pd.DataFrame) -> pd.DataFrame:
    """1 dong / (target_address, tx_hash)."""
    if ev.empty:
        return pd.DataFrame(columns=["target_address", "tx_hash"])
    e = ev.copy()
    tgt = e["target_address"]
    is_eth = e["source"].isin(["normal", "internal"]) & (e["is_error"] == 0)
    eth = e["value_raw"].map(_wei_to_eth)
    e["_eth_in"] = np.where(is_eth & (e["to_address"] == tgt), eth, 0.0)
    e["_eth_out"] = np.where(is_eth & (e["from_address"] == tgt), eth, 0.0)
    tok = e["source"].isin(["erc20", "erc721"])
    e["_tok_in"] = (tok & (e["to_address"] == tgt)).astype(int)
    e["_tok_out"] = (tok & (e["from_address"] == tgt)).astype(int)
    e["_tok_addr"] = np.where(tok, e["token_address"], None)
    e["_internal"] = (e["source"] == "internal").astype(int)
    e["_err"] = (e["source"].isin(["normal", "internal"]) & (e["is_error"] == 1)).astype(int)
    e["_create"] = ((e["contract_created"] == tgt) | (e["tx_hash"] == e["creation_tx"])).astype(int)
    nrm = e["source"] == "normal"
    e["_n_in"] = (nrm & (e["to_address"] == tgt)).astype(int)
    e["_n_out"] = (nrm & (e["from_address"] == tgt)).astype(int)
    e["_mid"] = np.where(nrm & (e["to_address"] == tgt), e["method_id"], "")
    e["_fn"] = np.where(nrm & (e["to_address"] == tgt), e["function_name"], "")
    e["_gas"] = np.where(nrm, e["gas_used"].astype("float"), np.nan)

    g = e.groupby(["target_address", "tx_hash"], sort=False)
    el = g.agg(block_number=("block_number", "min"), timestamp=("timestamp", "min"),
               tx_index=("tx_index", "min"), creation_ts=("creation_ts", "first"),
               obs_start=("obs_start", "first"),
               eth_in=("_eth_in", "sum"), eth_out=("_eth_out", "sum"),
               n_internal=("_internal", "sum"), n_tok_in=("_tok_in", "sum"),
               n_tok_out=("_tok_out", "sum"), n_tok_distinct=("_tok_addr", "nunique"),
               is_error=("_err", "max"), is_create=("_create", "max"),
               n_in=("_n_in", "max"), n_out=("_n_out", "max"),
               method_id=("_mid", "max"), function_name=("_fn", "max"),
               gas_used=("_gas", "max"),
               in_sigmetrics_tx_log=("in_sigmetrics_tx_log", "max")).reset_index()

    el["direction"] = np.select(
        [el["is_create"] == 1, (el["n_in"] == 1) & (el["n_out"] == 1), el["n_out"] == 1, el["n_in"] == 1],
        ["create", "self", "out", "in"], default="indirect")
    el["is_pre_deploy"] = (el["timestamp"] < el["creation_ts"]).astype(int)

    # thu tu: block -> tx_index; NA xep cuoi block va gan co order_uncertain
    el["_txi"] = el["tx_index"].astype("float").fillna(np.inf)
    el = el.sort_values(["target_address", "block_number", "_txi", "tx_hash"]).reset_index(drop=True)
    blk_n = el.groupby(["target_address", "block_number"])["tx_hash"].transform("size")
    blk_na = el.groupby(["target_address", "block_number"])["tx_index"].transform(lambda s: s.isna().any())
    el["order_uncertain"] = ((blk_n > 1) & blk_na).astype(int)

    el["dt"] = el.groupby("target_address")["timestamp"].diff()
    el["dt_mask"] = el["dt"].notna().astype(int)
    el["dt"] = el["dt"].fillna(0).clip(lower=0)
    el["age"] = (el["timestamp"] - el["obs_start"]).clip(lower=0)
    el["gas_known"] = el["gas_used"].notna().astype(int)

    el["log_eth_in"] = np.log1p(el["eth_in"])
    el["log_eth_out"] = np.log1p(el["eth_out"])
    el["log_dt"] = np.log1p(el["dt"])
    el["log_age"] = np.log1p(el["age"])
    el["log_gas"] = np.log1p(el["gas_used"].fillna(0))
    for c in ["n_internal", "n_tok_in", "n_tok_out", "n_tok_distinct"]:
        el[f"log_{c}"] = np.log1p(el[c])
    return el.drop(columns=["_txi"])


# ------------------------------------------------------------------- splits
def _ts(s: Optional[str]) -> Optional[int]:
    if not s:
        return None
    return int(datetime.fromisoformat(s.replace("Z", "+00:00")).replace(tzinfo=timezone.utc).timestamp())


def assign_split(windows: pd.DataFrame, t1: Optional[int], t2: Optional[int]) -> pd.Series:
    """train: cutoff <= T1 ; val: obs_start >= T1 & cutoff <= T2 ; test: obs_start >= T2 ; con lai: gap.
    Dia chi co cua so vat qua T1/T2 bi loai (gap) de khong co du lieu nao cua train nam sau T1."""
    if t1 is None or t2 is None:
        return pd.Series("all", index=windows.index)
    s = np.select([windows["cutoff"] <= t1,
                   (windows["obs_start"] >= t1) & (windows["cutoff"] <= t2),
                   windows["obs_start"] >= t2], ["train", "val", "test"], default="gap")
    return pd.Series(s, index=windows.index)


# ------------------------------------------------------------ fit on train
def fit_normalizer(el_train: pd.DataFrame) -> Dict[str, Dict[str, float]]:
    stats = {}
    for c in CONT_FEATS:
        v = el_train[c]
        if c in COND_MASK:
            v = v[el_train[COND_MASK[c]] == 1]
        mu = float(v.mean()) if len(v) else 0.0
        sd = float(v.std(ddof=0)) if len(v) else 1.0
        stats[c] = {"mean": mu, "std": sd if sd > 1e-12 else 1.0}
    return stats


def load_keywords(path: Path) -> List[str]:
    return [l.strip().lower() for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def _fn_name(fn: str) -> str:
    return re.split(r"[(\s]", str(fn or ""), maxsplit=1)[0].lower()


def apply_method_policy(el: pd.DataFrame, policy: str, keywords: List[str]) -> pd.Series:
    mid = el["method_id"].fillna("").astype(str)
    if policy == "keep":
        return mid
    if policy == "drop":
        return pd.Series("", index=el.index)
    if policy == "mask_keywords":
        # Xap xi heuristic cua bai bao bang chuoi con (bai bao dung them Levenshtein.ratio > 0.8).
        hit = el["function_name"].map(lambda f: any(k in _fn_name(f) for k in keywords))
        return mid.where(~hit, "")
    raise ValueError(policy)


def build_method_vocab(train_ids: pd.Series, min_count: int = 1) -> Dict[str, int]:
    vc = train_ids[train_ids != ""].value_counts()
    vocab = dict(METHOD_SPECIAL)
    for m in sorted(vc[vc >= min_count].index, key=lambda m: (-vc[m], m)):
        vocab[m] = len(vocab)
    return vocab


# ----------------------------------------------------------------- tensors
def to_tensors(el: pd.DataFrame, addresses: List[str], stats, method_vocab, max_len: int):
    N, F = len(addresses), len(NUM_FEATS)
    X = np.zeros((N, max_len, F), np.float32)
    D = np.zeros((N, max_len), np.int64)
    M = np.zeros((N, max_len), np.int64)
    mask = np.zeros((N, max_len), np.uint8)
    info = []
    groups = {a: g for a, g in el.groupby("target_address", sort=False)} if len(el) else {}
    for i, a in enumerate(addresses):
        g = groups.get(a)
        n_raw = 0 if g is None else len(g)
        if n_raw:
            g = g.iloc[-max_len:]  # giu L giao dich gan cutoff nhat
            n = len(g)
            cols = []
            for c in NUM_FEATS:
                v = g[c].to_numpy(np.float64)
                if c in stats:
                    v = (v - stats[c]["mean"]) / stats[c]["std"]
                    if c in COND_MASK:
                        v = np.where(g[COND_MASK[c]].to_numpy() == 1, v, 0.0)
                cols.append(v)
            X[i, -n:] = np.stack(cols, axis=1)
            D[i, -n:] = g["direction"].map(DIR_VOCAB).to_numpy()
            M[i, -n:] = [method_vocab.get(m, METHOD_SPECIAL["<unk>"]) if m else METHOD_SPECIAL["<none>"]
                         for m in g["method_id_policy"]]
            mask[i, -n:] = 1
        else:
            n = 0
        info.append({"address": a, "seq_len_raw": n_raw, "seq_len": n, "truncated": int(n_raw > max_len),
                     "n_pre_deploy": 0 if g is None else int(g["is_pre_deploy"].sum()),
                     "n_order_uncertain": 0 if g is None else int(g["order_uncertain"].sum()),
                     "n_in_sigmetrics_tx_log": 0 if g is None else int(g["in_sigmetrics_tx_log"].sum())})
    return X, D, M, mask, pd.DataFrame(info)


# -------------------------------------------------------------------- run
def run(creation: pd.DataFrame, events: pd.DataFrame, labels: pd.DataFrame, *, window_days: int = 7,
        max_len: int = 256, t1: Optional[str] = None, t2: Optional[str] = None,
        method_policy: str = "keep", keywords: Optional[List[str]] = None,
        max_lookback_days: Optional[int] = None, min_method_count: int = 1):
    creation = creation.assign(address=creation["address"].str.lower())
    events = events.assign(target_address=events["target_address"].str.lower())
    labels = labels.assign(address=labels["address"].str.lower())

    windows = compute_windows(creation, events, window_days * 86400,
                              None if max_lookback_days is None else max_lookback_days * 86400)
    windows["split"] = assign_split(windows, _ts(t1), _ts(t2))
    ev = filter_window(events, windows)
    ev, n_dup = dedupe(ev)
    el = build_elements(ev)
    if len(el):
        el = el.merge(windows[["address", "split"]], left_on="target_address", right_on="address").drop(columns="address")
        el["method_id_policy"] = apply_method_policy(el, method_policy, keywords or [])

    fit_split = "train" if (windows["split"] == "train").any() else "all"
    if fit_split == "all":
        print("[WARN] Khong co split train (thieu --t1/--t2): chuan hoa va tu vung fit tren TOAN BO du lieu. "
              "Chi dung de kiem tra pipeline, khong dung cho danh gia.")
    el_fit = el[el["split"] == fit_split] if len(el) else el
    stats = fit_normalizer(el_fit) if len(el_fit) else {c: {"mean": 0.0, "std": 1.0} for c in CONT_FEATS}
    vocab = build_method_vocab(el_fit["method_id_policy"] if len(el_fit) else pd.Series(dtype=str),
                               min_method_count)

    keep_addr = windows.loc[windows["split"] != "gap", "address"].tolist()
    X, D, M, mask, info = to_tensors(el, keep_addr, stats, vocab, max_len)

    # info giu dung thu tu hang cua tensor
    meta = (info.merge(windows, on="address", how="left")
            .merge(labels, on="address", how="left"))
    meta["label_status"] = meta["label_status"].fillna("unknown")
    spec = {"num_features": NUM_FEATS, "continuous_features": CONT_FEATS, "binary_features": BIN_FEATS,
            "conditional_masks": COND_MASK, "direction_vocab": DIR_VOCAB, "method_vocab": vocab,
            "method_policy": method_policy, "normalizer": stats, "normalizer_fit_split": fit_split,
            "max_len": max_len, "padding": "left", "window_days": window_days,
            "max_lookback_days": max_lookback_days, "t1": t1, "t2": t2,
            "n_duplicates_dropped": int(n_dup)}
    return {"X_num": X, "X_dir": D, "X_method": M, "mask": mask}, meta, spec, el


def length_report(meta: pd.DataFrame, stop_median: int = 3) -> str:
    lines = ["# View 2 - Bao cao do dai chuoi", "",
             "| label_status | n | min | median | mean | max | seq_len=0 | co su kien truoc deploy |",
             "|---|---|---|---|---|---|---|---|"]
    for lab, g in meta.groupby("label_status"):
        s = g["seq_len_raw"]
        lines.append(f"| {lab} | {len(g)} | {s.min()} | {s.median():.1f} | {s.mean():.1f} | {s.max()} | "
                     f"{(s == 0).sum()} | {(g['n_pre_deploy'] > 0).sum()} |")
    lines.append("")
    pos = meta.loc[meta["label_status"] == "positive", "seq_len_raw"]
    if len(pos) and pos.median() <= stop_median:
        lines.append(f"**CANH BAO (tieu chi dung):** trung vi do dai chuoi positive = {pos.median():.1f} "
                     f"<= {stop_median}. Chuoi qua ngan de mo hinh hoa theo thoi gian; can nhac chuyen "
                     f"thanh dac trung tinh (View 1) hoac chuyen sang cap tai khoan.")
    lines.append("")
    lines.append("Chenh lech do dai giua P va U la nguon hoc duong tat tiem an: "
                 "bao cao ket qua theo nhom do dai va/hoac ghep U theo muc do hoat dong.")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--in-dir", default=str(ROOT / "data/interim/view2"))
    ap.add_argument("--labels", required=True, help="CSV: address,label_status[,label_source]")
    ap.add_argument("--out-dir", default=str(ROOT / "data/processed/view2"))
    ap.add_argument("--window-days", type=int, default=7)
    ap.add_argument("--max-len", type=int, default=256)
    ap.add_argument("--t1", help="ISO UTC, vd 2024-06-01T00:00:00Z")
    ap.add_argument("--t2", help="ISO UTC")
    ap.add_argument("--method-policy", choices=["keep", "drop", "mask_keywords"], default="keep")
    ap.add_argument("--keywords", default=str(ROOT / "data/raw/suspicious_keywords.log"))
    ap.add_argument("--max-lookback-days", type=int, default=None)
    ap.add_argument("--min-method-count", type=int, default=1)
    a = ap.parse_args()

    in_dir, out = Path(a.in_dir), Path(a.out_dir)
    kw = []
    if a.method_policy == "mask_keywords":
        if not Path(a.keywords).exists():
            sys.exit(f"Thieu {a.keywords} cho --method-policy mask_keywords")
        kw = load_keywords(Path(a.keywords))
    labels = pd.read_csv(a.labels)
    labels = labels[[c for c in ["address", "label_status", "label_source"] if c in labels.columns]]

    tensors, meta, spec, _ = run(pd.read_parquet(in_dir / "creation.parquet"),
                                 pd.read_parquet(in_dir / "events.parquet"), labels,
                                 window_days=a.window_days, max_len=a.max_len, t1=a.t1, t2=a.t2,
                                 method_policy=a.method_policy, keywords=kw,
                                 max_lookback_days=a.max_lookback_days, min_method_count=a.min_method_count)
    out.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out / "view2_sequences.npz", **tensors,
                        address=np.array(meta["address"].tolist()))
    meta.to_csv(out / "view2_metadata.csv", index=False)
    (out / "view2_spec.json").write_text(json.dumps(spec, indent=2, ensure_ascii=False), encoding="utf-8")
    rep = length_report(meta)
    (out / "view2_report.md").write_text(rep, encoding="utf-8")
    print(rep)
    print(f"\n[OK] {len(meta)} dia chi -> {out}")


if __name__ == "__main__":
    main()