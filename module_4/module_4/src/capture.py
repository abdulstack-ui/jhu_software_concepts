from __future__ import annotations

import argparse
import hashlib
import json
import random
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from scrape import build_url, deduplicate, load_data, parse_html, save_data

BLOCK_MARKERS = (
    "verify you are human",
    "just a moment",
    "attention required",
    "access denied",
    "too many requests",
    "rate limit",
)


def _blocked(html: str, title: str) -> bool:
    haystack = f"{title}\n{html[:10000]}".lower()
    return any(marker in haystack for marker in BLOCK_MARKERS)


def _survey_tabs(driver: webdriver.Chrome) -> list[tuple[str, str]]:
    """Return open GradCafe survey/result tabs without silently choosing a stale one."""
    tabs: list[tuple[str, str]] = []
    original = driver.current_window_handle
    for handle in driver.window_handles:
        try:
            driver.switch_to.window(handle)
            url = driver.current_url
            parsed = urlparse(url)
            if "thegradcafe.com" in parsed.netloc.lower() and parsed.path.startswith("/survey"):
                tabs.append((handle, url))
        except WebDriverException:
            continue
    try:
        driver.switch_to.window(original)
    except WebDriverException:
        pass
    return tabs


def _select_single_gradcafe_tab(driver: webdriver.Chrome) -> None:
    tabs = _survey_tabs(driver)
    if not tabs:
        raise RuntimeError(
            "No GradCafe /survey tab was found in the debug Chrome session. "
            "Open https://www.thegradcafe.com/survey in the Chrome window launched "
            "with --remote-debugging-port=9222, complete any verification manually, "
            "and leave that tab open."
        )
    if len(tabs) > 1:
        details = "\n".join(f"  {i + 1}. {url}" for i, (_, url) in enumerate(tabs))
        raise RuntimeError(
            "Multiple GradCafe survey tabs are open. This can make a restart attach to an old "
            "cursor and reread thousands of duplicate rows. Close all but the one you intend "
            f"to continue from, then rerun.\nOpen GradCafe tabs:\n{details}"
        )
    driver.switch_to.window(tabs[0][0])


def _is_root_survey_url(url: str) -> bool:
    parsed = urlparse(url)
    return (
        "thegradcafe.com" in parsed.netloc.lower()
        and parsed.path.rstrip("/") == "/survey"
        and not parsed.query
        and not parsed.fragment
    )


def _contains_next_word(text: str) -> bool:
    words = text.replace("→", " next ").replace("›", " next ").replace("»", " next ").split()
    return "next" in words


def _next_url_from_html(html: str, current_url: str) -> str | None:
    soup = BeautifulSoup(html, "html.parser")

    node = soup.find("a", rel=lambda value: value and "next" in str(value).lower())
    if node and node.get("href"):
        return urljoin(current_url, node["href"])

    for anchor in soup.find_all("a", href=True):
        label = " ".join(
            filter(
                None,
                [anchor.get_text(" ", strip=True), anchor.get("aria-label"), anchor.get("title")],
            )
        ).lower()
        if _contains_next_word(label):
            return urljoin(current_url, anchor["href"])
    return None


def _click_next(driver: webdriver.Chrome) -> bool:
    xpaths = [
        "//a[contains(translate(normalize-space(.),'NEXT','next'),'next')]",
        "//button[contains(translate(normalize-space(.),'NEXT','next'),'next')]",
        "//*[@aria-label and contains(translate(@aria-label,'NEXT','next'),'next')]",
        "//*[@title and contains(translate(@title,'NEXT','next'),'next')]",
    ]
    for xpath in xpaths:
        try:
            element = driver.find_element(By.XPATH, xpath)
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", element)
            element.click()
            return True
        except (NoSuchElementException, WebDriverException):
            continue
    return False


def _wait_for_change(driver: webdriver.Chrome, old_hash: str, timeout: int = 30) -> None:
    def changed(d):
        html = d.page_source
        new_hash = hashlib.sha1(html.encode("utf-8", errors="ignore")).hexdigest()
        return new_hash != old_hash

    WebDriverWait(driver, timeout).until(changed)


