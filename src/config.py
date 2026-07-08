import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

PILOT_CHANNELS = [
    {
        "name": "Joseph Carlson After Hours",
        "url": "https://www.youtube.com/@JosephCarlsonAfterHours",
        "channel_id": "UCfCT7SSFEWyG4th9ZmaGYqQ",
        "language": "EN",
        "market_default": "USA",
    },
    {
        "name": "Jerry Romine Stocks",
        "url": "https://www.youtube.com/@JerryRomineStocks",
        "channel_id": "UCMiJUXvEpHHW5JTnW-ez9EA",
        "language": "EN",
        "market_default": "USA",
    },
    {
        "name": "Finanzbär",
        "url": "https://www.youtube.com/@Finanzbaer",
        "channel_id": "UCFxPUPyzQQYaNfj0El4Ccqg",
        "language": "DE",
        "market_default": "Europe",
    },
    {
        "name": "Ticker Symbol: YOU",
        "url": "https://www.youtube.com/@TickerSymbolYOU",
        "channel_id": "UCORX3Cl7ByidjEgzSCgv9Yw",
        "language": "EN",
        "market_default": "USA",
    },
    {
        "name": "Millionaires Investment Secrets",
        "url": "https://www.youtube.com/channel/UCESh5daDcPqvG0QhbSdzIzw",
        "channel_id": "UCESh5daDcPqvG0QhbSdzIzw",
        "language": "EN",
        "market_default": "USA",
    },
    {
        "name": "Honeystocks Active Investing",
        "url": "https://www.youtube.com/channel/UCmNwLkHnslfzEtO2S16vmcQ",
        "channel_id": "UCmNwLkHnslfzEtO2S16vmcQ",
        "language": "EN",
        "market_default": "USA",
    },
    {
        "name": "Clive Thompson",
        "url": "https://www.youtube.com/@clivethompson-jc9my",
        "channel_id": "UCrlFUp4OtXJSiDfiPMFnk3A",
        "language": "EN",
        "market_default": "Globale",
    },
    {
        "name": "BWB - Business With Brian",
        "url": "https://www.youtube.com/@BusinessWithBrian",
        "channel_id": "UCyqlbzLoYtpqDXwRI9Yh5LA",
        "language": "EN",
        "market_default": "USA",
    },
]

RSS_TEMPLATE = "https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
