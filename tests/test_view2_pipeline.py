# File: tests/test_view2_pipeline.py
"""Kiem thu pipeline View 2 (src/view2). Chay: pytest tests/test_view2_pipeline.py -q"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.view2.build_sequences import (NUM_FEATS, assign_split, build_elements, compute_windows,  # noqa: E402
                                       dedupe, filter_window, run)
from src.view2.etherscan_client import EtherscanClient  # noqa: E402

DAY = 86400
A, B = "0x" + "a" * 40, "0x" + "b" * 40
VICTIM, FACTORY, X = "0x" + "1" * 40, "0x" + "2" * 40, "0x" + "3" * 40
WEI = 10 ** 18


def ev(target, source, h, block, ts, frm, to, value="0", tx_index=None, **kw):
    row = dict(target_address=target, source=source, tx_hash=h, block_number=block, timestamp=ts,
               tx_index=tx_index, trace_id=kw.get("trace_id"), from_address=frm, to_address=to,
               value_raw=str(value), token_address=kw.get("token", ""), token_decimal=kw.get("dec"),
               method_id=kw.get("method_id", ""), function_name=kw.get("fn", ""),
               call_type=kw.get("call_type", ""), is_error=kw.get("is_error", 0),
               contract_created=kw.get("created", ""), gas_used=kw.get("gas"),
               in_sigmetrics_tx_log=kw.get("sig", False))
    return row


def frame(rows):
    df = pd.DataFrame(rows)
    df["tx_index"] = df["tx_index"].astype("Int64")
    df["gas_used"] = df["gas_used"].astype("Int64")
    return df


T0 = 1_700_000_000


@pytest.fixture
def toy():
    """A: nan nhan gui ETH 12s TRUOC khi hop dong duoc tao bang create2 (dia chi CREATE2), roi 1 giao dich
    sau cutoff. B: hop dong binh thuong, 3 giao dich."""
    rows = [
        ev(A, "normal", "0xh1", 100, T0 - 12, VICTIM, A, WEI // 10, 5, method_id="0xaad3ec96",
           fn="claim(address _buyer, uint256 _amount)", gas=50000, sig=True),
        ev(A, "internal", "0xh2", 101, T0, FACTORY, "", 0, None, trace_id="0", call_type="create2", created=A),
        ev(A, "normal", "0xh3", 500, T0 - 12 + 7 * DAY, VICTIM, A, WEI, 0),  # dung tai cutoff -> loai
        ev(B, "normal", "0xb1", 100, T0, X, "", 0, 1, created=B, gas=900000),
        ev(B, "normal", "0xb3", 102, T0 + 90, B, X, 2 * WEI, 0, gas=21000),
        ev(B, "normal", "0xb2", 102, T0 + 90, X, B, WEI, 3, method_id="0xa9059cbb", fn="transfer(address,uint256)", gas=30000),
        ev(B, "erc20", "0xb2", 102, T0 + 90, X, B, 10 ** 30, 3, token="0xtok", dec=18),
    ]
    creation = pd.DataFrame([
        {"address": A, "creation_tx": "0xh2", "creation_ts": T0},
        {"address": B, "creation_tx": "0xb1", "creation_ts": T0},
    ])
    labels = pd.DataFrame([{"address": A, "label_status": "positive"}, {"address": B, "label_status": "unlabeled"}])
    return creation, frame(rows), labels


def test_window_anchor_includes_pre_deploy_and_excludes_cutoff(toy):
    creation, events, _ = toy
    w = compute_windows(creation, events, 7 * DAY)
    wa = w.set_index("address").loc[A]
    assert wa.obs_start == T0 - 12 and wa.pre_deploy_lead_s == 12
    kept = filter_window(events, w)
    a_hashes = set(kept.loc[kept.target_address == A, "tx_hash"])
    assert a_hashes == {"0xh1", "0xh2"}          # 0xh3 nam dung tai cutoff -> bi loai (t < cutoff)


def test_max_lookback_limits_pre_deploy(toy):
    creation, events, _ = toy
    w = compute_windows(creation, events, 7 * DAY, max_lookback_s=5)
    assert w.set_index("address").loc[A, "obs_start"] == T0 - 5


def test_elements_order_direction_dt_and_no_eth_token_mixing(toy):
    creation, events, _ = toy
    el = build_elements(filter_window(events, compute_windows(creation, events, 7 * DAY)))
    a = el[el.target_address == A]
    assert a["direction"].tolist() == ["in", "create"]
    assert a["is_pre_deploy"].tolist() == [1, 0]
    assert a["dt_mask"].tolist() == [0, 1] and a["dt"].tolist() == [0, 12]
    b = el[el.target_address == B]
    # cung block 102: tx_index 0 (0xb3) truoc tx_index 3 (0xb2)
    assert b["tx_hash"].tolist() == ["0xb1", "0xb3", "0xb2"]
    b2 = b.set_index("tx_hash").loc["0xb2"]
    assert b2.eth_in == pytest.approx(1.0)       # 10**30 don vi token KHONG cong vao ETH
    assert b2.n_tok_in == 1 and b2.direction == "in"
    assert b.set_index("tx_hash").loc["0xb3"].eth_out == pytest.approx(2.0)


def test_order_uncertain_flag_when_tx_index_missing():
    rows = [ev(A, "internal", "0xp", 10, T0, FACTORY, A, 0, None, trace_id="0"),
            ev(A, "normal", "0xq", 10, T0, VICTIM, A, 0, 7)]
    creation = pd.DataFrame([{"address": A, "creation_tx": "", "creation_ts": T0}])
    events = frame(rows)
    el = build_elements(filter_window(events, compute_windows(creation, events, DAY)))
    assert el["tx_hash"].tolist() == ["0xq", "0xp"]          # NA xep cuoi block
    assert el["order_uncertain"].tolist() == [1, 1]


def test_dedupe_internal_and_normal():
    rows = [ev(A, "normal", "0xn", 1, T0, VICTIM, A, 1, 0)] * 2 + \
           [ev(A, "internal", "0xi", 1, T0, A, X, 5, None, trace_id="0_1")] * 3
    d, dropped = dedupe(frame(rows))
    assert len(d) == 2 and dropped == 3


def test_split_rules_gap_prevents_train_spilling_past_t1():
    w = pd.DataFrame({"obs_start": [0, 90, 100, 150, 210, 300], "cutoff": [50, 120, 140, 205, 260, 350]})
    assert assign_split(w, 100, 200).tolist() == ["train", "gap", "val", "gap", "test", "test"]


def test_normalizer_fit_only_on_train_and_labels_not_in_tensors(toy):
    creation, events, labels = toy
    t1, t2 = "2023-11-14T22:13:20Z", "2023-11-30T00:00:00Z"   # T0 = 2023-11-14T22:13:20Z
    # A, B deu bat dau tai/truoc T0 -> chinh lai de A la train, B la test
    creation2 = creation.copy()
    events2 = events.copy()
    shift = 40 * DAY
    events2.loc[events2.target_address == B, "timestamp"] += shift
    creation2.loc[creation2.address == B, "creation_ts"] += shift
    creation2.loc[creation2.address == A, "creation_ts"] -= 30 * DAY
    events2.loc[events2.target_address == A, "timestamp"] -= 30 * DAY

    T, meta, spec, _ = run(creation2, events2, labels, t1=t1, t2=t2)
    assert dict(zip(meta.address, meta.split)) == {A: "train", B: "test"}
    assert spec["normalizer_fit_split"] == "train"

    # doi gia tri cua dia chi test -> tham so chuan hoa khong doi
    events3 = events2.copy()
    events3.loc[events3.target_address == B, "value_raw"] = str(10 ** 24)
    _, _, spec3, _ = run(creation2, events3, labels, t1=t1, t2=t2)
    assert spec3["normalizer"] == spec["normalizer"]

    # dao nhan -> tensor giong het (nhan khong di vao tensor)
    flipped = labels.assign(label_status=labels.label_status.map({"positive": "unlabeled", "unlabeled": "positive"}))
    T2, _, _, _ = run(creation2, events2, flipped, t1=t1, t2=t2)
    for k in T:
        np.testing.assert_array_equal(T[k], T2[k])
    assert set(T) == {"X_num", "X_dir", "X_method", "mask"}


def test_padding_left_and_shapes(toy):
    creation, events, labels = toy
    T, meta, _, _ = run(creation, events, labels, max_len=4)
    assert T["X_num"].shape == (2, 4, len(NUM_FEATS))
    ia = meta.index[meta.address == A][0]
    assert T["mask"][ia].tolist() == [0, 0, 1, 1]
    assert (T["X_num"][ia][T["mask"][ia] == 0] == 0).all()


def test_method_policies(toy):
    creation, events, labels = toy
    _, _, spec_keep, el_keep = run(creation, events, labels, method_policy="keep")
    assert "0xaad3ec96" in spec_keep["method_vocab"]
    T_drop, _, spec_drop, _ = run(creation, events, labels, method_policy="drop")
    assert set(np.unique(T_drop["X_method"])) <= {0, 1}
    _, _, spec_mask, el_mask = run(creation, events, labels, method_policy="mask_keywords", keywords=["claim"])
    assert "0xaad3ec96" not in spec_mask["method_vocab"]      # claim(...) bi che
    assert "0xa9059cbb" in spec_mask["method_vocab"]          # transfer khong khop tu khoa


# ------------------------------------------------------------------ client
class FakeResp:
    def __init__(self, data):
        self.status_code, self._d = 200, data

    def json(self):
        return self._d


class FakeSession:
    """Moi block co `per_block` ban ghi; tra ve dung theo startblock/endblock/page/offset."""
    def __init__(self, per_block=3):
        self.per_block, self.calls = per_block, []

    def get(self, url, params, timeout):
        self.calls.append(dict(params))
        s, e, page, off = int(params["startblock"]), int(params["endblock"]), int(params["page"]), int(params["offset"])
        rows = [{"hash": f"0x{b:04d}{k}", "blockNumber": str(b)} for b in range(s, e + 1) for k in range(self.per_block)]
        chunk = rows[(page - 1) * off: page * off]
        if not chunk:
            return FakeResp({"status": "0", "message": "No transactions found", "result": []})
        return FakeResp({"status": "1", "message": "OK", "result": chunk})


def test_client_bisects_saturated_ranges_and_caches_by_params(tmp_path):
    sess = FakeSession(per_block=3)
    c = EtherscanClient("k", tmp_path, rate_limit=0, session=sess)
    res = c.list_range("txlist", A, 0, 9, offset=4, max_records=8)   # 30 ban ghi > tran 8
    hashes = [r["hash"] for r in res["rows"]]
    assert len(set(hashes)) == 30 and res["saturated_ranges"] == []
    assert all("apikey" not in json.loads(p.read_text()) for p in tmp_path.rglob("*.json"))
    n = c.n_network_calls
    c.list_range("txlist", A, 0, 9, offset=4, max_records=8)
    assert c.n_network_calls == n                                    # lan 2 doc cache
    queried = {(int(p["startblock"]), int(p["endblock"])) for p in sess.calls}
    assert (1, 6) not in queried
    c.list_range("txlist", A, 1, 6, offset=4, max_records=8)
    assert c.n_network_calls > n                                     # khoang moi -> khong dung nham cache


def test_client_reports_single_block_saturation(tmp_path):
    c = EtherscanClient("k", tmp_path, rate_limit=0, session=FakeSession(per_block=20))
    res = c.list_range("txlist", A, 5, 5, offset=4, max_records=8)
    assert res["saturated_ranges"] == [(5, 5)]


# ------------------------------------------------------------- pilot data
PILOT = ROOT / "data/pilot/combined/pilot_20_transactions_before_cutoff.parquet"


@pytest.mark.skipif(not PILOT.exists(), reason="Khong co du lieu pilot")
def test_pilot_recovers_pre_deploy_victim_calls():
    from src.view2.adapt_pilot import adapt
    creation, events = adapt(pd.read_parquet(PILOT), pd.read_csv(ROOT / "data/processed/view1/view1_metadata_pilot.csv"))
    labels = pd.read_csv(ROOT / "data/pilot/combined/pilot_20_addresses.csv")
    _, meta, _, _ = run(creation, events, labels)
    pos = meta[meta.label_status == "positive"]
    assert (pos.n_pre_deploy > 0).sum() == 4
    assert (meta.seq_len_raw > 0).all()