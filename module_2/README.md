# Module 2 - Web Scraping

## Name
Muhammad Abdullah Sarwar  
JHED ID: **ABE84F**

## Module Info
Module 2 - Assignment: Web Scraping  
Due: Sunday, September 13, 2026, 11:59 PM

## Responsible scraping / robots.txt
Before scraping, I manually reviewed `https://www.thegradcafe.com/robots.txt` in a normal browser. The generic `User-agent: *` rules allow `/` while explicitly disallowing authentication/account-related routes including `/signin`, `/register`, `/forgot-password`, `/reset-password`, `/confirm-password`, `/verify-email`, and `/profile`. The public admissions-results pages used for this assignment are not listed as disallowed. The site also advertises a content signal that permits search/reference use while disallowing AI training.

This project is limited to the public applicant listings required for the course. It does not scrape account/private routes and does not attempt to bypass CAPTCHAs, Cloudflare verification, rate limits, login requirements, or other access controls. If the site blocks/challenges/rejects the browser, the collection script stops.

The required evidence is stored as `screenshot.jpg`: a screenshot of the GradCafe `robots.txt` page in Chrome showing the applicable rules.

## Approach
The implementation separates acquisition, parsing, cleaning, and persistence.

1. GradCafe URLs are constructed and validated using `urllib.parse`.
2. Because direct automated HTTP requests may currently receive HTTP 403 and a newly automated Selenium browser may be challenged by Cloudflare, a normal Chrome window is launched with Chrome remote debugging enabled.
3. Any Cloudflare verification is completed manually by the user in that normal Chrome window. The script does not solve or bypass the challenge.
4. `capture.py` attaches Selenium to that already-open Chrome session, captures the current rendered HTML, saves each page under `captured_pages/`, parses the page, checkpoints to `applicant_data.json`, and follows the public Next-page control with a polite delay.
5. `scrape.py` uses BeautifulSoup plus regex/string methods to extract the requested fields. The parser looks for the admissions table semantically by its School / Program / Added On / Decision columns rather than depending on one fragile CSS class.
6. Original program text and full raw listing text are preserved for traceability.
7. Missing values use Python `None`, which is serialized as JSON `null`.
8. Records are deduplicated before each checkpoint, so the run can resume from an existing JSON file.
9. `clean.py` removes remnant HTML entities and normalizes whitespace without destructively modifying applicant-provided content.
10. The provided `llm_hosting` package is run after scraping to add standardized program/university values while preserving the original fields.

## Project layout

```text
module_2/
â”œâ”€â”€ capture.py
â”œâ”€â”€ scrape.py
â”œâ”€â”€ clean.py
â”œâ”€â”€ requirements.txt
â”œâ”€â”€ applicant_data.json
â”œâ”€â”€ screenshot.jpg
â”œâ”€â”€ captured_pages/
â”œâ”€â”€ llm_hosting/
â””â”€â”€ llm_extend_applicant_data.json
```

## Setup on Windows
From PowerShell:

```powershell
cd C:\Users\DELL\Desktop\jhu_software_concepts\module_2
python -m pip install -r requirements.txt
```

Close ordinary Chrome windows first, then launch a dedicated Chrome window with a debugging port:

```powershell
& "C:\Program Files\Google\Chrome\Application\chrome.exe" `
  --remote-debugging-port=9222 `
  --user-data-dir="$env:TEMP\gradcafe_chrome"
```

If Chrome is installed under Program Files (x86), use that Chrome path instead.

In this Chrome window:

1. Open `https://www.thegradcafe.com/survey`.
2. Complete any normal Cloudflare verification manually.
3. Leave the public admissions-results page visible after any manual verification.
4. Do not navigate away from or close the attached Chrome session while collection is running.

Then, in a second PowerShell window:

```powershell
cd C:\Users\DELL\Desktop\jhu_software_concepts\module_2
python capture.py --target 30000
```

The script saves each page HTML and checkpoints `applicant_data.json` after every page. If collection is interrupted, rerun the same command; existing records are loaded and deduplicated. If GradCafe presents a Cloudflare challenge, access denial, or rate-limit page, the script stops rather than attempting to evade it.

## Parse saved HTML manually
A captured/saved page can also be parsed independently:

```powershell
python scrape.py --html captured_pages\page_0001.html --output test_data.json --page-url "https://www.thegradcafe.com/survey"
```

Validate JSON:

```powershell
python -c "from scrape import load_data; print(len(load_data('applicant_data.json')))"
```

## Local LLM standardization
The instructor-provided `llm_hosting` package is included under `module_2/llm_hosting`. The original package files are preserved alongside the locally adapted versions for traceability. See `llm_hosting/LOCAL_CHANGES.md`.

The live 2026 GradCafe page now exposes program and university in separate cells, while the supplied LLM sample expects a single legacy `program` field containing both. The adapted standardizer therefore combines the already-parsed `program_name` and `university` only for the model prompt, while preserving every original field in the output. It appends:

