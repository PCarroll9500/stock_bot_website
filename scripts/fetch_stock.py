# scripts/fetch_stock.py
import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo  # Python 3.9+

# Optional CLI: python scripts/fetch_stock.py MSFT
TICKER = sys.argv[1].upper() if len(sys.argv) > 1 else "AAPL"

DATA_DIR = Path("docs/data")
JSON_PATH = DATA_DIR / "stockinfo.json"
DATA_DIR.mkdir(parents=True, exist_ok=True)

NY = ZoneInfo("America/New_York")

def now_est_iso():
    return datetime.now(NY).isoformat()

def today_est_str():
    return datetime.now(NY).strftime("%Y-%m-%d")

def load_json(path: Path):
    if path.exists():
        try:
            with open(path, "r") as f:
                return json.load(f)
        except Exception:
            pass
    # Fresh file skeleton (positions: only static fields; JS will compute live values)
    return {
        "updated_at": None,
        "title": "Inf Money Stock Bot",
        "invested_cost_basis": 10000.00,
        "equity_series": [],
        "positions": [
            {
                "ticker": TICKER,
                "qty": 10.0,
                "avg_price": 100.0
            }
        ]
    }

def save_json(path: Path, obj):
    with open(path, "w") as f:
        json.dump(obj, f, indent=2)

def main():
    data = load_json(JSON_PATH)

    # --- equity_series: append once per market day (EST) ---
    today = today_est_str()
    has_today = any(x.get("date") == today for x in data.get("equity_series", []))

    if not has_today:
        # Carry forward last known equity (morning snapshot before the market moves).
        last_equity = None
        if data.get("equity_series"):
            last_equity = data["equity_series"][-1].get("equity")
        if last_equity is None:
            # Fallback: use invested_cost_basis on first run
            last_equity = float(data.get("invested_cost_basis", 0.0))

        data.setdefault("equity_series", []).append({
            "date": today,
            "equity": float(last_equity)
        })

    # Keep positions trimmed to ONLY the testing fields (ticker, qty, avg_price)
    # If existing file has more fields, strip them.
    clean_positions = []
    for p in data.get("positions", []):
        clean_positions.append({
            "ticker": p.get("ticker", TICKER),
            "qty": float(p.get("qty", 0.0)),
            "avg_price": float(p.get("avg_price", 0.0)),
        })
    data["positions"] = clean_positions

    # Final touchups
    data["equity_series"] = sorted(data["equity_series"], key=lambda x: x["date"])
    data["updated_at"] = now_est_iso()
    data["title"] = "Inf Money Stock Bot"

    save_json(JSON_PATH, data)
    print(f"Wrote {JSON_PATH}")

if __name__ == "__main__":
    main()
