from src.db import get_client

c = get_client()
channels = c.table("channels").select("id, name, channel_id").execute()
total = 0
for ch in channels.data:
    count = c.table("videos").select("id", count="exact").eq("channel_id", ch["id"]).execute()
    n = count.count
    total += n
    name = ch["name"].encode("ascii", "replace").decode()
    print(f"  {name}: {n} videos")

print(f"\nTotal videos in database: {total}")
