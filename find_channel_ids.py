import httpx
import re

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Cookie": "CONSENT=PENDING+987; SOCS=CAISNQgDEitib3FfaWRlbnRpdHlmcm9udGVuZHVpc2VydmVyXzIwMjMxMTE0LjA3X3AxGgJlbiADGgYIgJnpqwY",
}

handles = {
    "@JerryRomineStocks": "https://www.youtube.com/@JerryRomineStocks",
    "@Finanzbaer": "https://www.youtube.com/@Finanzbaer",
    "@JosephCarlsonAfterHours": "https://www.youtube.com/@JosephCarlsonAfterHours",
}

for name, url in handles.items():
    try:
        r = httpx.get(url, headers=headers, follow_redirects=True, timeout=15)
        patterns = [
            r'"externalId"\s*:\s*"(UC[^"]+)"',
            r'"channelId"\s*:\s*"(UC[^"]+)"',
            r'channel_id=(UC[^&"]+)',
            r'/channel/(UC[^"/?]+)',
        ]
        found = False
        for p in patterns:
            match = re.search(p, r.text)
            if match:
                print(f"{name}: {match.group(1)}")
                found = True
                break
        if not found:
            print(f"{name}: NOT FOUND (status={r.status_code}, len={len(r.text)})")
    except Exception as e:
        print(f"{name}: ERROR - {e}")