- `llm-generated-program`
- `llm-generated-university`

The adapted CLI also writes a valid JSON array rather than JSONL because the required deliverable is `llm_extend_applicant_data.json`. Repeated identical program/university inputs are cached so the local model does not redo identical work. Optional worker-level parallelism is available, but each worker loads its own model, so the recommended laptop starting point is two workers.

Setup and smoke-test commands are in `LLM_SETUP_WINDOWS.md`. After raw scraping reaches 30,000+ rows:

```powershell
cd C:\Users\DELL\Desktop\jhu_software_concepts\module_2
python clean.py --input applicant_data.json --output llm_extend_applicant_data.json --workers 2
python verify_llm_output.py applicant_data.json llm_extend_applicant_data.json
```

### Cleaning edge cases / remaining imperfections
The canonical/post-processing layer handles common abbreviations and spelling variants, but a tiny local model can still produce imperfect mappings for rare interdisciplinary programs, schools with multiple campuses, abbreviations that are ambiguous across institutions, or program names whose official title differs substantially from applicant wording. The original `program_name`, `university`, `raw_program_text`, and `raw_listing_text` fields are retained so these cases can be audited and canonical lists can be extended without losing source traceability.

## Known Bugs / Limitations
- GradCafe is a live website, so markup and pagination controls can change. The parser therefore uses semantic table headers and a generic fallback, but a future layout change may require updating selectors.
- Cloudflare may still challenge an attached browser session. The program intentionally stops instead of bypassing the restriction.
- The local TinyLlama stage was successfully installed and run under Python 3.13 using the CPU build of `llama-cpp-python`. The reproducible setup is documented in `LLM_SETUP_WINDOWS.md` and `llm_hosting/LOCAL_CHANGES.md`.

## Final validation before submission

Run the raw-data audit after collection:

```powershell
python verify_output.py applicant_data.json --minimum 30000
```

Before submission, verify that the final repository contains the required raw JSON, LLM-extended JSON, robots.txt screenshot, source files, `llm_hosting/`, README, and requirements file; that `captured_pages/` and local environments are not accidentally committed; and that the repository remains private. See `ASSIGNMENT_CHECKLIST.md` for the rubric-by-rubric control sheet and `GITHUB_SETUP.md` for the final repository workflow. Run `submission_audit.py` before the final commit/push.

## Checkpoint/resume safety

The scraper writes a local `capture_state.json` after each successfully parsed page. It stores the exact next GradCafe cursor URL so an interrupted run can continue from that cursor instead of starting from whichever browser tab Selenium happens to attach to. The state file is intentionally excluded from Git because it is runtime state, not a deliverable.

The capture helper also refuses to proceed when more than one GradCafe `/survey` tab is open. This avoids a failure mode observed during development where a restart attached to an older tab and reread many already-collected rows. `inspect_gradcafe_tabs.py` can be used to list the currently attached Chrome tabs and decode GradCafe cursor metadata for debugging.

## Final LLM run and validation

The final raw dataset contains 30,011 GradCafe records. The local TinyLlama
standardization stage reduced these to 12,636 unique program/university inputs
through caching and processed all 12,636 inputs with two worker processes.

The adapted cleaner preserves every original scraped field and appends:

- `llm-generated-program`
- `llm-generated-university`

A real-data smoke test and subsequent full-dataset quality audit showed that the
small local model could occasionally introduce semantic drift. I therefore
added conservative deterministic post-processing that preserves source
acronyms, recognizes selected university abbreviations/canonical spellings,
compares normalized semantic terms, and falls back to the original parsed value
when a proposed model change is insufficiently supported.

After the full model run, a stricter post-processing pass rejected 2,111
questionable program candidates and 990 questionable university candidates
without rerunning the model.

Final validation results:

- 30,011 raw rows
- 30,011 LLM-extended rows
- zero missing LLM-generated keys
- zero empty generated program values
- zero unknown/empty generated university values
- zero modifications to any original scraped field
- valid JSON
- previously identified semantic-drift regressions eliminated

The GGUF model weights and local virtual environment are intentionally excluded
from Git because they are large and reproducible from the provided requirements
and setup files.

### Data limitations

The captured public survey-listing pages did not expose GPA, GRE values,
student type, or program-start semester/year, so those fields remain `null`
rather than being fabricated.

The captured listing blocks also did not expose applicant comment bodies. An
earlier parser fallback interpreted the decision fragment `Wait listed on` as a
comment for 2,585 rows. Those values were corrected to `null`, the parser was
regression-tested, and the raw listing text remains preserved for traceability.

During collection, a malformed checkpoint was handled conservatively by
excluding the suspect records and continuing collection into older genuine
public GradCafe entries. No records were fabricated. The final dataset contains
30,011 unique non-null result URLs.

