# Module 2 Assignment Control Sheet

This file is the working rubric map for the GradCafe web-scraping assignment.

## Deliverables / repository

- Private GitHub repository: `jhu_software_concepts`
- Work lives under `module_2/`
- Submit repository SSH URL
- Required/expected files in final `module_2/`:
  - `scrape.py`
  - `clean.py`
  - `llm_hosting/` (instructor-supplied package)
  - `applicant_data.json` with at least 30,000 real entries
  - `llm_extend_applicant_data.json`
  - `screenshot.jpg` showing the reviewed GradCafe `robots.txt`
  - `README.md`
  - `requirements.txt`
- `capture.py` is an implementation helper for the instructor's current Cloudflare workaround.
- Do not commit `captured_pages/` unless the instructor specifically asks for the raw HTML snapshots.

## Rubric map

### Repository / setup — 15
- Correct private repository and `module_2` layout.
- Reproducible setup/run instructions.
- `requirements.txt` present.
- All final deliverables committed.
- Repository SSH URL ready for submission.

### robots.txt / responsible scraping — 12
- `robots.txt` manually reviewed.
- `screenshot.jpg` included.
- README explains applicable rules.
- Public pages only.
- No login/private/account paths.
- Polite delay.
- Stop on challenge, block, rejection, or rate limiting.
- No CAPTCHA/Cloudflare bypass, fingerprint spoofing, secret/private APIs, or access-control evasion.

### Scraping — 18
- Programmatically collect GradCafe applicant data.
- At least 30,000 real records.
- Use Python 3.10+.
- Use `urllib` facilities for URL construction/inspection/management.
- Handle pagination/current site behavior.
- Checkpoint so an interrupted run does not destroy collected data.
- Current-semester workaround uses a manually verified normal Chrome session and a helper that captures visible public HTML; automation must not defeat verification.

### Parsing — 15
Capture fields when available:
- Program Name
- University
- Comments
- Date Added
- Applicant/result URL
- Status
- Acceptance/Rejection decision date
- Semester/year start
- International/American/Other
- GRE
- GRE V
- Masters/PhD
- GPA
- GRE AW

Also:
- Preserve original/raw program/listing text for traceability.
- Consistent missing values (`None` -> JSON `null` is acceptable).
- No remnant HTML tags/entities after cleaning.
- Handle messy/missing information robustly.

### JSON — 10
- Valid JSON.
- Descriptive keys.
- `applicant_data.json` contains >= 30,000 entries.
- No fabricated records.

### Local LLM cleaning — 12
- Put instructor package under `module_2/llm_hosting/`.
- Run local model on Part 1 JSON.
- Produce `llm_extend_applicant_data.json`.
- Preserve original program/university information.
- Add standardized program/university fields rather than erasing traceability.
- Use supplied canonical/post-processing/fuzzy matching logic as intended.
- Document code/system-version fixes and systematic edge cases in README.

### Structure / reproducibility — 10
- Clear separation of scraping, cleaning, persistence, and LLM standardization.
- Functions/helpers with clear names.
- Expected methods/helpers include `scrape_data`, `clean_data`, `save_data`, `load_data`; rubric-friendly private helpers include `_parse_entry` and `_normalize_status`.
- README lets another person reproduce the workflow.

### Quality — 8
- Clear variable/function names.
- Useful comments/docstrings, not noise.
- Robust error handling.
- Ethical behavior is visible in code, not merely claimed in README.
- No dead/debug code or accidental secrets.

## Current checkpoint

Known working from the user's terminal run:
- 20-record smoke test passed.
- 100-record pagination test passed.
- 1,000-record test reached 1,015 unique records over 52 pages.
- JSON checkpointing and deduplication are functioning.

Still unverified / incomplete:
- Corrected `capture.py` tab-selection fix must be tested on the 30,000-record run.
- Raw scrape currently in progress; final count must be >= 30,000.
- Field-quality audit against captured HTML, especially comments and optional metrics.
- `screenshot.jpg` presence has not yet been confirmed.
- Instructor `llm_hosting` package not yet integrated in this checkpoint.
- LLM output not yet produced/audited.
- Final README system-specific notes not yet complete.
- Final Git status/private remote/SSH URL not yet audited.

## Gate rule

Do not call the assignment finished merely because the scraper reaches 30,000. Completion requires the raw data audit, LLM standardization, final repository audit, and rubric-by-rubric verification.


## Checkpoint 02 additions

- Added `GITHUB_SETUP.md` with the exact local repository, staging, commit, push, and SSH-URL verification workflow.
- Added `submission_audit.py` to check required deliverables, raw JSON count, LLM JSON validity, robots screenshot, `llm_hosting/`, and basic Git state before submission.
- Updated README so it no longer assumes a 250-results-per-page control; the observed live GradCafe results currently paginate at 20 records per page.
- Next gate remains: finish raw collection, run `verify_output.py`, then audit field quality before LLM standardization.

## Checkpoint 03 — LLM package received/integrated
- [x] Instructor `llm_hosting` package received
- [x] Original LLM package files preserved for traceability
- [x] Current scraper field names mapped to LLM input without destructive changes
- [x] Final LLM output path/format aligned to `llm_extend_applicant_data.json` valid JSON
- [x] Model directory ignored by Git
- [x] LLM output validator added
- [ ] Confirm JHED ID in README
- [ ] Raw scrape reaches >=30,000 unique records
- [ ] LLM dependency install smoke test passes on student's Windows machine
- [ ] `sample_data.json` smoke test passes
- [ ] Full LLM cleaning run completes
- [ ] `verify_llm_output.py` passes
- [ ] Final meaningful Git commits/push and Canvas zip submission
