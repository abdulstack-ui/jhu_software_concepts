# Local LLM setup — Windows

Do this in a second PowerShell after the raw scrape is safely checkpointed. The model is CPU-heavy, so do not run the full 30k cleaning job while the scraper is still collecting.

## 1. Confirm Python versions

```powershell
py -0p
python --version
```

The assignment permits Python 3.10+. The current project was scraped with Python 3.13.

## 2. Create an isolated LLM environment

```powershell
cd C:\Users\DELL\Desktop\jhu_software_concepts\module_2\llm_hosting
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If `llama-cpp-python` cannot install under Python 3.13, stop and capture the error. Do not randomly install unrelated packages. A Python 3.12 venv is an allowed fallback if `py -0p` shows 3.12 installed:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## 3. Smoke test the instructor sample

```powershell
python app.py --file sample_data.json --out sample_out.json --format json --workers 1
python -c "import json; d=json.load(open('sample_out.json', encoding='utf-8')); print(len(d)); print(d[0])"
```

Expected: 3 rows, each preserving its original fields and adding `llm-generated-program` and `llm-generated-university`.

The first run downloads the TinyLlama GGUF model. The model is stored under `llm_hosting/models/` and is intentionally ignored by Git.

## 4. Run the real dataset after raw scraping reaches 30,000+

From `module_2` with the LLM venv still active:

```powershell
cd ..
python clean.py --input applicant_data.json --output llm_extend_applicant_data.json --workers 2
```

Start with 2 workers. Each worker loads its own model, so more workers can consume large amounts of RAM. If memory pressure is high, use `--workers 1`.

## 5. Validate the final file

```powershell
python -c "import json; d=json.load(open('llm_extend_applicant_data.json', encoding='utf-8')); print(len(d)); print(d[0].get('llm-generated-program')); print(d[0].get('llm-generated-university'))"
```

The final row count should match the raw input count, and the original raw/program fields must still be present.
