"""Validate and resolve tickers/ISINs using OpenFIGI API."""

import httpx

FIGI_URL = "https://api.openfigi.com/v3/mapping"

MARKET_MIC = {
    "USA": "US",
    "Europe": None,
    "Germany": "DE",
    "Italy": "IT",
    "UK": "GB",
}

YAHOO_SUFFIX = {
    "XMIL": ".MI",
    "XFRA": ".DE",
    "XETR": ".DE",
    "XPAR": ".PA",
    "XAMS": ".AS",
    "XLON": ".L",
}


def lookup_ticker(ticker: str, market_default: str = "USA") -> dict | None:
    """Look up a ticker on OpenFIGI. Returns dict with name, ticker, isin, or None."""
    jobs = [{"idType": "TICKER", "idValue": ticker.upper()}]

    try:
        resp = httpx.post(FIGI_URL, json=jobs, timeout=10)
        resp.raise_for_status()
        results = resp.json()
    except Exception:
        return None

    if not results or "data" not in results[0]:
        return None

    entries = results[0]["data"]
    if not entries:
        return None

    best = entries[0]
    yahoo_ticker = ticker.upper()
    exchange = best.get("exchCode", "")
    if exchange in YAHOO_SUFFIX:
        yahoo_ticker = ticker.upper() + YAHOO_SUFFIX[exchange]

    return {
        "name": best.get("name", ""),
        "ticker": yahoo_ticker,
        "figi": best.get("figi", ""),
        "exchange": exchange,
    }


def lookup_by_name(name: str) -> dict | None:
    """Search OpenFIGI by company name. Returns first match or None."""
    jobs = [{"idType": "NAME", "idValue": name}]

    try:
        resp = httpx.post(FIGI_URL, json=jobs, timeout=10)
        resp.raise_for_status()
        results = resp.json()
    except Exception:
        return None

    if not results or "data" not in results[0]:
        return None

    entries = results[0]["data"]
    if not entries:
        return None

    best = entries[0]
    return {
        "name": best.get("name", ""),
        "ticker": best.get("ticker", ""),
        "figi": best.get("figi", ""),
        "exchange": best.get("exchCode", ""),
    }
