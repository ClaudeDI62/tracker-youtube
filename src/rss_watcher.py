"""Fetch YouTube RSS feeds and detect new videos."""

import feedparser
from datetime import datetime, timezone
from src.config import RSS_TEMPLATE
from src import db


def fetch_feed(channel_id: str) -> list[dict]:
    """Parse the RSS feed for a channel and return video entries."""
    url = RSS_TEMPLATE.format(channel_id=channel_id)
    feed = feedparser.parse(url)

    videos = []
    for entry in feed.entries:
        video_id = entry.yt_videoid
        published = datetime(
            *entry.published_parsed[:6], tzinfo=timezone.utc
        )
        videos.append(
            {
                "video_id": video_id,
                "title": entry.title,
                "url": entry.link,
                "published_at": published.isoformat(),
            }
        )
    return videos


def check_channel(channel: dict) -> list[dict]:
    """Check one channel for new videos. Returns list of newly inserted videos."""
    new_videos = []
    try:
        entries = fetch_feed(channel["channel_id"])
    except Exception as e:
        print(f"  [ERROR] RSS fetch failed for {channel['name']}: {e}")
        return new_videos

    for entry in entries:
        if db.video_exists(entry["video_id"]):
            continue

        video_record = {
            "channel_id": channel["id"],
            "video_id": entry["video_id"],
            "title": entry["title"],
            "url": entry["url"],
            "published_at": entry["published_at"],
            "transcript_source": "none",
            "status": "new",
        }
        try:
            saved = db.insert_video(video_record)
            new_videos.append(saved)
            safe_title = entry['title'].encode('ascii', 'replace').decode()
            print(f"  [NEW] {safe_title}")
        except Exception as e:
            print(f"  [ERROR] Failed to insert video {entry['video_id']}: {type(e).__name__}")

    return new_videos


def check_all_channels() -> dict:
    """Check all active channels. Returns summary."""
    channels = db.get_active_channels()
    summary = {"checked": 0, "new_videos": 0, "errors": []}

    for channel in channels:
        print(f"Checking: {channel['name']}...")
        try:
            new = check_channel(channel)
            summary["checked"] += 1
            summary["new_videos"] += len(new)
        except Exception as e:
            summary["errors"].append(f"{channel['name']}: {e}")
            print(f"  [ERROR] {e}")

    return summary