def _load_state(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _save_state(path: Path, *, last_url: str, resume_url: str | None, records: int) -> None:
    payload = {
        "version": 1,
        "last_url": last_url,
        "resume_url": resume_url,
        "records": records,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def capture(
    target: int,
    output: Path,
    pages_dir: Path,
    state_file: Path,
    delay_min: float,
    delay_max: float,
    resume: bool,
    novelty_window: int,
    min_new_ratio: float,
    require_root_start: bool,
) -> None:
    options = webdriver.ChromeOptions()
    options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    driver = webdriver.Chrome(options=options)

    # Never silently choose among several stale GradCafe tabs.
    _select_single_gradcafe_tab(driver)
    print(f"Using browser tab: {driver.current_url}")

    if require_root_start and not _is_root_survey_url(driver.current_url):
        raise RuntimeError(
            "Recovery capture must begin from exactly https://www.thegradcafe.com/survey "
            "with no ?cursor=... query string. Navigate the debug Chrome tab to the root "
            "survey URL and rerun the same command. If recovery files already exist, do NOT "
            "delete them; the saved state will resume from the correct cursor after this check."
        )

    # If a prior run saved the exact next cursor, resume there in the already-verified browser.
    state = _load_state(state_file)
    resume_url = state.get("resume_url") if resume else None
    if resume_url:
        print(f"Resuming from saved cursor: {resume_url}")
        driver.get(build_url(resume_url))
        WebDriverWait(driver, 30).until(lambda d: d.execute_script("return document.readyState") == "complete")

    existing = load_data(output)
    records = deduplicate(existing)
    pages_dir.mkdir(parents=True, exist_ok=True)
    page_no = 1
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    novelty = deque(maxlen=max(1, novelty_window))

    print(f"Starting with {len(records)} existing records.")
    print("The script will stop rather than bypass Cloudflare, CAPTCHAs, or rate limits.")

    while len(records) < target:
        current_url = build_url(driver.current_url)
        parsed_url = urlparse(current_url)
        if "thegradcafe.com" not in parsed_url.netloc.lower() or not parsed_url.path.startswith("/survey"):
            print("The selected tab is no longer a GradCafe survey page. Stopping safely.")
            break

        html = driver.page_source
        title = driver.title
        if _blocked(html, title):
            print("Site appears to be blocking or challenging the browser. Stopping as required.")
            break

        # Session-prefixed names prevent later runs from overwriting earlier diagnostic pages.
        page_path = pages_dir / f"{session_id}_page_{page_no:04d}.html"
        page_path.write_text(html, encoding="utf-8")

        parsed = parse_html(html, page_url=current_url)
        before = len(records)
        records = deduplicate([*records, *parsed])
        save_data(records, output)
        added = len(records) - before

        next_url = _next_url_from_html(html, current_url)
        _save_state(
            state_file,
            last_url=current_url,
            resume_url=build_url(next_url) if next_url else None,
            records=len(records),
        )

        novelty.append((len(parsed), added))
        print(f"Page {page_no}: parsed {len(parsed)}, added {added}, total {len(records)}")

        if len(records) >= target:
            break
        if not parsed:
            print("No applicant rows were parsed from this page. Stopping for inspection.")
            break

        # A long stretch of mostly duplicates is usually a stale-tab/restart problem.
        if len(novelty) == novelty.maxlen:
            parsed_recent = sum(p for p, _ in novelty)
            added_recent = sum(a for _, a in novelty)
            ratio = (added_recent / parsed_recent) if parsed_recent else 0.0
            if ratio < min_new_ratio:
                print(
                    f"Recent novelty ratio is only {ratio:.1%} over {len(novelty)} pages "
                    f"({added_recent} new / {parsed_recent} parsed)."
                )
                print(
                    "Stopping to avoid rereading a stale/overlapping cursor. Check open GradCafe "
                    "tabs and capture_state.json before continuing."
                )
                break

        old_hash = hashlib.sha1(html.encode("utf-8", errors="ignore")).hexdigest()

        try:
            if next_url and build_url(next_url) != current_url:
                driver.get(build_url(next_url))
            elif not _click_next(driver):
                print("Could not find a Next-page control. Stopping.")
                break
            _wait_for_change(driver, old_hash)
        except Exception as exc:
            print(f"Navigation stopped: {exc}")
            break

        # If navigation used a click fallback, record the actual new cursor too.
        if not next_url:
            _save_state(
                state_file,
                last_url=current_url,
                resume_url=build_url(driver.current_url),
                records=len(records),
            )

        time.sleep(random.uniform(delay_min, delay_max))
        page_no += 1

    save_data(records, output)
    print(f"Finished with {len(records)} records in {output}")
    print(f"Resume state: {state_file}")


def main() -> None:  # pragma: no cover - CLI wrapper
    parser = argparse.ArgumentParser(
        description="Capture verified GradCafe result pages from an already-open Chrome session"
    )
    parser.add_argument("--target", type=int, default=30000)
    parser.add_argument("--output", type=Path, default=Path("applicant_data.json"))
    parser.add_argument("--pages-dir", type=Path, default=Path("captured_pages"))
    parser.add_argument("--state-file", type=Path, default=Path("capture_state.json"))
    parser.add_argument("--delay-min", type=float, default=2.0)
    parser.add_argument("--delay-max", type=float, default=4.0)
    parser.add_argument("--no-resume", action="store_true", help="Ignore capture_state.json for this run")
    parser.add_argument("--novelty-window", type=int, default=50)
    parser.add_argument(
        "--min-new-ratio",
        type=float,
        default=0.20,
        help="Stop if fewer than this fraction of recently parsed rows are new",
    )
    parser.add_argument(
        "--require-root-start",
        action="store_true",
        help=(
            "Refuse to start unless the selected debug-Chrome tab is exactly "
            "https://www.thegradcafe.com/survey with no cursor. Recommended for recovery captures."
        ),
    )
    args = parser.parse_args()

    if args.target <= 0:
        parser.error("--target must be greater than zero")
    if args.delay_min < 0 or args.delay_max < 0:
        parser.error("Delay values cannot be negative")
    if args.delay_min > args.delay_max:
        parser.error("--delay-min cannot be greater than --delay-max")
    if args.novelty_window <= 0:
        parser.error("--novelty-window must be greater than zero")
    if not 0 <= args.min_new_ratio <= 1:
        parser.error("--min-new-ratio must be between 0 and 1")

    try:
        capture(
            args.target,
            args.output,
            args.pages_dir,
            args.state_file,
            args.delay_min,
            args.delay_max,
            not args.no_resume,
            args.novelty_window,
            args.min_new_ratio,
            args.require_root_start,
        )
    except KeyboardInterrupt:
        print("\nCapture interrupted by user.")
        print(
            "Progress through the last completed page was already written to the output and "
            "state files. Do NOT delete the recovery files. Reopen the root /survey page in "
            "debug Chrome and rerun the same command to resume."
        )


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main()
