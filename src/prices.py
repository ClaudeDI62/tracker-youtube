"""Fetch and cache daily close prices using yfinance."""

from datetime import date, timedelta
import yfinance as yf
from src.db import get_client


def get_close_price(ticker: str, target_date: date) -> float | None:
    """Get the closing price for a ticker on or before target_date.

    Checks the DB cache first, fetches from yfinance if missing.
    Returns None if no data available.
    """
    cached = _get_cached(ticker, target_date)
    if cached is not None:
        return cached

    price = _fetch_and_cache(ticker, target_date)
    return price


def _get_cached(ticker: str, target_date: date) -> float | None:
    """Look up price in the local cache (prices table).

    Only returns a price if it's within 5 calendar days of target_date
    (accounts for weekends and holidays).
    """
    min_date = target_date - timedelta(days=5)
    client = get_client()
    result = (
        client.table("prices")
        .select("close, date")
        .eq("ticker", ticker)
        .gte("date", min_date.isoformat())
        .lte("date", target_date.isoformat())
        .order("date", desc=True)
        .limit(1)
        .execute()
    )
    if result.data:
        return float(result.data[0]["close"])
    return None


def _fetch_and_cache(ticker: str, target_date: date) -> float | None:
    """Fetch price data from yfinance and store in cache."""
    start = target_date - timedelta(days=10)
    end = target_date + timedelta(days=1)

    try:
        tk = yf.Ticker(ticker)
        hist = tk.history(start=start.isoformat(), end=end.isoformat())
    except Exception:
        return None

    if hist.empty:
        return None

    rows_to_insert = []
    for idx, row in hist.iterrows():
        d = idx.date() if hasattr(idx, 'date') else idx
        rows_to_insert.append({
            "ticker": ticker,
            "date": d.isoformat() if hasattr(d, 'isoformat') else str(d),
            "close": round(float(row["Close"]), 4),
        })

    if rows_to_insert:
        client = get_client()
        client.table("prices").upsert(rows_to_insert).execute()

    valid = [r for r in rows_to_insert if r["date"] <= target_date.isoformat()]
    if valid:
        valid.sort(key=lambda r: r["date"], reverse=True)
        return valid[0]["close"]

    return None


def fetch_price_range(ticker: str, start_date: date, end_date: date) -> list[dict]:
    """Fetch and cache prices for a date range. Returns list of {date, close}."""
    start = start_date - timedelta(days=5)
    end = end_date + timedelta(days=1)

    try:
        tk = yf.Ticker(ticker)
        hist = tk.history(start=start.isoformat(), end=end.isoformat())
    except Exception:
        return []

    if hist.empty:
        return []

    rows = []
    for idx, row in hist.iterrows():
        d = idx.date() if hasattr(idx, 'date') else idx
        rows.append({
            "ticker": ticker,
            "date": d.isoformat() if hasattr(d, 'isoformat') else str(d),
            "close": round(float(row["Close"]), 4),
        })

    if rows:
        client = get_client()
        client.table("prices").upsert(rows).execute()

    return rows


def fill_price_at_reco(recommendation: dict) -> float | None:
    """Fill price_at_reco for a recommendation. Returns the price or None."""
    ticker = recommendation.get("ticker")
    if not ticker:
        return None

    reco_date = recommendation.get("reco_date")
    if not reco_date:
        return None

    if isinstance(reco_date, str):
        reco_date = date.fromisoformat(reco_date)

    price = get_close_price(ticker, reco_date)

    if price is not None:
        client = get_client()
        client.table("recommendations").update(
            {"price_at_reco": price}
        ).eq("id", recommendation["id"]).execute()

    return price
