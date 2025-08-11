# scripts/fetch_stock.py
import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo  # Python 3.9+

# --- integrate stock picker ---
try:
    # stock_picker.py should be importable (same project / PYTHONPATH)
    from stock_picker import get_stocks
except Exception as e:
    get_stocks = None
    _IMPORT_ERR = e

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
    # Fresh file skeleton; JS will compute live values
    return {
        "updated_at": None,
        "title": "Inf Money Stock Bot",
        "invested_cost_basis": 10000.00,
        "equity_series": [],
        "picks": [],
        "positions": []
    }

def save_json(path: Path, obj):
    with open(path, "w") as f:
        json.dump(obj, f, indent=2)

def _build_positions_from_picks(picks, default_qty=10.0, default_avg=100.0):
    # Keep only simple fields; your JS computes market stuff
    positions = []
    seen = set()
    for p in picks:
        t = (p.get("ticker") or "").upper()
        if not t or t in seen:
            continue
        positions.append({
            "ticker": t,
            "qty": float(default_qty),
            "avg_price": float(default_avg),
        })
        seen.add(t)
    return positions

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

    # --- get 10 stocks from the picker ---
    picks = []
    if get_stocks is None:
        # Picker not importable; preserve any existing data
        # You can print the error for CI logs if desired
        print(f"Warning: could not import stock_picker: {_IMPORT_ERR}")
        picks = data.get("picks", [])
    else:
        try:
            picks = get_stocks(10) or []
        except Exception as e:
            print(f"Warning: stock_picker.get_stocks failed: {e}")
            picks = data.get("picks", [])

    # Normalize picks: [{"ticker": "AAPL", "reason": "..."}, ...]
    norm_picks = []
    seen = set()
    for p in picks:
        t = (p.get("ticker") or "").upper()
        r = p.get("reason") or ""
        if not t or t in seen:
            continue
        norm_picks.append({"ticker": t, "reason": r})
        seen.add(t)

    # If picker returned nothing, keep previous positions/picks (don’t blow away the file)
    if norm_picks:
        data["picks"] = norm_picks
        data["positions"] = _build_positions_from_picks(norm_picks, default_qty=10.0, default_avg=100.0)
    else:
        # Ensure positions (if present) are trimmed to required fields
        clean_positions = []
        for p in data.get("positions", []):
            clean_positions.append({
                "ticker": (p.get("ticker") or "").upper(),
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
