# Module 3 Checkpoint 01 — Baseline and Cleaned Data Pipeline

## Objective

Establish a reproducible Module 3 starting point from the submitted Module 2 work before any PostgreSQL, SQL, ORM, or Flask implementation is added.

## Requirements covered

- Module 2 scraper/code/data copied forward into `module_3`.
- LLM-extended Module 2 data preserved.
- Separate database-ready cleaning step created in `clean.py`.
- Output schema matches the 15 Module 3 `applicants` columns exactly.
- Missing values stay missing; no GPA/GRE/term/nationality/degree values are fabricated or inferred.
- `p_id` comes from the numeric identifier already embedded in each GradCafe result URL.
- Cleaned data is validated for exact field set, integer IDs, required core fields, and duplicate IDs/URLs.
- README documents provenance, cleaning rules, commands, and known data limitations.
- `.gitignore` excludes local secrets and generated/runtime artifacts.

## Validation performed

Commands:

```powershell
python clean.py --input llm_extend_applicant_data.json --output cleaned_applicant_data.json
python checkpoint_01_audit.py
python data_preflight.py
```

Checkpoint audit result:

```text
CHECKPOINT 01 AUDIT: PASS
Rows verified: 30,011
Unique p_id values: 30,011
Unique URLs: 30,011
No GPA/GRE/term/nationality/degree values were inferred beyond source fields.
```

Structural validation:

```text
Rows with wrong field set: 0
Duplicate p_id values: 0
Duplicate non-null URLs: 0
```

## Known data-readiness issue

The captured public GradCafe survey listing pages contain zero populated values for `term`, `us_or_international`, `gpa`, `gre`, `gre_v`, and `gre_aw`. The assignment permits missing values, so these remain `NULL`; they must not be guessed. However, several required Module 3 analyses depend on those fields, so this issue must be resolved with source-supported data or instructor guidance before the analysis checkpoint can be considered final.

## Git checkpoint name

After committing the files for this checkpoint, tag the commit:

```powershell
git tag -a m3-checkpoint-01-baseline -m "Module 3 checkpoint 01: baseline and cleaned data pipeline"
git push origin m3-checkpoint-01-baseline
```

Recommended commit message:

```text
Harden Module 3 baseline cleaning and checkpoint audit
```
