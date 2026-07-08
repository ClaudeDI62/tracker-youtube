"""Check recommendations saved in database."""
from src.db import get_client

c = get_client()

# Count recommendations
recos = c.table("recommendations").select("*").execute()
print(f"Total recommendations: {len(recos.data)}\n")

for r in recos.data:
    name = r["asset_name"].encode("ascii", "replace").decode()
    print(f"  {r['action'].upper():5s} | {name:30s} | {r['ticker'] or '?':8s} | {r['reco_date']} | cond={r['conditional']}")

# Check quarantine
q = c.table("quarantine").select("*").execute()
print(f"\nQuarantined items: {len(q.data)}")

# Check video statuses
videos = c.table("videos").select("status", count="exact").execute()
status_counts = {}
for v in videos.data:
    s = v["status"]
    status_counts[s] = status_counts.get(s, 0) + 1
print(f"\nVideo statuses: {status_counts}")
