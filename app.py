"""Dashboard perkembangan saham Indonesia berbasis data Yahoo Finance."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
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
import sqlite3
import threading

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "portfolio_demo.sqlite3"
INITIAL_CASH = 100_000_000
DB_LOCK = threading.Lock()

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
        "market_time": meta.get("regularMarketTime"), "is_available": True,
    }


def unavailable_quote():
    return {"price": None, "previous": None, "change": None, "change_pct": None,
            "high": None, "low": None, "volume": None, "spark": [], "candles": [],
            "currency": "IDR", "market_time": None, "is_available": False}


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
                fetched[code] = unavailable_quote()
    try:
        index = yahoo_chart("^JKSE")
        index["symbol"] = "^JKSE"
    except Exception:
        index = {**unavailable_quote(), "symbol": "^JKSE"}
    rows = [{"symbol": code, "name": name, **fetched[code]} for code, name in items]
    available_count = sum(bool(q.get("is_available")) for q in rows) + int(bool(index.get("is_available")))
    if available_count == len(rows) + 1:
        source = "Yahoo Finance · BEI tertunda sekitar 10 menit"
        status = "delayed"
    elif available_count == 0:
        source = "Yahoo Finance tidak dapat diakses · kutipan belum tersedia"
        status = "unavailable"
    else:
        source = "Yahoo Finance · sebagian kutipan belum tersedia · BEI tertunda sekitar 10 menit"
        status = "partial"
    data = {"index": index, "stocks": rows, "source": source,
            "status": status, "available_count": available_count,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "is_available": available_count > 0}
    _cache.update(at=time(), data=data)
    return data


def db_connect():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def db_session():
    conn = db_connect()
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def init_portfolio():
    with db_session() as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS wallet (id INTEGER PRIMARY KEY CHECK(id=1), cash INTEGER NOT NULL)")
        conn.execute("INSERT OR IGNORE INTO wallet(id, cash) VALUES (1, ?)", (INITIAL_CASH,))
        conn.execute("""CREATE TABLE IF NOT EXISTS holdings (
            symbol TEXT PRIMARY KEY, lots INTEGER NOT NULL CHECK(lots >= 0), avg_price REAL NOT NULL CHECK(avg_price >= 0)
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT, symbol TEXT NOT NULL, side TEXT NOT NULL CHECK(side IN ('BUY','SELL')),
            lots INTEGER NOT NULL, price REAL NOT NULL, total INTEGER NOT NULL, created_at TEXT NOT NULL
        )""")


def portfolio_snapshot():
    market = market_data()
    quotes = {item["symbol"]: item for item in market["stocks"]}
    with DB_LOCK, db_session() as conn:
        cash = conn.execute("SELECT cash FROM wallet WHERE id=1").fetchone()["cash"]
        holdings = conn.execute("SELECT symbol, lots, avg_price FROM holdings WHERE lots > 0 ORDER BY symbol").fetchall()
        trades = conn.execute("SELECT id, symbol, side, lots, price, total, created_at FROM trades ORDER BY id DESC LIMIT 100").fetchall()
    positions = []
    for row in holdings:
        quote = quotes.get(row["symbol"])
        available = bool(quote and quote.get("is_available"))
        price = quote["price"] if available else None
        positions.append({"symbol": row["symbol"], "name": quote["name"] if quote else row["symbol"],
                          "lots": row["lots"], "avg_price": row["avg_price"], "price": price,
                          "market_value": round(price * row["lots"] * 100) if available else None,
                          "unrealized": round((price - row["avg_price"]) * row["lots"] * 100) if available else None,
                          "is_available": available})
    mark_available = all(p["is_available"] for p in positions)
    return {"cash": cash, "initial_cash": INITIAL_CASH,
            "market_value": sum(p["market_value"] for p in positions) if mark_available else None,
            "mark_available": mark_available, "positions": positions,
            "trades": [dict(t) for t in trades], "market_status": market["status"]}


def execute_trade(payload):
    if not isinstance(payload, dict):
        raise ValueError("Data transaksi tidak valid.")
    symbol = str(payload.get("symbol", "")).upper().strip()
    side = str(payload.get("side", "")).upper().strip()
    try:
        lots = int(payload.get("lots", 0))
    except (TypeError, ValueError):
        raise ValueError("Jumlah lot harus berupa bilangan bulat.")
    names = dict(WATCHLIST)
    if symbol not in names:
        raise ValueError("Saham tidak tersedia di daftar pantauan.")
    if side not in ("BUY", "SELL"):
        raise ValueError("Pilih beli atau jual.")
    if lots < 1 or lots > 1_000_000:
        raise ValueError("Jumlah lot minimal 1 dan maksimal 1.000.000.")
    quote = next((s for s in market_data()["stocks"] if s["symbol"] == symbol), None)
    if not quote:
        raise ValueError("Kutipan harga saham tidak tersedia.")
    if not quote.get("is_available"):
        raise ValueError("Kutipan harga nyata tidak tersedia. Transaksi demo hanya bisa dilakukan saat feed pasar berhasil diakses.")
    price = float(quote["price"])
    total = int(round(price * lots * 100))
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    with DB_LOCK, db_session() as conn:
        conn.execute("BEGIN IMMEDIATE")
        cash = conn.execute("SELECT cash FROM wallet WHERE id=1").fetchone()["cash"]
        holding = conn.execute("SELECT lots, avg_price FROM holdings WHERE symbol=?", (symbol,)).fetchone()
        owned = holding["lots"] if holding else 0
        if side == "BUY":
            if total > cash:
                raise ValueError(f"Saldo tidak cukup. Dibutuhkan {total:,} rupiah, saldo {cash:,} rupiah.")
            new_lots = owned + lots
            avg_price = ((owned * holding["avg_price"] + lots * price) / new_lots) if holding else price
            conn.execute("UPDATE wallet SET cash=cash-? WHERE id=1", (total,))
            conn.execute("INSERT INTO holdings(symbol,lots,avg_price) VALUES(?,?,?) ON CONFLICT(symbol) DO UPDATE SET lots=excluded.lots, avg_price=excluded.avg_price",
                         (symbol, new_lots, avg_price))
        else:
            if lots > owned:
                raise ValueError(f"Lot tidak cukup untuk dijual. Anda memiliki {owned} lot {symbol}.")
            conn.execute("UPDATE wallet SET cash=cash+? WHERE id=1", (total,))
            if lots == owned:
                conn.execute("DELETE FROM holdings WHERE symbol=?", (symbol,))
            else:
                conn.execute("UPDATE holdings SET lots=lots-? WHERE symbol=?", (lots, symbol))
        conn.execute("INSERT INTO trades(symbol,side,lots,price,total,created_at) VALUES(?,?,?,?,?,?)",
                     (symbol, side, lots, price, total, now))
    return {"symbol": symbol, "name": names[symbol], "side": side, "lots": lots,
            "price": price, "total": total, "created_at": now}


def execute_sell_all():
    quotes = {item["symbol"]: item for item in market_data()["stocks"]}
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    with DB_LOCK, db_session() as conn:
        conn.execute("BEGIN IMMEDIATE")
        holdings = conn.execute("SELECT symbol, lots FROM holdings WHERE lots > 0 ORDER BY symbol").fetchall()
        if not holdings:
            raise ValueError("Tidak ada saham di dompet untuk dijual.")
        unavailable = [row["symbol"] for row in holdings
                       if row["symbol"] not in quotes or not quotes[row["symbol"]].get("is_available")]
        if unavailable:
            raise ValueError("Tidak bisa menjual semua: kutipan nyata belum tersedia untuk " + ", ".join(unavailable) + ".")
        results = []
        proceeds = 0
        for row in holdings:
            quote = quotes[row["symbol"]]
            price = float(quote["price"])
            total = int(round(price * row["lots"] * 100))
            proceeds += total
            conn.execute("INSERT INTO trades(symbol,side,lots,price,total,created_at) VALUES(?,?,?,?,?,?)",
                         (row["symbol"], "SELL", row["lots"], price, total, now))
            results.append({"symbol": row["symbol"], "lots": row["lots"], "price": price, "total": total})
        conn.execute("UPDATE wallet SET cash=cash+? WHERE id=1", (proceeds,))
        conn.execute("DELETE FROM holdings WHERE lots > 0")
    return {"sold": results, "proceeds": proceeds, "created_at": now}


init_portfolio()


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
        if path == "/api/portfolio":
            self.send_json(200, portfolio_snapshot())
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

    def send_json(self, status, data):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/api/trade/sell-all":
            try:
                result = execute_sell_all()
                self.send_json(200, {"ok": True, "result": result, "portfolio": portfolio_snapshot()})
            except ValueError as error:
                self.send_json(400, {"ok": False, "error": str(error)})
            return
        if path != "/api/trade":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length < 1 or length > 10_000:
                raise ValueError("Permintaan transaksi tidak valid.")
            payload = json.loads(self.rfile.read(length))
            trade = execute_trade(payload)
            self.send_json(200, {"ok": True, "trade": trade, "portfolio": portfolio_snapshot()})
        except (ValueError, json.JSONDecodeError) as error:
            self.send_json(400, {"ok": False, "error": str(error)})

    def log_message(self, fmt, *args):
        print(f"[{self.log_date_time_string()}] {fmt % args}")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    host = os.environ.get("HOST", "0.0.0.0")
    server = ThreadingHTTPServer((host, port), DashboardHandler)
    print(f"Pasar Hari Ini tersedia pada {host}:{port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer dihentikan.")
        server.server_close()
