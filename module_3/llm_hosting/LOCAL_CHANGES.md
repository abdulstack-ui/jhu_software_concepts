# Local changes for Module 2

The instructor package is preserved in this folder as:
- `app_instructor_original.py`
- `requirements_instructor_original.txt`
- `README_INSTRUCTOR.md`

Local adaptations were required because the live 2026 GradCafe page and the student's scraper differ from the older sample shown in the package.

1. The current raw dataset stores `program_name` and `university` separately and also preserves `raw_program_text`; the original helper expected one legacy key named `program`. `app.py` now combines the current program + university only for the LLM prompt while leaving every original field unchanged.
2. The assignment requires `llm_extend_applicant_data.json` as valid JSON. The original CLI writes JSONL. The adapted CLI defaults to a normal JSON array and retains optional `--format jsonl` behavior.
3. Identical program/university inputs are standardized once and cached, then reused across records. This reduces repeated model calls without changing the data semantics.
4. Optional `--workers` parallelizes unique LLM inputs. Each process loads its own model, so 1–2 workers is the recommended laptop starting point.
5. The Hugging Face model download call uses current supported arguments.
6. `requirements.txt` updates `llama-cpp-python` from the instructor's old `<0.3.0` constraint to a current 0.3.x release and points pip at the project's CPU wheel index. This is intended for the student's Python 3.13 Windows environment.

No applicant outcomes, dates, scores, comments, raw program text, or university values are overwritten. The LLM output is appended only in `llm-generated-program` and `llm-generated-university`.

## Final full-dataset validation

The adapted implementation was run against the final 30,011-row GradCafe
dataset using TinyLlama-1.1B-Chat-v1.0 Q4_K_M.

The final run processed 12,636 unique cached inputs. Real-data testing prompted
additional deterministic safeguards against semantic drift. These safeguards
preserve original fields, protect acronyms, recognize selected university
abbreviations/canonical names, require conservative semantic agreement for
model-generated changes, and otherwise fall back to the source value.

A strict post-processing pass rejected 2,111 questionable program candidates
and 990 questionable university candidates. Final validation found zero
missing generated fields, zero empty standardized values, and zero changes to
the original scraped fields.

Model weights and the local virtual environment are intentionally excluded from
Git.

