"""Calculate channel ratings using Wilson lower bound."""

import math
from src.db import get_client

Z = 1.96  # 95% confidence


def wilson_lower_bound(hits: int, total: int) -> float:
    """Wilson score interval lower bound at 95% confidence."""
    if total == 0:
        return 0.0
    p = hits / total
    denominator = 1 + Z * Z / total
    centre = p + Z * Z / (2 * total)
    spread = Z * math.sqrt((p * (1 - p) + Z * Z / (4 * total)) / total)
    return (centre - spread) / denominator


def update_ratings() -> dict:
    """Recalculate ratings for all channels at all horizons.

    Returns summary.
    """
    client = get_client()
    channels = client.table("channels").select("id, name").eq("active", True).execute()
    horizons = [7, 30, 90]
    updated = 0

    for channel in channels.data:
        ch_id = channel["id"]

        recos = (
            client.table("recommendations")
            .select("id, action, video_id, videos!inner(channel_id)")
            .eq("videos.channel_id", ch_id)
            .in_("action", ["buy", "sell"])
            .execute()
        )

        reco_ids = [r["id"] for r in recos.data]
        if not reco_ids:
            continue

        for horizon in horizons:
            evals = (
                client.table("evaluations")
                .select("hit, excess_return_pct")
                .in_("recommendation_id", reco_ids)
                .eq("horizon_days", horizon)
                .not_.is_("hit", "null")
                .execute()
            )

            if not evals.data:
                continue

            n = len(evals.data)
            hits = sum(1 for e in evals.data if e["hit"])
            hit_rate = hits / n if n > 0 else 0
            wlb = wilson_lower_bound(hits, n)
            avg_excess = sum(float(e["excess_return_pct"]) for e in evals.data) / n

            score = wlb

            rating_record = {
                "channel_id": ch_id,
                "horizon_days": horizon,
                "n_recos": n,
                "hit_rate": round(hit_rate, 4),
                "wilson_lb": round(wlb, 4),
                "avg_excess_return": round(avg_excess, 2),
                "score": round(score, 4),
            }

            client.table("ratings").upsert(rating_record).execute()
            updated += 1

            name = channel["name"].encode("ascii", "replace").decode()
            print(f"  {name} {horizon}d: {hits}/{n} hits ({hit_rate:.0%}) "
                  f"Wilson={wlb:.3f} excess={avg_excess:+.1f}%")

    return {"updated": updated}
