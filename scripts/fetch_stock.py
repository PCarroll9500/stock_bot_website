# scripts/fetch_stock.py
import json, os
from datetime import datetime, timezone
import yfinance as yf
from pathlib import Path

# pick a ticker to start with
TICKER = os.getenv("TICKER", "AAPL")

p = Path("docs/data")
p.mkdir(parents=True, exist_ok=True)

# pull ~1 month of daily closes for a quick chart
hist = yf.Ticker(TICKER).history(period="1mo")[["Close"]]
series = [{"date": d.strftime("%Y-%m-%d"), "close": float(v)} for d, v in hist["Close"].items()]

payload = {
    "updated_at": datetime.now(timezone.utc).isoformat(),
    "ticker": TICKER,
    "series": series,          # easy to chart
}

with open(p / "stockinfo.json", "w") as f:
    json.dump(payload, f, indent=2)
print(f"Wrote {p / 'stockinfo.json'}")
