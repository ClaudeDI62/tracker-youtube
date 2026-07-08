"""Evaluate recommendations at 7/30/90 day horizons against benchmarks."""

from datetime import date, timedelta
from src.db import get_client
from src.prices import get_close_price, fill_price_at_reco

HORIZONS = [7, 30, 90]
RELEVANCE_THRESHOLD = 1.0  # ±1% excess return to count as hit/miss


def evaluate_recommendation(reco: dict) -> list[dict]:
    """Evaluate one recommendation at all mature horizons.

    Returns list of evaluation dicts that were saved.
    """
    ticker = reco.get("ticker")
    if not ticker:
        return []

    reco_date_str = reco.get("reco_date")
    if not reco_date_str:
        return []
    reco_date = date.fromisoformat(reco_date_str) if isinstance(reco_date_str, str) else reco_date_str

    price_at_reco = reco.get("price_at_reco")
    if price_at_reco is None:
        price_at_reco = fill_price_at_reco(reco)
    if price_at_reco is None:
        return []
    price_at_reco = float(price_at_reco)

    benchmark_ticker = reco.get("benchmark_ticker", "^GSPC")
    benchmark_price_at_reco = get_close_price(benchmark_ticker, reco_date)
    if benchmark_price_at_reco is None:
        return []
    benchmark_price_at_reco = float(benchmark_price_at_reco)

    today = date.today()
    action = reco.get("action", "buy")
    client = get_client()
    evaluations = []

    for horizon in HORIZONS:
        target_date = reco_date + timedelta(days=horizon)
        if target_date > today:
            continue

        existing = (
            client.table("evaluations")
            .select("id")
            .eq("recommendation_id", reco["id"])
            .eq("horizon_days", horizon)
            .execute()
        )
        if existing.data:
            continue

        asset_price = get_close_price(ticker, target_date)
        if asset_price is None:
            continue
        asset_price = float(asset_price)

        bench_price = get_close_price(benchmark_ticker, target_date)
        if bench_price is None:
            continue
        bench_price = float(bench_price)

        asset_return = ((asset_price - price_at_reco) / price_at_reco) * 100
        bench_return = ((bench_price - benchmark_price_at_reco) / benchmark_price_at_reco) * 100
        excess = asset_return - bench_return

        if action == "hold":
            hit = None
        elif action == "buy":
            hit = excess > RELEVANCE_THRESHOLD
        else:  # sell
            hit = excess < -RELEVANCE_THRESHOLD

        eval_record = {
            "recommendation_id": reco["id"],
            "horizon_days": horizon,
            "asset_return_pct": round(asset_return, 2),
            "benchmark_return_pct": round(bench_return, 2),
            "excess_return_pct": round(excess, 2),
            "hit": hit,
        }

        try:
            client.table("evaluations").insert(eval_record).execute()
            evaluations.append(eval_record)
        except Exception as e:
            print(f"    [ERROR] Eval insert failed: {type(e).__name__}")

    if evaluations:
        client.table("recommendations").update(
            {"status": "evaluated"}
        ).eq("id", reco["id"]).execute()

    return evaluations


def evaluate_all_open() -> dict:
    """Evaluate all open recommendations that have mature horizons.

    Returns summary.
    """
    client = get_client()
    recos = (
        client.table("recommendations")
        .select("*")
        .in_("status", ["open", "evaluated"])
        .not_.is_("ticker", "null")
        .execute()
    )

    summary = {"evaluated": 0, "new_evals": 0, "errors": 0}

    for reco in recos.data:
        try:
            evals = evaluate_recommendation(reco)
            if evals:
                summary["evaluated"] += 1
                summary["new_evals"] += len(evals)
                name = reco["asset_name"].encode("ascii", "replace").decode()
                for ev in evals:
                    hit_str = "HIT" if ev["hit"] else ("MISS" if ev["hit"] is not None else "HOLD")
                    print(f"  {name} ({reco['ticker']}) {ev['horizon_days']}d: "
                          f"asset={ev['asset_return_pct']:+.1f}% bench={ev['benchmark_return_pct']:+.1f}% "
                          f"excess={ev['excess_return_pct']:+.1f}% -> {hit_str}")
        except Exception as e:
            summary["errors"] += 1
            print(f"  [ERROR] {reco.get('ticker')}: {type(e).__name__}")

    return summary
