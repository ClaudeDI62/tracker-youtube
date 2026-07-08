"""Delete bad evaluations and re-run with fixed price cache."""

from src.db import get_client
from src.evaluator import evaluate_all_open
from src.ratings import update_ratings

client = get_client()

# Delete all evaluations to recalculate with fixed cache
print("Deleting all evaluations to recalculate...")
client.table("evaluations").delete().neq("id", 0).execute()
print("Done.\n")

# Reset recommendation statuses back to 'open'
client.table("recommendations").update(
    {"status": "open"}
).eq("status", "evaluated").execute()
print("Reset recommendation statuses.\n")

# Re-evaluate
print("--- Re-evaluating all recommendations ---")
eval_result = evaluate_all_open()
print(f"\nEvaluation: {eval_result}")

# Re-calculate ratings
print("\n--- Recalculating ratings ---")
rating_result = update_ratings()
print(f"\nRatings: {rating_result}")
