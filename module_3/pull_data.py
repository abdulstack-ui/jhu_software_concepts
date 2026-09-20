"""Background Pull Data worker for the Module 3 Flask application.

This worker reuses the Module 2 Selenium capture/parser instead of implementing a
second scraper. It starts from the newest GradCafe survey page in the already-open,
verified debug-Chrome session, captures only enough pages to discover new records,
conservatively cleans usable records, upserts them into the existing PostgreSQL
``applicants`` table, and updates the canonical JSON files.

The worker never bypasses Cloudflare/CAPTCHA challenges. If GradCafe requires
verification, the user must complete it manually in Chrome first.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from capture import capture
from clean import clean_record, validate_cleaned_records
from load_data import (
    connect_database,
    count_database_rows,
    create_applicants_table,
    upsert_records,
)
from scrape import deduplicate, load_data as load_raw_data

ROOT = Path(__file__).resolve().parent
RAW_PATH = ROOT / "applicant_data.json"
LLM_PATH = ROOT / "llm_extend_applicant_data.json"
CLEAN_PATH = ROOT / "cleaned_applicant_data.json"

WORK_PATH = ROOT / "pull_data_work.json"
PAGES_DIR = ROOT / "pull_data_pages"
CAPTURE_STATE = ROOT / "pull_data_capture_state.json"
STATUS_PATH = ROOT / "pull_data_status.json"
LOCK_PATH = ROOT / "pull_data.lock"

DEFAULT_TARGET_INCREMENT = 100
DEFAULT_NOVELTY_WINDOW = 5
DEFAULT_MIN_NEW_RATIO = 0.10


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_write_json(path: Path, payload: Any) -> None:
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(temp, path)


def _write_status(state: str, message: str, **extra: Any) -> None:
    payload = {
        "state": state,
        "message": message,
        "updated_at": _utc_now(),
        **extra,
    }
    _atomic_write_json(STATUS_PATH, payload)


def _load_json_list(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"Expected a JSON array in {path.name}")
    if not all(isinstance(row, dict) for row in data):
        raise ValueError(f"Expected object records in {path.name}")
    return data


def _url(record: dict[str, Any]) -> str | None:
    value = record.get("entry_url") or record.get("url")
    return str(value).strip() if value else None


def _merge_by_url(
    existing: Iterable[dict[str, Any]], new_records: Iterable[dict[str, Any]]
) -> list[dict[str, Any]]:
    output = list(existing)
    seen = {_url(row) for row in output if _url(row)}
    for row in new_records:
        key = _url(row)
        if key and key not in seen:
            output.append(row)
            seen.add(key)
    return output


def _merge_cleaned(
    existing: Iterable[dict[str, Any]], new_records: Iterable[dict[str, Any]]
) -> list[dict[str, Any]]:
    output = list(existing)
    seen = {int(row["p_id"]) for row in output}
    for row in new_records:
        p_id = int(row["p_id"])
        if p_id not in seen:
            output.append(row)
            seen.add(p_id)
    validate_cleaned_records(output)
    return output


def _llm_placeholder_record(raw: dict[str, Any]) -> dict[str, Any]:
    """Preserve source data while marking not-yet-LLM-standardized fields missing."""
    row = dict(raw)
    row.setdefault("llm-generated-program", None)
    row.setdefault("llm-generated-university", None)
    return row


def _acquire_lock() -> int:
    try:
        descriptor = os.open(LOCK_PATH, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise RuntimeError(
            "Pull Data is already running, or a stale pull_data.lock remains from an "
            "interrupted process. Do not start a second scraper."
        ) from exc
    os.write(descriptor, f"pid={os.getpid()} started={_utc_now()}\n".encode("utf-8"))
    return descriptor


def _release_lock(descriptor: int | None) -> None:
    if descriptor is not None:
        try:
            os.close(descriptor)
        except OSError:
            pass
    try:
        LOCK_PATH.unlink()
    except FileNotFoundError:
        pass


def run_pull() -> dict[str, Any]:
    """Capture, clean, and load newly available GradCafe records."""
    existing_raw = load_raw_data(RAW_PATH)
    if not existing_raw:
        raise RuntimeError("applicant_data.json is missing or empty; refusing to replace the baseline.")

    existing_urls = {_url(row) for row in existing_raw if _url(row)}
    _atomic_write_json(WORK_PATH, existing_raw)

    increment = max(1, int(os.getenv("PULL_DATA_TARGET_INCREMENT", DEFAULT_TARGET_INCREMENT)))
    target = len(existing_raw) + increment

    _write_status(
        "running",
        "Retrieving newly available GradCafe records using the Module 2 scraper.",
        existing_records=len(existing_raw),
    )

    # capture.py writes page snapshots to the supplied directory but assumes
    # that directory already exists. Create it so the first Pull Data run works
    # in a fresh checkout and after local runtime cleanup.
    PAGES_DIR.mkdir(parents=True, exist_ok=True)

    # Start at the root/newest survey page every time. The temporary output is
    # pre-seeded with known records, so capture.py's deduplication counts only
    # genuinely new URLs toward the target. A short novelty window stops the run
    # after it reaches already-known pages when fewer than `increment` records exist.
    capture(
        target=target,
        output=WORK_PATH,
        pages_dir=PAGES_DIR,
        state_file=CAPTURE_STATE,
        delay_min=2.0,
        delay_max=4.0,
        resume=False,
        novelty_window=DEFAULT_NOVELTY_WINDOW,
        min_new_ratio=DEFAULT_MIN_NEW_RATIO,
        require_root_start=True,
    )

    captured = load_raw_data(WORK_PATH)
    new_raw = [row for row in captured if _url(row) and _url(row) not in existing_urls]

    usable_raw: list[dict[str, Any]] = []
    new_cleaned: list[dict[str, Any]] = []
    skipped = 0
    for row in new_raw:
        try:
            cleaned = clean_record(row)
            # Validate one record structurally without requiring all optional fields.
            validate_cleaned_records([cleaned])
        except (TypeError, ValueError):
            skipped += 1
            continue
        usable_raw.append(row)
        new_cleaned.append(cleaned)

    if not new_cleaned:
        result = {
            "discovered": len(new_raw),
            "added": 0,
            "skipped": skipped,
            "database_before": None,
            "database_after": None,
        }
        _write_status(
            "complete",
            "Pull Data finished. No new usable records were available to add.",
            **result,
        )
        return result

    # Prepare all file updates before touching PostgreSQL.
    existing_llm = _load_json_list(LLM_PATH)
    existing_cleaned = _load_json_list(CLEAN_PATH)

    merged_raw = deduplicate([*existing_raw, *usable_raw])
    merged_llm = _merge_by_url(
        existing_llm,
        (_llm_placeholder_record(row) for row in usable_raw),
    )
    merged_cleaned = _merge_cleaned(existing_cleaned, new_cleaned)

    # Upsert only newly discovered records into the existing one-table database.
    with connect_database() as connection:
        create_applicants_table(connection)
        before = count_database_rows(connection)
        upsert_records(connection, new_cleaned)
        after = count_database_rows(connection)

    # Persist source/derived JSON only after the database transaction succeeds.
    _atomic_write_json(RAW_PATH, merged_raw)
    _atomic_write_json(LLM_PATH, merged_llm)
    _atomic_write_json(CLEAN_PATH, merged_cleaned)

    result = {
        "discovered": len(new_raw),
        "added": len(new_cleaned),
        "skipped": skipped,
        "database_before": before,
        "database_after": after,
    }
    _write_status(
        "complete",
        f"Pull Data finished. Added {len(new_cleaned):,} new usable record(s) to PostgreSQL.",
        **result,
    )
    return result


def main() -> None:
    descriptor: int | None = None
    try:
        descriptor = _acquire_lock()
        result = run_pull()
        print(
            "Pull Data complete: "
            f"discovered={result['discovered']}, added={result['added']}, skipped={result['skipped']}"
        )
    except Exception as exc:
        _write_status(
            "error",
            (
                "Pull Data stopped without modifying the canonical files. "
                f"{type(exc).__name__}: {exc}"
            ),
        )
        raise
    finally:
        _release_lock(descriptor)


if __name__ == "__main__":
    main()
