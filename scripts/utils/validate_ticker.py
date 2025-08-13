import sys
from pathlib import Path
from typing import Set

CANDIDATE_PATHS = [
    ("docs", "data", "all_stock_tickers.txt")
]

def _repo_root() -> Path:
    """
    Try to detect the repo root by walking up from this file until we find
    a folder that contains 'data' or 'docs/data'. Fall back to three levels up.
    """
    here = Path(__file__).resolve()
    for p in here.parents:
        if (p / "docs" / "data").exists() or (p / "data").exists():
            return p
    # Fallback: assume three levels up from scripts/utils/<file>.py → repo/
    # (parents[0]=utils, [1]=scripts, [2]=repo)
    return here.parents[2] if len(here.parents) >= 3 else here.parents[-1]

def _find_symbols_file(repo_root: Path) -> Path | None:
    for parts in CANDIDATE_PATHS:
        path = repo_root.joinpath(*parts)
        if path.exists():
            return path
    return None

def _load_symbols(path: Path) -> Set[str]:
    """
    Accepts newline-delimited with optional "Symbol" header (case-insensitive).
    Also tolerates commas on a line (will split). Empty tokens are ignored.
    """
    lines: list[str] = []
    with path.open("r", encoding="utf-8") as f:
        for ln in f:
            ln = ln.strip()
            if not ln:
                continue
            # split by comma if present, else keep the whole line
            tokens = [t.strip() for t in ln.split(",")] if "," in ln else [ln]
            for t in tokens:
                if t:
                    lines.append(t)

    # drop header if present
    if lines and lines[0].strip().upper() == "SYMBOL":
        lines = lines[1:]

    return {t.upper() for t in lines if t}

def normalize(t: str) -> str:
    return (t or "").strip().upper()

def is_valid_ticker(ticker: str, universe: Set[str]) -> bool:
    return normalize(ticker) in universe

def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("Usage: python scripts/utils/validate_ticker.py <TICKER> [<TICKER> ...]")
        return 2

    repo = _repo_root()
    symbols_path = _find_symbols_file(repo)
    if not symbols_path:
        print(
            "[error] Could not find a symbols file.\n"
            f"Looked under: {repo}\\docs\\data\\all_stock_tickers.txt, "
            "Generate one with your fetch script."
        )
        return 1

    try:
        symbols = _load_symbols(symbols_path)
    except Exception as e:
        print(f"[error] Failed to load symbols from {symbols_path}: {e.__class__.__name__}: {e}")
        return 1

    tickers = [normalize(a) for a in argv[1:] if a.strip()]
    all_ok = True
    for t in tickers:
        ok = t in symbols
        print(f"{t}: {'VALID' if ok else 'INVALID'}")
        if not ok:
            all_ok = False

    return 0 if all_ok else 1

if __name__ == "__main__":
    sys.exit(main(sys.argv))
