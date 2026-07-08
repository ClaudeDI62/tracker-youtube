"""YouTube Tracker — main entry point."""

from src.config import PILOT_CHANNELS
from src import db
from src.rss_watcher import check_all_channels


def main():
    print("=== YouTube Recommendation Tracker ===\n")

    # Ensure pilot channels are in the database
    print("1. Syncing pilot channels...")
    db.init_channels(PILOT_CHANNELS)
    print("   Done.\n")

    # Check RSS feeds for new videos
    print("2. Checking RSS feeds for new videos...")
    summary = check_all_channels()
    print(f"\n   Channels checked: {summary['checked']}")
    print(f"   New videos found: {summary['new_videos']}")
    if summary["errors"]:
        print(f"   Errors: {len(summary['errors'])}")
        for err in summary["errors"]:
            print(f"     - {err}")

    # Log the run
    status = "success" if not summary["errors"] else "partial"
    db.log_job_run(status, f"New videos: {summary['new_videos']}")

    print("\nDone!")


if __name__ == "__main__":
    main()
