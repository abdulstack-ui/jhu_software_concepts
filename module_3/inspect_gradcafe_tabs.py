from __future__ import annotations

import base64
import json
from urllib.parse import parse_qs, urlparse

from selenium import webdriver


def decode_cursor(url: str) -> str:
    cursor = parse_qs(urlparse(url).query).get("cursor", [None])[0]
    if not cursor:
        return "(no cursor)"
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        payload = base64.urlsafe_b64decode(padded.encode()).decode("utf-8")
        obj = json.loads(payload)
        return json.dumps(obj, ensure_ascii=False)
    except Exception:
        return "(cursor present; could not decode)"


options = webdriver.ChromeOptions()
options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
driver = webdriver.Chrome(options=options)

rows = []
original = driver.current_window_handle
for i, handle in enumerate(driver.window_handles, start=1):
    driver.switch_to.window(handle)
    rows.append((i, driver.title, driver.current_url, decode_cursor(driver.current_url)))

try:
    driver.switch_to.window(original)
except Exception:
    pass

print(f"Open Chrome tabs: {len(rows)}")
for i, title, url, cursor in rows:
    print(f"\n[{i}] {title}\nURL: {url}\nCursor: {cursor}")
