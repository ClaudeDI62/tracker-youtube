"""Fetch YouTube video transcripts."""

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
    CouldNotRetrieveTranscript,
)


def get_transcript(video_id: str, language: str = "EN") -> dict:
    """Fetch transcript for a video. Returns dict with 'text' and 'source'."""
    lang_codes = {
        "EN": ["en", "en-US", "en-GB"],
        "DE": ["de", "de-DE", "de-AT"],
    }
    preferred = lang_codes.get(language, ["en"])

    try:
        ytt_api = YouTubeTranscriptApi()
        transcript_list = ytt_api.list(video_id)

        # Try manual (human) subtitles first in preferred language
        for t in transcript_list:
            if not t.is_generated and t.language_code in preferred:
                fetched = t.fetch()
                text = " ".join(snippet.text for snippet in fetched)
                return {"text": text, "source": "subs"}

        # Try auto-generated in preferred language
        for t in transcript_list:
            if t.is_generated and t.language_code in preferred:
                fetched = t.fetch()
                text = " ".join(snippet.text for snippet in fetched)
                return {"text": text, "source": "subs"}

        # Try any available transcript
        for t in transcript_list:
            if t.language_code in preferred:
                fetched = t.fetch()
                text = " ".join(snippet.text for snippet in fetched)
                return {"text": text, "source": "subs"}

        # Last resort: first available
        first = next(iter(transcript_list))
        fetched = first.fetch()
        text = " ".join(snippet.text for snippet in fetched)
        return {"text": text, "source": "subs"}

    except (TranscriptsDisabled, NoTranscriptFound, CouldNotRetrieveTranscript):
        return {"text": None, "source": "none"}
    except Exception as e:
        print(f"  [WARN] Transcript error for {video_id}: {type(e).__name__}")
        return {"text": None, "source": "none"}
