"""Extract financial recommendations from video transcripts using Claude API."""

import json
import anthropic
from src.config import ANTHROPIC_API_KEY

_client = None

EXTRACTION_TOOL = {
    "name": "save_recommendations",
    "description": "Save extracted financial recommendations from the video transcript.",
    "input_schema": {
        "type": "object",
        "properties": {
            "recommendations": {
                "type": "array",
                "description": "List of financial recommendations found in the transcript. Empty array if none found.",
                "items": {
                    "type": "object",
                    "properties": {
                        "asset_name": {
                            "type": "string",
                            "description": "Full name of the financial asset (e.g. 'Apple Inc.', 'SPDR S&P 500 ETF')",
                        },
                        "ticker": {
                            "type": "string",
                            "description": "Ticker symbol if mentioned or inferable (e.g. 'AAPL', 'SPY'). Empty string if unknown.",
                        },
                        "asset_type": {
                            "type": "string",
                            "enum": ["stock", "etf", "index", "commodity"],
                            "description": "Type of financial asset",
                        },
                        "action": {
                            "type": "string",
                            "enum": ["buy", "sell", "hold"],
                            "description": "The recommended action",
                        },
                        "target_price": {
                            "type": ["number", "null"],
                            "description": "Target price if mentioned, null otherwise. Normalize numbers by language.",
                        },
                        "horizon_text": {
                            "type": ["string", "null"],
                            "description": "Time horizon if mentioned (e.g. '6 months', 'end of year'). Null if not stated.",
                        },
                        "rationale": {
                            "type": "string",
                            "description": "Brief summary of why the author recommends this action (1-2 sentences).",
                        },
                        "quote": {
                            "type": "string",
                            "description": "Direct quote from the transcript (1-2 sentences max) supporting this recommendation.",
                        },
                        "video_timestamp": {
                            "type": ["string", "null"],
                            "description": "Approximate timestamp in the video (e.g. '5:30', '12:45'). Null if unclear.",
                        },
                        "conditional": {
                            "type": "boolean",
                            "description": "True if this is a conditional recommendation (e.g. 'if it breaks $200 then...').",
                        },
                        "low_confidence": {
                            "type": "boolean",
                            "description": "True if the asset name might be garbled by auto-transcription.",
                        },
                    },
                    "required": [
                        "asset_name", "ticker", "asset_type", "action",
                        "target_price", "horizon_text", "rationale", "quote",
                        "video_timestamp", "conditional", "low_confidence",
                    ],
                },
            },
        },
        "required": ["recommendations"],
    },
}


def _get_client():
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    return _client


def _build_prompt(title: str, transcript: str, language: str, date: str) -> str:
    number_note = ""
    if language in ("DE", "IT"):
        number_note = (
            "IMPORTANT: In German and Italian, decimal separator is comma and "
            "thousands separator is period. '6.500' means six thousand five hundred, "
            "'4,36' means four point thirty-six. Normalize all numbers to standard "
            "decimal notation (dot as decimal separator) in your output."
        )

    return f"""Analyze this YouTube video transcript and extract ALL financial recommendations.

VIDEO TITLE: {title}
VIDEO DATE: {date}
LANGUAGE: {language}

RULES:
1. Extract ONLY operative statements by the video author: buy, sell, hold, "I'm buying", "I would buy", "I'm avoiding", "my target is X".
2. Do NOT extract: news the author is merely reporting, recommendations from third parties the author is quoting, or general market commentary without a specific actionable call.
3. Distinguish buy/sell/hold recommendations from pure quantitative forecasts (price targets without a buy/sell/hold call). Only extract the former.
4. If the asset name seems garbled by automatic transcription (e.g. "RWE ACZEN" for "RWE Aktien"), propose the most plausible interpretation and set low_confidence to true.
5. Mark conditional recommendations (e.g. "if it breaks $200 then buy") with conditional: true.
6. Include a direct quote (1-2 sentences) and approximate video timestamp if discernible.
7. If no financial recommendations are found, return an empty array.
{number_note}

TRANSCRIPT:
{transcript}"""


def extract_recommendations(
    title: str,
    transcript: str,
    language: str = "EN",
    date: str = "",
) -> list[dict]:
    """Extract financial recommendations from a transcript using Claude Haiku.

    Returns a list of recommendation dicts, or empty list if none found.
    """
    if not transcript:
        return []

    max_chars = 100_000
    if len(transcript) > max_chars:
        transcript = transcript[:max_chars]

    prompt = _build_prompt(title, transcript, language, date)
    client = _get_client()

    try:
        response = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=4096,
            tools=[EXTRACTION_TOOL],
            tool_choice={"type": "tool", "name": "save_recommendations"},
            messages=[{"role": "user", "content": prompt}],
        )
    except anthropic.APIError as e:
        print(f"  [ERROR] Claude API error: {e}")
        return []

    for block in response.content:
        if block.type == "tool_use" and block.name == "save_recommendations":
            return block.input.get("recommendations", [])

    return []
