from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

REQUIRED_FILES = [
    "scrape.py",
    "clean.py",
    "requirements.txt",
    "README.md",
    "screenshot.jpg",
    "applicant_data.json",
    "llm_extend_applicant_data.json",
]

REQUIRED_DIRS = ["llm_hosting"]

RAW_MINIMUM = 30000


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _git_output(args: list[str], cwd: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Final local audit for Module 2 submission")
    parser.add_argument("--module-dir", type=Path, default=Path("."))
    args = parser.parse_args()

    module_dir = args.module_dir.resolve()
    print(f"Module directory: {module_dir}")

    failures = 0

    print("\n[Required files]")
    for name in REQUIRED_FILES:
        path = module_dir / name
        ok = path.is_file() and path.stat().st_size > 0
        print(f"{'PASS' if ok else 'FAIL'}  {name}")
        failures += 0 if ok else 1

    print("\n[Required directories]")
    for name in REQUIRED_DIRS:
        path = module_dir / name
        ok = path.is_dir() and any(path.iterdir())
        print(f"{'PASS' if ok else 'FAIL'}  {name}/")
        failures += 0 if ok else 1

    raw_path = module_dir / "applicant_data.json"
    print("\n[Raw JSON]")
    if raw_path.is_file():
        try:
            raw = _load_json(raw_path)
            is_list = isinstance(raw, list)
            count = len(raw) if is_list else 0
            print(f"{'PASS' if is_list else 'FAIL'}  valid top-level JSON list")
            print(f"{'PASS' if count >= RAW_MINIMUM else 'FAIL'}  record count = {count} (minimum {RAW_MINIMUM})")
            failures += 0 if is_list else 1
            failures += 0 if count >= RAW_MINIMUM else 1
        except Exception as exc:
            print(f"FAIL  could not load raw JSON: {exc}")
            failures += 1
    else:
        print("FAIL  applicant_data.json missing")
        failures += 1

    llm_path = module_dir / "llm_extend_applicant_data.json"
    print("\n[LLM JSON]")
    if llm_path.is_file():
        try:
            llm = _load_json(llm_path)
            is_list = isinstance(llm, list)
            print(f"{'PASS' if is_list else 'FAIL'}  valid top-level JSON list")
            if is_list:
                print(f"INFO  record count = {len(llm)}")
            failures += 0 if is_list else 1
        except Exception as exc:
            print(f"FAIL  could not load LLM JSON: {exc}")
            failures += 1
    else:
        print("FAIL  llm_extend_applicant_data.json missing")
        failures += 1

    screenshot = module_dir / "screenshot.jpg"
    print("\n[robots.txt evidence]")
    if screenshot.is_file() and screenshot.stat().st_size > 0:
        print(f"PASS  screenshot.jpg exists ({screenshot.stat().st_size:,} bytes)")
    else:
        print("FAIL  screenshot.jpg missing or empty")
        failures += 1

    captured = module_dir / "captured_pages"
    print("\n[Working artifacts]")
    if captured.exists():
        print("INFO  captured_pages/ exists locally; confirm it remains ignored by Git")
    else:
        print("PASS  no local captured_pages/ directory")

    repo_root = module_dir.parent
    print("\n[Git]")
    status = _git_output(["status", "--short"], repo_root)
    remote = _git_output(["remote", "get-url", "origin"], repo_root)
    branch = _git_output(["branch", "--show-current"], repo_root)

    if status is None:
        print("WARN  could not inspect Git repository automatically")
    else:
        print(f"INFO  branch: {branch or '(unknown)'}")
        print(f"INFO  origin: {remote or '(missing)'}")
        if status:
            print("INFO  working tree has changes:")
            print(status)
        else:
            print("PASS  working tree clean")

    if remote and remote.startswith("git@github.com:"):
        print("PASS  origin is an SSH-style GitHub URL")
    elif remote:
        print("WARN  origin is not SSH-style; assignment submission expects the SSH URL")

    print("\n[Result]")
    if failures:
        print(f"NOT READY: {failures} required local check(s) failed.")
        raise SystemExit(1)

    print("LOCAL DELIVERABLE CHECKS PASS. Perform the final GitHub privacy/push inspection before submitting.")


if __name__ == "__main__":
    main()
