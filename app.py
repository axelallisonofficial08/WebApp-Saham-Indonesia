"""Dashboard perkembangan saham Indonesia berbasis data Yahoo Finance."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse
from time import time
from urllib.error import URLError
from urllib.request import Request, urlopen
import json
import mimetypes
import os

ROOT = Path(__file__).resolve().parent

WATCHLIST = [
    ("BBCA", "Bank Central Asia"), ("BBRI", "Bank Rakyat Indonesia"),
    ("BMRI", "Bank Mandiri"), ("TLKM", "Telkom Indonesia"),
    ("ASII", "Astra International"), ("GOTO", "GoTo Gojek Tokopedia"),
    ("ANTM", "Aneka Tambang"), ("BRPT", "Barito Pacific"),
    ("BREN", "Barito Renewables Energy"), ("AMMN", "Amman Mineral"),
    ("ICBP", "Indofood CBP"), ("UNVR", "Unilever Indonesia"),
    ("ADRO", "Alamtri Resources Indonesia"), ("BFIN", "BFI Finance"),
    ("PGAS", "Perusahaan Gas Negara"),
]

SAMPLE = {
    "BBCA": (10125, 10075, 10400, 10000, 18200000), "BBRI": (3970, 4020, 4080, 3930, 96200000),
    "BMRI": (5425, 5350, 5500, 5300, 41300000), "TLKM": (3180, 3210, 3250, 3150, 35600000),
    "ASII": (5050, 4975, 5100, 4925, 26700000), "GOTO": (72, 70, 74, 69, 2100000000),
    "ANTM": (1745, 1695, 1780, 1680, 79800000), "BRPT": (1060, 1090, 1115, 1040, 112000000),
    "BREN": (7350, 7100, 7500, 7000, 9100000), "AMMN": (7650, 7800, 7900, 7525, 12700000),
    "ICBP": (11100, 11000, 11225, 10900, 3400000), "UNVR": (1880, 1910, 1940, 1855, 48300000),
    "ADRO": (2440, 2390, 2470, 2360, 52000000), "BFIN": (970, 955, 980, 945, 10500000),
    "PGAS": (1590, 1575, 1620, 1560, 22100000),
}


def yahoo_chart(symbol):
    """Ambil ringkasan dan candle intraday dari endpoint chart Yahoo Finance."""
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=1d&interval=5m"
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; SahamHariIni/1.0)"})
    with urlopen(req, timeout=7) as response:
        payload = json.loads(response.read())
    result = payload["chart"]["result"][0]
    meta = result["meta"]
    quote = result["indicators"]["quote"][0]
    timestamps = result.get("timestamp", [])
    closes = [v for v in quote.get("close", []) if v is not None]
    current = meta.get("regularMarketPrice") or (closes[-1] if closes else None)
    previous = meta.get("chartPreviousClose") or meta.get("previousClose")
    if current is None or previous is None:
        raise ValueError("Kutipan harga tidak tersedia")
    candles = []
    fields = [quote.get(key, []) for key in ("open", "high", "low", "close", "volume")]
    for i, stamp in enumerate(timestamps):
        values = [series[i] if i < len(series) else None for series in fields]
        opened, high, low, close, volume = values
        if all(v is None for v in values):
            continue
        candles.append({"time": stamp, "open": opened, "high": high, "low": low,
                        "close": close, "volume": volume or 0})
    return {
        "price": current, "previous": previous,
        "change": current - previous, "change_pct": (current / previous - 1) * 100,
        "high": meta.get("regularMarketDayHigh") or max(closes),
        "low": meta.get("regularMarketDayLow") or min(closes),
        "volume": meta.get("regularMarketVolume") or sum(v or 0 for v in quote.get("volume", [])),
        "spark": closes[-30:], "candles": candles, "currency": meta.get("currency", "IDR"),
        "market_time": meta.get("regularMarketTime"), "is_sample": False,
    }


def sample_quote(code):
    price, previous, high, low, volume = SAMPLE[code]
    return {"price": price, "previous": previous, "change": price - previous,
            "change_pct": (price / previous - 1) * 100, "high": high, "low": low,
            "volume": volume, "spark": [], "candles": [], "currency": "IDR", "market_time": None,
            "is_sample": True}


_cache = {"at": 0, "data": None}


def market_data():
    if _cache["data"] and time() - _cache["at"] < 60:
        return _cache["data"]
    items = [(code, name) for code, name in WATCHLIST]
    fetched = {}
    with ThreadPoolExecutor(max_workers=8) as pool:
        jobs = {pool.submit(yahoo_chart, f"{code}.JK"): code for code, _ in items}
        for job, code in jobs.items():
            try:
                fetched[code] = job.result(timeout=8)
            except Exception:
                fetched[code] = sample_quote(code)
    try:
        index = yahoo_chart("^JKSE")
        index["symbol"] = "^JKSE"
    except Exception:
        index = {"price": 7100.0, "previous": 7050.0, "change": 50.0,
                 "change_pct": 0.71, "high": 7125.0, "low": 7020.0,
                 "volume": 0, "spark": [], "currency": "IDR", "market_time": None,
                 "is_sample": True, "symbol": "^JKSE"}
    rows = [{"symbol": code, "name": name, **fetched[code]} for code, name in items]
    sample_count = sum(bool(q.get("is_sample")) for q in rows) + int(bool(index.get("is_sample")))
    if sample_count == 0:
        source = "Yahoo Finance · BEI tertunda sekitar 10 menit"
        status = "delayed"
    elif sample_count == len(rows) + 1:
        source = "Data contoh · koneksi ke penyedia harga gagal"
        status = "sample"
    else:
        source = f"Yahoo Finance + {sample_count} kutipan contoh · BEI tertunda sekitar 10 menit"
        status = "partial"
    data = {"index": index, "stocks": rows, "source": source,
            "status": status, "sample_count": sample_count,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "is_sample": sample_count > 0}
    _cache.update(at=time(), data=data)
    return data


class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/market":
            body = json.dumps(market_data()).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if path == "/":
            file_path = ROOT / "templates" / "index.html"
        elif path.startswith("/static/"):
            relative = Path(unquote(path.removeprefix("/static/")))
            file_path = (ROOT / "static" / relative).resolve()
            if ROOT / "static" not in file_path.parents:
                self.send_error(404)
                return
        else:
            self.send_error(404)
            return

        if not file_path.is_file():
            self.send_error(404)
            return
        body = file_path.read_bytes()
        content_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
        if content_type.startswith("text/") or content_type in ("application/javascript", "application/json"):
            content_type += "; charset=utf-8"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        print(f"[{self.log_date_time_string()}] {fmt % args}")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    server = ThreadingHTTPServer(("127.0.0.1", port), DashboardHandler)
    print(f"Pasar Hari Ini tersedia di http://127.0.0.1:{port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer dihentikan.")
        server.server_close()
