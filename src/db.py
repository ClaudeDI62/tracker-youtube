from supabase import create_client, Client
from src.config import SUPABASE_URL, SUPABASE_KEY

_client: Client | None = None


def get_client() -> Client:
    global _client
    if _client is None:
        _client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _client


def init_channels(channels: list[dict]) -> None:
    """Insert pilot channels if they don't already exist."""
    client = get_client()
    for ch in channels:
        existing = (
            client.table("channels")
            .select("id")
            .eq("channel_id", ch["channel_id"])
            .execute()
        )
        if not existing.data:
            client.table("channels").insert(
                {
                    "name": ch["name"],
                    "url": ch["url"],
                    "channel_id": ch["channel_id"],
                    "language": ch["language"],
                    "market_default": ch["market_default"],
                    "active": True,
                }
            ).execute()


def get_active_channels() -> list[dict]:
    """Return all active channels from the database."""
    client = get_client()
    result = client.table("channels").select("*").eq("active", True).execute()
    return result.data


def video_exists(video_id: str) -> bool:
    """Check if a video is already in the database."""
    client = get_client()
    result = (
        client.table("videos")
        .select("id")
        .eq("video_id", video_id)
        .execute()
    )
    return len(result.data) > 0


def insert_video(video: dict) -> dict:
    """Insert a new video record and return it."""
    client = get_client()
    result = client.table("videos").insert(video).execute()
    return result.data[0]


def log_job_run(status: str, notes: str = "") -> None:
    """Log a job execution."""
    client = get_client()
    from datetime import datetime, timezone

    client.table("job_runs").insert(
        {
            "started_at": datetime.now(timezone.utc).isoformat(),
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "status": status,
            "notes": notes,
        }
    ).execute()
