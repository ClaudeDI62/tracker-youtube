"""Process all pending videos and evaluate all recommendations."""

from src.pipeline import process_pending_videos
from src.prices import fill_price_at_reco
from src.evaluator import evaluate_all_open
from src.ratings import update_ratings
from src.db import get_client

print("=" * 60)
print("BACKFILL: Process all videos + evaluate + rate")
print("=" * 60)

# Step 1: Process all pending videos (transcribe + extract)
print("\n--- Step 1: Processing all pending videos ---\n")
result = process_pending_videos(limit=50)
print(f"\nProcessing done: {result}")

# Step 2: Fill missing prices
print("\n--- Step 2: Fetching prices for all recommendations ---")
client = get_client()
recos = client.table("recommendations").select("*").is_("price_at_reco", "null").execute()
print(f"Recommendations missing price: {len(recos.data)}")
for r in recos.data:
    price = fill_price_at_reco(r)
    name = r["asset_name"].encode("ascii", "replace").decode()
    ticker = r["ticker"] or "?"
    if price:
        print(f"  {name} ({ticker}): ${price:.2f}")
    else:
        print(f"  {name} ({ticker}): NO PRICE")

# Step 3: Evaluate
print("\n--- Step 3: Evaluating at 7/30/90 days ---")
eval_result = evaluate_all_open()
print(f"\nEvaluation: {eval_result}")

# Step 4: Ratings
print("\n--- Step 4: Channel ratings ---")
rating_result = update_ratings()
print(f"\nRatings: {rating_result}")

# Summary
print("\n--- FINAL SUMMARY ---")
all_recos = client.table("recommendations").select("id", count="exact").execute()
all_evals = client.table("evaluations").select("id", count="exact").execute()
all_ratings = client.table("ratings").select("*").execute()
quarantine = client.table("quarantine").select("id", count="exact").execute()

print(f"  Total recommendations: {all_recos.count}")
print(f"  Total evaluations: {all_evals.count}")
print(f"  Quarantined: {quarantine.count}")
print(f"  Ratings entries: {len(all_ratings.data)}")
print("=" * 60)
