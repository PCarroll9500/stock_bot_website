import logging
from datetime import datetime
import yfinance as yf
import pandas as pd
import re

def sanitize_ticker(ticker: str) -> str:
    """
    Cleans up a ticker by removing leading/trailing spaces, dollar signs, and other unwanted chars.
    """
    return re.sub(r'[^A-Z0-9\.-]', '', ticker.upper())

class StockDataFetcher:
    def __init__(self, ticker):
        self.ticker = sanitize_ticker(ticker)
        self.data = {}

    def fetch(self):
        stock = yf.Ticker(self.ticker)
        info = stock.info

        # Historical data
        hist_month = stock.history(period="1mo")
        hist_week = stock.history(period="7d")

        # Performance
        month_perf = ((hist_month["Close"].iloc[-1] - hist_month["Close"].iloc[0]) / hist_month["Close"].iloc[0] * 100) if not hist_month.empty else None
        week_perf = ((hist_week["Close"].iloc[-1] - hist_week["Close"].iloc[0]) / hist_week["Close"].iloc[0] * 100) if not hist_week.empty else None

        # Recent news
        try:
            news = stock.news
            recent_news = [n['title'] for n in news[:5]]
        except Exception:
            recent_news = []

        # Moving averages
        ma7 = hist_month["Close"].rolling(window=7).mean().iloc[-1] if not hist_month.empty else None
        ma30 = hist_month["Close"].rolling(window=30).mean().iloc[-1] if not hist_month.empty else None

        # RSI
        def get_rsi(series, period=14):
            delta = series.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            return rsi.iloc[-1] if not rsi.empty else None
        rsi = get_rsi(hist_month["Close"]) if not hist_month.empty else None

        # Earnings
        def get_earnings_history(stock, limit=20):
            try:
                edf = stock.get_earnings_dates(limit=limit)
                if not edf.empty:
                    return edf.reset_index().to_dict(orient="records")
            except Exception:
                pass
            return None
        earnings_history = get_earnings_history(stock)

        self.data = {
            "Current date and time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "ticker": self.ticker,
            "currentPrice": info.get("currentPrice"),
            "exchange": info.get("exchange"),
            "beta": info.get("beta"),
            "debtToEquity": info.get("debtToEquity"),
            "marketCap": info.get("marketCap"),
            "trailingPE": info.get("trailingPE"),
            "sector": info.get("sector"),
            "longBusinessSummary": info.get("longBusinessSummary"),
            "monthPerformancePct": month_perf,
            "weekPerformancePct": week_perf,
            "averageVolume": info.get("averageVolume"),
            "currentVolume": info.get("volume"),
            "MA7": ma7,
            "MA30": ma30,
            "RSI": rsi,
            "fiftyTwoWeekHigh": info.get("fiftyTwoWeekHigh"),
            "fiftyTwoWeekLow": info.get("fiftyTwoWeekLow"),
            "recentNews": recent_news,
            "earningsHistory": earnings_history,
        }
        self.hist_month = hist_month

    def get_data(self):
        if not self.data:
            self.fetch()
        return self.data

    def get_daily_performance_table(self):
        if not hasattr(self, "hist_month"):
            self.fetch()
        hist = self.hist_month
        if hist is None or hist.empty:
            return "No historical data available."
        hist = hist.copy()
        hist["Pct Change"] = hist["Close"].pct_change() * 100
        hist = hist.dropna()
        volatility = hist["Pct Change"].std()
        table = "Date       | Close    | % Change\n"
        table += "-----------|----------|---------\n"
        for idx, row in hist.iterrows():
            table += f"{idx.date()} | {row['Close']:.2f} | {row['Pct Change']:+.2f}%\n"
        table += f"\nVolatility (std dev of daily % change): {volatility:.2f}%"
        return table

def is_valid_ticker(ticker):
    """
    Returns True if the ticker exists and has a current price.
    Accepts NASDAQ, NMS, NYSE, AMEX.
    """
    try:
        fetcher = StockDataFetcher(ticker)
        data = fetcher.get_data()
        exchange = str(data.get("exchange", "")).upper()
        return (
            data.get("currentPrice") is not None and
            exchange in ("NASDAQ", "NMS", "NYSE", "AMEX")
        )
    except Exception:
        return False

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    ticker = "AAPL"
    if not is_valid_ticker(ticker):
        logging.error(f"Invalid ticker symbol: {ticker}")
    else:
        fetcher = StockDataFetcher(ticker)
        print(fetcher.get_data())
        print(fetcher.get_daily_performance_table())
