"""Daily job: ingest new videos, extract, evaluate, rate, email."""

import sys
from datetime import datetime, timezone

from src.db import get_client, init_channels, log_job_run
from src.config import PILOT_CHANNELS
from src.rss_watcher import check_all_channels
from src.pipeline import process_pending_videos
from src.prices import fill_price_at_reco
from src.evaluator import evaluate_all_open
from src.ratings import update_ratings
from src.emailer import send_daily_email


def main():
    start = datetime.now(timezone.utc)
    print(f"=== Daily Job started at {start.strftime('%Y-%m-%d %H:%M:%S UTC')} ===\n")
    errors = []

    # Step 1: Sync channels
    print("--- Step 1: Sync channels ---")
    try:
        init_channels(PILOT_CHANNELS)
        print("  Channels synced.\n")
    except Exception as e:
        errors.append(f"Channel sync: {e}")
        print(f"  [ERROR] {e}\n")

    # Step 2: Check RSS feeds
    print("--- Step 2: Check RSS feeds ---")
    try:
        rss_result = check_all_channels()
        print(f"  Checked {rss_result['checked']} channels, "
              f"{rss_result['new_videos']} new videos.\n")
        errors.extend(rss_result.get("errors", []))
    except Exception as e:
        errors.append(f"RSS: {e}")
        print(f"  [ERROR] {e}\n")

    # Step 3: Process videos (transcribe + extract)
    print("--- Step 3: Process pending videos ---")
    try:
        proc_result = process_pending_videos(limit=30)
        print(f"  Processed {proc_result['processed']} videos, "
              f"{proc_result['recommendations']} recommendations, "
              f"{proc_result['quarantined']} quarantined.\n")
    except Exception as e:
        errors.append(f"Processing: {e}")
        print(f"  [ERROR] {e}\n")

    # Step 4: Fill missing prices
    print("--- Step 4: Fill missing prices ---")
    try:
        client = get_client()
        recos = client.table("recommendations").select("*").is_("price_at_reco", "null").execute()
        filled = 0
        for r in recos.data:
            if fill_price_at_reco(r):
                filled += 1
        print(f"  Filled {filled}/{len(recos.data)} prices.\n")
    except Exception as e:
        errors.append(f"Prices: {e}")
        print(f"  [ERROR] {e}\n")

    # Step 5: Evaluate recommendations
    print("--- Step 5: Evaluate recommendations ---")
    try:
        eval_result = evaluate_all_open()
        print(f"  {eval_result['new_evals']} new evaluations.\n")
    except Exception as e:
        errors.append(f"Evaluation: {e}")
        print(f"  [ERROR] {e}\n")

    # Step 6: Update ratings
    print("--- Step 6: Update ratings ---")
    try:
        rating_result = update_ratings()
        print(f"  {rating_result['updated']} ratings updated.\n")
    except Exception as e:
        errors.append(f"Ratings: {e}")
        print(f"  [ERROR] {e}\n")

    # Step 7: Send email
    print("--- Step 7: Send email ---")
    try:
        send_daily_email()
    except Exception as e:
        errors.append(f"Email: {e}")
        print(f"  [ERROR] {e}\n")

    # Log job run
    status = "success" if not errors else "partial"
    notes = "; ".join(errors) if errors else ""
    try:
        log_job_run(status, notes)
    except Exception:
        pass

    end = datetime.now(timezone.utc)
    duration = (end - start).total_seconds()
    print(f"\n=== Daily Job finished in {duration:.0f}s — status: {status} ===")

    if errors:
        print(f"Errors: {errors}")
        sys.exit(1)


if __name__ == "__main__":
    main()
