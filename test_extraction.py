"""Test extraction pipeline on 5 videos."""

from src.pipeline import process_pending_videos

print("=" * 60)
print("TEST: Extraction pipeline (5 videos)")
print("=" * 60)
print()

result = process_pending_videos(limit=5)

print("=" * 60)
print(f"RESULTS:")
print(f"  Videos processed: {result['processed']}")
print(f"  Recommendations saved: {result['recommendations']}")
print(f"  Quarantined: {result['quarantined']}")
print("=" * 60)
