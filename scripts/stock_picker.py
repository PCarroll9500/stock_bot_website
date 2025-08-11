from concurrent.futures import ThreadPoolExecutor
from openai import OpenAI
from datetime import datetime
from utils.yahoo_finance_stock_info import is_valid_ticker, sanitize_ticker
import os
import re
import time

from dotenv import load_dotenv
load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def log(message):
    print(f"[{datetime.now().isoformat()}] {message}")

PROMPT_TEMPLATE = """
You are a highly aggressive day trader focused on short-term explosive stock moves.

Your job is to identify ONE stock that is likely to spike at least 10% TODAY based on a **very recent catalyst** something that happened in the last 24 hours, ideally within the last few hours possibly minutes.

You may justify your pick using:
- Politician trading disclosures (recent House/Senate buys)
- Breaking news, earnings, PRs, FDA decisions, or regulatory events
- Reddit, Twitter, Discord, or Stocktwits hype
- Unusual intraday volume or price action
- Sector momentum from global events (wars, hacks, disasters, sanctions, etc.)

✅ You may pick large-cap stocks **only if the catalyst is strong enough to realistically drive a 10%+ move today**  
🚫 Do NOT suggest “safe” or generic picks — only stocks with serious upside potential due to a current catalyst

🧠 Be bold. Be decisive. Pick the one stock with the highest probability of surging hard today.

🎯 Output format:
TICKER
One short sentence describing the catalyst behind your pick.

Nothing else. No disclaimers. No alternatives. Just the ticker and a one-liner reason.
"""

TICKER_LINE = re.compile(r"^([A-Z$.\-]{1,12})[:\-–\s]+(.+)$")

def _parse_pick(text: str):
    text = text.strip()
    m = TICKER_LINE.match(text)
    if m:
        raw = m.group(1).strip().upper()
        reason = m.group(2).strip()
        return raw, reason
    parts = text.split(None, 1)
    if parts:
        return parts[0].strip().upper(), (parts[1].strip() if len(parts) > 1 else "")
    return "UNKNOWN", text

def single_stock_picker(existing_tickers, max_retries=5, sleep_between=0.35):
    """
    Ask the model for a single pick, sanitize & validate with Yahoo util, retry on:
      - parse fails
      - invalid ticker
      - duplicate ticker
    """
    for attempt in range(1, max_retries + 1):
        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": PROMPT_TEMPLATE}],
                temperature=1.2,
            )
            content = (response.choices[0].message.content or "").strip()

            raw_ticker, reason = _parse_pick(content)
            ticker = sanitize_ticker(raw_ticker)

            if ticker == "" or ticker == "UNKNOWN":
                log(f"[Retry {attempt}] Could not parse ticker from: {content!r}")
            elif ticker in existing_tickers:
                log(f"[Retry {attempt}] Duplicate ticker: '{ticker}'")
            elif not is_valid_ticker(ticker):
                # Log the raw and sanitized to spot issues like '$NKLA' -> 'NKLA'
                log(f"[Retry {attempt}] Invalid ticker: '{raw_ticker}' -> '{ticker}'")
            else:
                return {"ticker": ticker, "reason": reason}

        except Exception as e:
            log(f"[Retry {attempt}] Error: {str(e)}")

        time.sleep(sleep_between)

    return {"ticker": "ERROR", "reason": "Exceeded retry limit or invalid/duplicate ticker"}

def run_multiple_agents(agent_count=10, seen_tickers=None):
    """
    Fire parallel agents to *attempt* unique, validated picks.
    Does not guarantee `agent_count` successes; use StockPicker.get_stocks for quotas.
    """
    results = []
    seen = set() if seen_tickers is None else set(seen_tickers)

    with ThreadPoolExecutor(max_workers=agent_count) as executor:
        futures = [executor.submit(single_stock_picker, seen.copy()) for _ in range(agent_count)]
        for future in futures:
            result = future.result()
            t = result["ticker"]
            if t != "ERROR" and t not in seen:
                seen.add(t)
                results.append(result)
            else:
                log(f"Duplicate or error: {t}")

    return results

class StockPicker:
    """
    Orchestrates repeated calls until we have the requested number of
    validated, non-duplicate tickers (or we hit a global attempt cap).
    """
    def __init__(self, per_call_retries: int = 5, global_attempt_cap: int = 50, batch_size: int = 6):
        self.per_call_retries = per_call_retries
        self.global_attempt_cap = global_attempt_cap
        self.batch_size = batch_size

    def get_stocks(self, num_stocks: int):
        picks = []
        seen = set()
        attempts = 0

        while len(picks) < num_stocks and attempts < self.global_attempt_cap:
            # Try a small parallel burst
            batch = run_multiple_agents(self.batch_size, seen_tickers=seen)
            attempts += 1

            added = 0
            for r in batch:
                t = r["ticker"]
                if t != "ERROR" and t not in seen:
                    seen.add(t)
                    picks.append(r)
                    added += 1
                    if len(picks) >= num_stocks:
                        break

            # If the burst didn't add anything, try a direct single call (with internal retries)
            if added == 0 and len(picks) < num_stocks:
                one = single_stock_picker(seen, max_retries=self.per_call_retries)
                attempts += 1
                if one["ticker"] != "ERROR" and one["ticker"] not in seen:
                    seen.add(one["ticker"])
                    picks.append(one)

        if len(picks) < num_stocks:
            log(f"Warning: requested {num_stocks}, but only obtained {len(picks)} validated picks after {attempts} attempts.")
        return picks

def get_stocks(num_stocks: int):
    return StockPicker().get_stocks(num_stocks)

# Local testing
if __name__ == "__main__":
    print("Running GPT agents...\n")
    picks = get_stocks(10)
    for i, pick in enumerate(picks, 1):
        print(f"Agent {i}:")
        print(f"  Ticker: {pick['ticker']}")
        print(f"  Reason: {pick['reason']}\n")
