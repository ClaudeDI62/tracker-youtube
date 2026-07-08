"""Test Session 3: prices, evaluation, and ratings."""

from src.db import get_client
from src.prices import fill_price_at_reco
from src.evaluator import evaluate_all_open
from src.ratings import update_ratings

print("=" * 60)
print("SESSION 3 TEST: Prices, Evaluation, Ratings")
print("=" * 60)

# Step 1: Fill price_at_reco for all recommendations
print("\n--- Step 1: Fetching prices at recommendation date ---")
client = get_client()
recos = client.table("recommendations").select("*").is_("price_at_reco", "null").execute()
print(f"Recommendations missing price: {len(recos.data)}")

for r in recos.data:
    price = fill_price_at_reco(r)
    name = r["asset_name"].encode("ascii", "replace").decode()
    if price:
        print(f"  {name} ({r['ticker']}): ${price:.2f} on {r['reco_date']}")
    else:
        print(f"  {name} ({r['ticker']}): NO PRICE FOUND")

# Step 2: Evaluate recommendations
print("\n--- Step 2: Evaluating recommendations at 7/30/90 days ---")
eval_result = evaluate_all_open()
print(f"\nEvaluation summary: {eval_result}")

# Step 3: Update ratings
print("\n--- Step 3: Calculating channel ratings ---")
rating_result = update_ratings()
print(f"\nRating summary: {rating_result}")

# Step 4: Show final state
print("\n--- Final State ---")
all_recos = client.table("recommendations").select("*").execute()
all_evals = client.table("evaluations").select("*").execute()
all_ratings = client.table("ratings").select("*").execute()
prices_count = client.table("prices").select("ticker", count="exact").execute()

print(f"  Recommendations: {len(all_recos.data)}")
print(f"  Evaluations: {len(all_evals.data)}")
print(f"  Ratings: {len(all_ratings.data)}")
print(f"  Cached prices: {prices_count.count}")
print("=" * 60)
