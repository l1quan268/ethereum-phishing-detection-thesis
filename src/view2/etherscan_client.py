# File: src/view2/etherscan_client.py
"""
Etherscan API V2 client cho pipeline View 2.

Khac voi src/collect_etherscan.py:
- Cache theo HASH CUA TOAN BO THAM SO (tru apikey), khong chi theo (address, action, page).
  Doi startblock/endblock se khong doc nham cache cu.
- Lay theo khoang khoi [startblock, endblock]; neu so ban ghi cham tran `max_records`
  thi tu dong chia doi khoang khoi (khong cat cut am tham).
- Khong log apikey.

Endpoint dung (tai lieu: https://docs.etherscan.io/api-reference/endpoint/<action>.md):
  account/txlist, account/txlistinternal, account/tokentx, account/tokennfttx,
  contract/getcontractcreation (toi da 5 dia chi/lan), block/getblocknobytime,
  proxy/eth_getTransactionByHash.
"""
from __future__ import annotations

import hashlib
import json
import random
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

ETHERSCAN_V2_URL = "https://api.etherscan.io/v2/api"


class EtherscanError(RuntimeError):
    pass


class EtherscanClient:
    def __init__(self, api_key: str, cache_dir: Path, rate_limit: float = 2.0,
                 timeout: int = 20, max_retries: int = 5, chainid: int = 1,
                 session: Optional[requests.Session] = None):
        if not api_key:
            raise ValueError("ETHERSCAN_API_KEY rong")
        self.api_key = api_key
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.interval = 1.0 / rate_limit if rate_limit > 0 else 0.0
        self.timeout = timeout
        self.max_retries = max_retries
        self.chainid = chainid
        self.session = session or requests.Session()
        self._last = 0.0
        self.n_network_calls = 0
        self.n_cache_hits = 0

    # ------------------------------------------------------------------ core
    def _cache_path(self, params: Dict[str, Any]) -> Path:
        key = json.dumps(params, sort_keys=True, default=str)
        h = hashlib.sha1(key.encode()).hexdigest()
        return self.cache_dir / params.get("action", "x") / f"{h}.json"

    def query(self, **params: Any) -> Dict[str, Any]:
        params = {"chainid": self.chainid, **params}
        path = self._cache_path(params)
        if path.exists():
            self.n_cache_hits += 1
            return json.loads(path.read_text(encoding="utf-8"))

        backoff = 2.0
        last_err = ""
        for _ in range(self.max_retries):
            wait = self.interval - (time.time() - self._last)
            if wait > 0:
                time.sleep(wait)
            self._last = time.time()
            try:
                self.n_network_calls += 1
                r = self.session.get(ETHERSCAN_V2_URL, params={**params, "apikey": self.api_key},
                                     timeout=self.timeout)
                if r.status_code in (429, 500, 502, 503, 504):
                    last_err = f"HTTP {r.status_code}"
                    time.sleep(backoff + random.uniform(0, 0.5)); backoff *= 2
                    continue
                data = r.json()
                res = data.get("result")
                if str(data.get("status")) == "0" and isinstance(res, str) and "rate limit" in res.lower():
                    last_err = res
                    time.sleep(backoff + random.uniform(0, 0.5)); backoff *= 2
                    continue
                if not self._is_cacheable(data):
                    raise EtherscanError(f"{params.get('action')}: {str(res)[:200]}")
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(data), encoding="utf-8")
                return data
            except (requests.RequestException, ValueError) as ex:
                last_err = str(ex)
                time.sleep(backoff); backoff *= 2
        raise EtherscanError(f"{params.get('action')} that bai sau {self.max_retries} lan: {last_err[:200]}")

    @staticmethod
    def _is_cacheable(data: Dict[str, Any]) -> bool:
        """Chi cache ket qua hop le: status=1, hoac status=0 voi 'No transactions/records found'.
        Proxy (jsonrpc) tra ve 'result' khong co 'status'."""
        if "jsonrpc" in data:
            return "error" not in data
        if str(data.get("status")) == "1":
            return True
        msg = f"{data.get('message', '')} {data.get('result', '')}".lower()
        return "no transactions found" in msg or "no records found" in msg or "no token transfers" in msg

    # ------------------------------------------------------------- endpoints
    def contract_creation(self, addresses: List[str]) -> List[Dict[str, Any]]:
        if not 1 <= len(addresses) <= 5:
            raise ValueError("getcontractcreation nhan 1..5 dia chi/lan")
        d = self.query(module="contract", action="getcontractcreation",
                       contractaddresses=",".join(a.lower() for a in addresses))
        if str(d.get("status")) != "1" or not isinstance(d.get("result"), list):
            return []
        return d["result"]

    def block_by_time(self, ts: int, closest: str = "before") -> int:
        d = self.query(module="block", action="getblocknobytime", timestamp=int(ts), closest=closest)
        return int(d["result"])

    def tx_by_hash(self, tx_hash: str) -> Optional[Dict[str, Any]]:
        d = self.query(module="proxy", action="eth_getTransactionByHash", txhash=tx_hash)
        return d.get("result")

    def list_range(self, action: str, address: str, startblock: int, endblock: int,
                   offset: int = 1000, max_records: int = 10000, _depth: int = 0) -> Dict[str, Any]:
        """Lay toan bo ban ghi `action` cua `address` trong [startblock, endblock].

        Neu tong so ban ghi trong mot khoang >= max_records (tran nghi van cua API,
        CHUA kiem chung trong tai lieu chinh thuc) thi chia doi khoang khoi va lay lai.
        Tra ve {"rows": [...], "saturated_ranges": [(s, e), ...]}.
        """
        rows: List[Dict[str, Any]] = []
        page = 1
        while True:
            d = self.query(module="account", action=action, address=address.lower(),
                           startblock=startblock, endblock=endblock, page=page,
                           offset=offset, sort="asc")
            res = d.get("result") if str(d.get("status")) == "1" else []
            res = res if isinstance(res, list) else []
            rows.extend(res)
            if len(res) < offset:
                return {"rows": rows, "saturated_ranges": []}
            if page * offset >= max_records:
                break
            page += 1

        # Cham tran -> chia doi khoang khoi
        if startblock >= endblock:
            return {"rows": rows, "saturated_ranges": [(startblock, endblock)]}
        mid = (startblock + endblock) // 2
        left = self.list_range(action, address, startblock, mid, offset, max_records, _depth + 1)
        right = self.list_range(action, address, mid + 1, endblock, offset, max_records, _depth + 1)
        return {"rows": left["rows"] + right["rows"],
                "saturated_ranges": left["saturated_ranges"] + right["saturated_ranges"]}