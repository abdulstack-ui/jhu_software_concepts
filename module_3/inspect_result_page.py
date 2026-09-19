from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import WebDriverException

OUTPUT = Path("result_page_sample.html")
KEYWORDS = (
    "gpa",
    "gre",
    "international",
    "american",
    "fall",
    "spring",
    "summer",
    "semester",
    "term",
    "masters",
    "master",
    "phd",
    "degree",
)


def main() -> None:
    options = webdriver.ChromeOptions()
    options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    driver = webdriver.Chrome(options=options)

    matches: list[tuple[str, str]] = []
    original = driver.current_window_handle

    for handle in driver.window_handles:
        try:
            driver.switch_to.window(handle)
            parsed = urlparse(driver.current_url)
            if "thegradcafe.com" in parsed.netloc.lower() and parsed.path.startswith("/result/"):
                matches.append((handle, driver.current_url))
        except WebDriverException:
            continue

    if not matches:
        raise RuntimeError(
            "No GradCafe /result/... tab is open in the debug Chrome session. "
            "Open one real result URL from applicant_data.json, complete any normal verification manually, "
            "leave that tab open, and rerun this script."
        )
    if len(matches) > 1:
        urls = "\n".join(f"  - {url}" for _, url in matches)
        raise RuntimeError(f"More than one GradCafe result tab is open. Close all but one:\n{urls}")

    driver.switch_to.window(matches[0][0])
    html = driver.page_source
    OUTPUT.write_text(html, encoding="utf-8")

    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text("\n", strip=True)
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    print(f"Captured: {driver.current_url}")
    print(f"Saved HTML: {OUTPUT.resolve()}")
    print("\nKeyword-bearing text from the rendered result page:\n")

    seen = set()
    found = 0
    for i, line in enumerate(lines):
        low = line.lower()
        if any(keyword in low for keyword in KEYWORDS):
            start = max(0, i - 1)
            end = min(len(lines), i + 2)
            block = " | ".join(lines[start:end])
            if block not in seen:
                print(block)
                seen.add(block)
                found += 1

    if found == 0:
        print("No obvious GPA/GRE/nationality/term/degree keywords were found in the rendered page text.")

    try:
        driver.switch_to.window(original)
    except WebDriverException:
        pass


if __name__ == "__main__":
    main()
