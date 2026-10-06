"""Fetch Yahoo Finance quotes and retain the most recent usable snapshot."""

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import ROOT, market_data

SNAPSHOT = ROOT / "data" / "market.json"


def read_previous():
    try:
        return json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def keep_last_good(current, previous):
    if current.get("is_available") and current.get("price") is not None:
        return {**current, "is_stale": False}
    if previous and previous.get("is_available") and previous.get("price") is not None:
        return {**previous, "is_available": True, "is_stale": True}
    return {**current, "is_stale": True}


def stable_json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def main():
    previous = read_previous()
    incoming = market_data()
    previous_stocks = {item["symbol"]: item for item in (previous or {}).get("stocks", [])}
    stocks = [keep_last_good(item, previous_stocks.get(item["symbol"])) for item in incoming["stocks"]]
    index = keep_last_good(incoming["index"], (previous or {}).get("index"))
    fresh_count = sum(bool(item.get("is_available")) for item in incoming["stocks"])
    fresh_count += int(bool(incoming["index"].get("is_available")))
    available_count = sum(bool(item.get("is_available")) for item in stocks) + int(bool(index.get("is_available")))
    expected_count = len(stocks) + 1

    if fresh_count == expected_count:
        status = "delayed"
        source = "Yahoo Finance · BEI tertunda sekitar 10 menit"
    elif fresh_count:
        status = "partial"
        source = "Yahoo Finance · kutipan yang gagal memakai data terakhir yang tersimpan"
    elif previous and available_count:
        status = "stale"
        source = "Yahoo Finance tidak dapat dijangkau · menampilkan kutipan valid terakhir"
    else:
        status = "unavailable"
        source = "Yahoo Finance · kutipan belum tersedia"

    updated = {
        **incoming,
        "index": index,
        "stocks": stocks,
        "status": status,
        "source": source,
        "available_count": available_count,
        "fresh_count": fresh_count,
        "is_available": available_count > 0,
    }
    comparable = deepcopy(updated)
    old_comparable = deepcopy(previous)
    if previous:
        comparable.pop("updated_at", None)
        old_comparable.pop("updated_at", None)
    if previous and stable_json(comparable) == stable_json(old_comparable):
        print("The published market snapshot has not changed.")
        return

    if not fresh_count and not available_count:
        print("No usable market data yet; no snapshot written.")
        return

    updated["updated_at"] = (previous or {}).get("updated_at") if not fresh_count else datetime.now(timezone.utc).isoformat()
    SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
    SNAPSHOT.write_text(json.dumps(updated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Saved market snapshot: {fresh_count}/{expected_count} fresh; {available_count}/{expected_count} available.")


if __name__ == "__main__":
    main()
