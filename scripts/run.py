#!/usr/bin/env python3
"""
Chay mot module Python va LUU BANG CHUNG vao reports/runs/<thoi_diem>_<ten>/.

    python -m scripts.run --name <ten_ngan> [--inputs tep ...] [--outputs tep ...] -- <module> [tham so cua module]

BAT BUOC co '--' truoc <module>: neu thieu, --inputs/--outputs se nuot luon ten module.

Vi du:
    python -m scripts.run --name daas_contract_creation \
        --inputs data/raw/daas/profit_sharing_contracts.log \
        --outputs data/interim/daas_contract_creation.csv \
        -- scripts.daas.s01_contract_creation

Moi lan chay tao:
    stdout.txt  toan bo output man hinh (stdout + stderr)
    meta.json   thoi diem, git commit/nhanh/co thay doi chua commit, lenh, phien ban Python va thu vien,
                SHA-256 + kich thuoc cua tep dau vao/dau ra, trang thai, thoi gian chay

Ten .txt (khong phai .log) vi .gitignore dang bo qua *.log.
Khong ghi API key: chi luu tham so dong lenh, khong luu bien moi truong.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import runpy
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGES = ["pandas", "numpy", "pyarrow", "requests", "python-dotenv", "pytest"]


class Tee:
    def __init__(self, *streams):
        self.streams = streams

    def write(self, x):
        for s in self.streams:
            s.write(x)
            s.flush()

    def flush(self):
        for s in self.streams:
            s.flush()


def git(*args):
    try:
        return subprocess.check_output(["git", *args], cwd=ROOT, text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return None


def file_info(p: str) -> dict:
    path = (ROOT / p) if not Path(p).is_absolute() else Path(p)
    if not path.exists():
        return {"exists": False}
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return {"exists": True, "bytes": path.stat().st_size, "sha256": h.hexdigest()}


def versions() -> dict:
    out = {}
    for p in PACKAGES:
        try:
            out[p] = metadata.version(p)
        except metadata.PackageNotFoundError:
            out[p] = None
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--name", required=True, help="ten ngan, vd daas_account_types")
    ap.add_argument("--inputs", nargs="*", default=[], help="tep dau vao can ghi SHA-256")
    ap.add_argument("--outputs", nargs="*", default=[], help="tep dau ra can ghi SHA-256")
    ap.add_argument("--runs-dir", default="reports/runs", help="thu muc luu bang chung (mac dinh reports/runs)")
    ap.add_argument("module", help="module chay bang python -m, vd scripts.daas.s01_contract_creation")
    ap.add_argument("args", nargs=argparse.REMAINDER, help="tham so chuyen cho module")
    a = ap.parse_args()

    started = datetime.now(timezone.utc)
    runs_dir = Path(a.runs_dir) if Path(a.runs_dir).is_absolute() else ROOT / a.runs_dir
    run_dir = runs_dir / f"{started.strftime('%Y-%m-%dT%H%M%SZ')}_{a.name}"
    run_dir.mkdir(parents=True, exist_ok=True)
    meta = {
        "name": a.name,
        "module": a.module,
        "args": a.args,
        "command": f"python -m {a.module} " + " ".join(a.args),
        "started_utc": started.isoformat(),
        "git_commit": git("rev-parse", "HEAD"),
        "git_branch": git("rev-parse", "--abbrev-ref", "HEAD"),
        "git_dirty": bool(git("status", "--porcelain")),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "packages": versions(),
        "inputs": {p: file_info(p) for p in a.inputs},
    }

    log = open(run_dir / "stdout.txt", "w", encoding="utf-8")
    old_out, old_err, old_argv = sys.stdout, sys.stderr, sys.argv
    sys.stdout, sys.stderr = Tee(old_out, log), Tee(old_err, log)
    sys.argv = [a.module] + a.args
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    t0, status = time.time(), "ok"
    try:
        runpy.run_module(a.module, run_name="__main__", alter_sys=True)
    except SystemExit as e:
        status = "ok" if e.code in (0, None) else f"exit {e.code}"
    except Exception as e:  # noqa: BLE001
        status = f"error: {e!r}"
        traceback.print_exc()
    finally:
        sys.stdout, sys.stderr, sys.argv = old_out, old_err, old_argv
        log.close()

    meta.update({
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "duration_s": round(time.time() - t0, 1),
        "status": status,
        "outputs": {p: file_info(p) for p in a.outputs},
    })
    (run_dir / "meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[run] {status} ({meta['duration_s']} s) -> {run_dir}")
    sys.exit(0 if status == "ok" else 1)


if __name__ == "__main__":
    main()
