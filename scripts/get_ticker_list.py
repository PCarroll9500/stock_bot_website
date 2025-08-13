"""
Fetch US-listed tickers and save to ../docs/data/all_stock_tickers.txt
- Newline-delimited with a header line "Symbol"
- Stdlib only, works on Windows/Linux/VS Code
"""

import time
from typing import List
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

NASDAQ_URL = "https://www.nasdaqtrader.com/dynamic/symdir/nasdaqlisted.txt"
OTHER_URL  = "https://www.nasdaqtrader.com/dynamic/symdir/otherlisted.txt"

def http_get(url: str, timeout: int = 15, retries: int = 3, backoff: float = 2.0) -> str:
    last_err = None
    for i in range(retries):
        try:
            req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf-8", errors="ignore")
        except (URLError, HTTPError) as e:
            last_err = e
            sleep_s = backoff ** i
            print(f"[warn] GET {url} failed ({e}). Retry in {sleep_s:.1f}s ({i+1}/{retries})...")
            time.sleep(sleep_s)
    raise last_err

def parse_symbols(text: str, symbol_fields: List[str]) -> List[str]:
    lines = [ln for ln in text.strip().splitlines() if ln.strip()]
    if not lines:
        return []
    header = [h.strip() for h in lines[0].split("|")]
    rows = (ln.split("|") for ln in lines[1:])

    symbols = []
    for row in rows:
        if row and row[0].startswith("File Creation Time"):
            break  # footer
        rec = {header[i]: (row[i].strip() if i < len(header) and i < len(row) else "")
               for i in range(len(header))}
        sym = next((rec[f] for f in symbol_fields if rec.get(f)), None)
        if not sym:
            continue
        if rec.get("Test Issue", "").upper() == "Y":
            continue
        symbols.append(sym.upper())
    return symbols

def main():
    # ../docs/data relative to this file (scripts/ -> docs/data/)
    base_dir = Path(__file__).resolve().parent.parent
    data_dir = base_dir / "docs" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    out_txt = data_dir / "all_stock_tickers.txt"

    print(f"[info] Repo root: {base_dir}")
    print(f"[info] Output dir: {data_dir}")
    print(f"[info] Writing: {out_txt}")

    print("[info] Downloading NASDAQ list...")
    nasdaq_txt = http_get(NASDAQ_URL)
    nasdaq_syms = parse_symbols(nasdaq_txt, ["Symbol"])

    print("[info] Downloading OTHER list...")
    other_txt = http_get(OTHER_URL)
    other_syms = parse_symbols(other_txt, ["ACT Symbol", "CQS Symbol"])

    all_syms = sorted(set(nasdaq_syms + other_syms))
    print(f"[info] Total symbols: {len(all_syms)}")

    # Write newline-delimited text with a header
    with out_txt.open("w", encoding="utf-8", newline="\n") as f:
        f.write("Symbol\n")
        for s in all_syms:
            f.write(f"{s}\n")

    print(f"[ok] Saved {len(all_syms)} tickers to {out_txt}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[error] {e.__class__.__name__}: {e}")
        raise
