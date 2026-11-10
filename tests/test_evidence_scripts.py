"""Kiem tra ha tang luu bang chung (scripts/run.py), luat cache moi va S02/S04 (offline, khong goi API)."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.daas import s04_enrich_accounts  # noqa: E402
from scripts.daas.s02_account_types import classify  # noqa: E402
from src.view2.etherscan_client import EtherscanClient  # noqa: E402


def _run(tmp_path, body, *extra):
    pkg = tmp_path / "dummy_pkg"
    pkg.mkdir(exist_ok=True)
    (pkg / "__init__.py").write_text("")
    (pkg / "job.py").write_text(body)
    out = tmp_path / "out.txt"
    out.write_text("abc")
    env = {**os.environ, "PYTHONPATH": os.pathsep.join([str(tmp_path), str(ROOT)])}
    cmd = [sys.executable, "-m", "scripts.run", "--name", "t", "--runs-dir", str(tmp_path / "runs"),
           "--outputs", str(out), "--", "dummy_pkg.job", *extra]
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, env=env)
    assert (tmp_path / "runs").exists(), r.stderr
    run_dir = next((tmp_path / "runs").iterdir())
    return r, run_dir, json.loads((run_dir / "meta.json").read_text(encoding="utf-8"))


def test_run_ok_saves_stdout_and_meta(tmp_path):
    r, d, meta = _run(tmp_path, "import sys\nprint('xin chao', sys.argv[1:])\n", "--x", "1")
    assert r.returncode == 0
    assert "xin chao ['--x', '1']" in (d / "stdout.txt").read_text(encoding="utf-8")
    assert meta["status"] == "ok" and meta["args"] == ["--x", "1"]
    o = next(iter(meta["outputs"].values()))
    assert o["bytes"] == 3 and o["sha256"].startswith("ba7816bf")  # sha256("abc")


def test_run_records_failure(tmp_path):
    r, d, meta = _run(tmp_path, "raise RuntimeError('hong')\n")
    assert r.returncode == 1 and meta["status"].startswith("error")
    assert "RuntimeError" in (d / "stdout.txt").read_text(encoding="utf-8")


def test_meta_has_no_env_secrets(tmp_path):
    os.environ["ETHERSCAN_API_KEY"] = "SECRET_KEY_123"
    _, d, _ = _run(tmp_path, "print(1)\n")
    assert "SECRET_KEY_123" not in (d / "meta.json").read_text(encoding="utf-8")


def test_cache_rule_contract_creation_none():
    none = {"status": "0", "message": "No data found", "result": None}
    assert EtherscanClient._is_cacheable(none, "getcontractcreation")
    assert not EtherscanClient._is_cacheable(none, "txlist")
    rate = {"status": "0", "message": "NOTOK", "result": "Max rate limit reached"}
    assert not EtherscanClient._is_cacheable(rate, "getcontractcreation")


def test_classify():
    assert classify("0x") == "eoa"
    assert classify(None) == "eoa"
    assert classify("0xef0100" + "ab" * 20) == "eoa_7702"
    assert classify("0x6080604052") == "unknown"


def test_s04_offline(tmp_path):
    inp, out = tmp_path / "in", tmp_path / "out"
    inp.mkdir()
    pd.DataFrame({"address": ["a", "b"], "role": ["affiliate", "operator"],
                  "evidence_ts": [1_700_000_000, 1_710_000_000]}).to_csv(inp / "accounts.csv", index=False)
    pd.DataFrame({"target_address": ["a", "a", "a", "b"],
                  "tx_hash": ["h1", "h2", "h3", "h4"],
                  "timestamp": [1_699_000_000, 1_700_000_000, 1_700_000_100, 1_710_000_000]}
                 ).to_parquet(inp / "events.parquet")
    s04_enrich_accounts.main(["--in-dir", str(inp), "--out-dir", str(out)])
    e = pd.read_csv(inp / "accounts_enriched.csv").set_index("address")
    assert e.loc["a", "n_tx_before"] == 1 and e.loc["a", "n_tx_first_day"] == 2
    assert e.loc["b", "n_tx_before"] == 0
    m = pd.read_csv(out / "s04_evidence_by_month.csv")
    assert m.n_P.sum() == 2 and m.cum_pct.iloc[-1] == 100.0
