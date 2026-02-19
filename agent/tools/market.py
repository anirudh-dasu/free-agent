"""
Stock / market data via yfinance.
"""
from __future__ import annotations

import yfinance as yf


def get_stock_data(tickers: list[str]) -> dict:
    """
    Fetch basic OHLCV and summary stats for a list of tickers.
    Returns a dict keyed by ticker symbol.
    """
    results = {}

    for symbol in tickers:
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info

            # 30-day daily history
            hist = ticker.history(period="30d")

            if hist.empty:
                results[symbol] = {"error": "No data available"}
                continue

            latest = hist.iloc[-1]
            month_ago = hist.iloc[0]

            month_return = (
                (latest["Close"] - month_ago["Open"]) / month_ago["Open"] * 100
                if month_ago["Open"] > 0
                else None
            )

            results[symbol] = {
                "name": info.get("longName", symbol),
                "price": round(float(latest["Close"]), 2),
                "open": round(float(latest["Open"]), 2),
                "high": round(float(latest["High"]), 2),
                "low": round(float(latest["Low"]), 2),
                "volume": int(latest["Volume"]),
                "market_cap": info.get("marketCap"),
                "pe_ratio": info.get("trailingPE"),
                "52w_high": info.get("fiftyTwoWeekHigh"),
                "52w_low": info.get("fiftyTwoWeekLow"),
                "month_return_pct": round(month_return, 2) if month_return is not None else None,
                "currency": info.get("currency", "USD"),
                "sector": info.get("sector"),
                "industry": info.get("industry"),
            }
        except Exception as e:
            results[symbol] = {"error": str(e)}

    return results
