"""Process videos: fetch transcript, extract recommendations, save to DB."""

from datetime import datetime, timezone
from src import db
from src.transcriber import get_transcript
from src.extractor import extract_recommendations
from src.figi import lookup_ticker


BENCHMARK_MAP = {
    "USA": "^GSPC",
    "Europe": "^STOXX",
    "Germany": "^STOXX",
    "Italy": "FTSEMIB.MI",
    "UK": "^STOXX",
}


def _resolve_ticker(reco: dict, market_default: str) -> dict:
    """Try to validate/resolve the ticker via OpenFIGI."""
    ticker = reco.get("ticker", "").strip()
    if not ticker:
        return {"validated": False, "ticker": None, "isin": None}

    result = lookup_ticker(ticker, market_default)
    if result:
        return {"validated": True, "ticker": result["ticker"], "isin": None}

    return {"validated": False, "ticker": ticker, "isin": None}


def process_video(video: dict, channel: dict) -> dict:
    """Process a single video: transcript -> extraction -> save.

    Returns a summary dict with counts.
    """
    video_id_yt = video["video_id"]
    language = channel.get("language", "EN")
    market = channel.get("market_default", "USA")
    client = db.get_client()

    safe_title = video["title"].encode("ascii", "replace").decode()
    print(f"  Processing: {safe_title}")

    # 1. Fetch transcript
    result = get_transcript(video_id_yt, language)
    transcript_text = result["text"]
    transcript_source = result["source"]

    client.table("videos").update({
        "transcript_source": transcript_source,
        "status": "transcribed" if transcript_text else "error",
    }).eq("id", video["id"]).execute()

    if not transcript_text:
        print(f"    No transcript available")
        return {"transcribed": False, "recommendations": 0, "quarantined": 0}

    print(f"    Transcript: {len(transcript_text)} chars ({transcript_source})")

    # 2. Extract recommendations
    pub_date = video.get("published_at", "")[:10]
    recos = extract_recommendations(
        title=video["title"],
        transcript=transcript_text,
        language=language,
        date=pub_date,
    )

    if not recos:
        client.table("videos").update({
            "status": "extracted",
            "processed_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", video["id"]).execute()
        print(f"    No recommendations found")
        return {"transcribed": True, "recommendations": 0, "quarantined": 0}

    print(f"    Found {len(recos)} recommendation(s)")

    # 3. Validate tickers and save
    saved = 0
    quarantined = 0
    benchmark = BENCHMARK_MAP.get(market, "^GSPC")

    for reco in recos:
        resolved = _resolve_ticker(reco, market)
        is_low_conf = reco.get("low_confidence", False)

        if is_low_conf and not resolved["validated"]:
            client.table("quarantine").insert({
                "video_id": video["id"],
                "raw_extraction_json": reco,
                "reason": f"Low confidence asset name, ticker not validated: {reco.get('asset_name', '?')}",
            }).execute()
            quarantined += 1
            print(f"    [QUARANTINE] {reco.get('asset_name', '?')}")
            continue

        ticker_to_save = resolved["ticker"] or reco.get("ticker", "")

        rec_record = {
            "video_id": video["id"],
            "asset_name": reco["asset_name"],
            "ticker": ticker_to_save if ticker_to_save else None,
            "isin": resolved.get("isin"),
            "asset_type": reco["asset_type"],
            "action": reco["action"],
            "target_price": reco.get("target_price"),
            "horizon_text": reco.get("horizon_text"),
            "rationale": reco.get("rationale", ""),
            "quote": reco.get("quote", ""),
            "video_timestamp": reco.get("video_timestamp"),
            "reco_date": pub_date or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "benchmark_ticker": benchmark,
            "conditional": reco.get("conditional", False),
            "status": "open",
        }

        try:
            client.table("recommendations").insert(rec_record).execute()
            saved += 1
            action = reco["action"].upper()
            print(f"    [SAVED] {action} {reco['asset_name']} ({ticker_to_save})")
        except Exception as e:
            client.table("quarantine").insert({
                "video_id": video["id"],
                "raw_extraction_json": reco,
                "reason": f"DB insert failed: {type(e).__name__}",
            }).execute()
            quarantined += 1

    status = "extracted" if saved > 0 else "error"
    client.table("videos").update({
        "status": status,
        "processed_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", video["id"]).execute()

    return {"transcribed": True, "recommendations": saved, "quarantined": quarantined}


def process_pending_videos(limit: int = 5) -> dict:
    """Process videos that haven't been extracted yet.

    Returns summary of processing.
    """
    client = db.get_client()

    videos_result = (
        client.table("videos")
        .select("*, channels!inner(language, market_default, name)")
        .in_("status", ["new", "transcribed"])
        .order("published_at", desc=True)
        .limit(limit)
        .execute()
    )

    videos = videos_result.data
    if not videos:
        print("No pending videos to process.")
        return {"processed": 0, "recommendations": 0, "quarantined": 0}

    print(f"Processing {len(videos)} video(s)...\n")

    total = {"processed": 0, "recommendations": 0, "quarantined": 0}

    for video in videos:
        channel_info = video.get("channels", {})
        channel = {
            "language": channel_info.get("language", "EN"),
            "market_default": channel_info.get("market_default", "USA"),
            "name": channel_info.get("name", "Unknown"),
        }

        result = process_video(video, channel)
        total["processed"] += 1
        total["recommendations"] += result["recommendations"]
        total["quarantined"] += result["quarantined"]
        print()

    return total
