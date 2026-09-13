# -*- coding: utf-8 -*-
"""Local TinyLlama standardizer adapted for the current Module 2 dataset.

This file is based on the instructor-provided app.py. Local changes are kept
small and documented in LOCAL_CHANGES.md:
- accept the current scraper's program_name/university/raw_program_text fields;
- preserve all original fields;
- emit a valid JSON array for the required final deliverable;
- cache repeated program/university inputs;
- optionally parallelize unique LLM calls across a small worker pool;
- use current huggingface_hub download arguments.
"""
from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from flask import Flask, jsonify, request
from huggingface_hub import hf_hub_download
from llama_cpp import Llama

app = Flask(__name__)

MODEL_REPO = os.getenv("MODEL_REPO", "TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF")
MODEL_FILE = os.getenv("MODEL_FILE", "tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf")
N_THREADS = int(os.getenv("N_THREADS", str(os.cpu_count() or 2)))
N_CTX = int(os.getenv("N_CTX", "2048"))
N_GPU_LAYERS = int(os.getenv("N_GPU_LAYERS", "0"))

HERE = Path(__file__).resolve().parent
CANON_UNIS_PATH = Path(os.getenv("CANON_UNIS_PATH", str(HERE / "canon_universities.txt")))
CANON_PROGS_PATH = Path(os.getenv("CANON_PROGS_PATH", str(HERE / "canon_programs.txt")))
MODEL_DIR = Path(os.getenv("MODEL_DIR", str(HERE / "models")))

JSON_OBJ_RE = re.compile(r"\{.*?\}", re.DOTALL)


def _read_lines(path: str | Path) -> List[str]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return [ln.strip() for ln in f if ln.strip()]
    except FileNotFoundError:
        return []


CANON_UNIS = _read_lines(CANON_UNIS_PATH)
CANON_PROGS = _read_lines(CANON_PROGS_PATH)

ABBREV_UNI: Dict[str, str] = {
    r"(?i)^mcg(\.|ill)?$": "McGill University",
    r"(?i)^(ubc|u\.?b\.?c\.?)$": "University of British Columbia",
    r"(?i)^uoft$": "University of Toronto",
    r"(?i)^jhu$": "Johns Hopkins University",
}
COMMON_UNI_FIXES: Dict[str, str] = {
    "McGiill University": "McGill University",
    "Mcgill University": "McGill University",
    "John Hopkins University": "Johns Hopkins University",
    "University Of British Columbia": "University of British Columbia",
}
COMMON_PROG_FIXES: Dict[str, str] = {
    "Mathematic": "Mathematics",
    "Info Studies": "Information Studies",
}

SYSTEM_PROMPT = (
    "You are a data cleaning assistant. Standardize degree program and university names.\n\n"
    "Rules:\n"
    "- Input provides one string under key `program`; it may contain both a degree program and university.\n"
    "- Split it into (program name, university name).\n"
    "- Trim extra spaces and commas.\n"
    "- Expand obvious abbreviations.\n"
    "- Use Title Case for program; use official capitalization for university names.\n"
    "- Correct obvious spelling errors.\n"
    "- If a university cannot be inferred, return `Unknown`.\n\n"
    "Return JSON ONLY with keys standardized_program and standardized_university."
)
FEW_SHOTS: List[Tuple[Dict[str, str], Dict[str, str]]] = [
    ({"program": "Information Studies, McGill University"},
     {"standardized_program": "Information Studies", "standardized_university": "McGill University"}),
    ({"program": "Information, McG"},
     {"standardized_program": "Information Studies", "standardized_university": "McGill University"}),
    ({"program": "Mathematics, University Of British Columbia"},
     {"standardized_program": "Mathematics", "standardized_university": "University of British Columbia"}),
]

_LLM: Llama | None = None


def _load_llm() -> Llama:
    global _LLM
    if _LLM is not None:
        return _LLM
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    model_path = hf_hub_download(
        repo_id=MODEL_REPO,
        filename=MODEL_FILE,
        local_dir=str(MODEL_DIR),
    )
    _LLM = Llama(
        model_path=model_path,
        n_ctx=N_CTX,
        n_threads=N_THREADS,
        n_gpu_layers=N_GPU_LAYERS,
        verbose=False,
    )
    return _LLM


def _split_fallback(text: str) -> Tuple[str, str]:
    s = re.sub(r"\s+", " ", text or "").strip().strip(",")
    parts = [p.strip() for p in re.split(r",| at | @ ", s) if p.strip()]
    prog = parts[0] if parts else ""
    uni = parts[-1] if len(parts) > 1 else ""
    if re.fullmatch(r"(?i)mcg(ill)?(\.)?", uni or ""):
        uni = "McGill University"
    if re.fullmatch(r"(?i)(ubc|u\.?b\.?c\.?|university of british columbia)", uni or ""):
        uni = "University of British Columbia"
    prog = prog.title()
    uni = re.sub(r"\bOf\b", "of", uni.title()) if uni else "Unknown"
    return prog, uni


def _best_match(name: str, candidates: List[str], cutoff: float = 0.86) -> str | None:
    if not name or not candidates:
        return None
    matches = difflib.get_close_matches(name, candidates, n=1, cutoff=cutoff)
    return matches[0] if matches else None


def _post_normalize_program(prog: str) -> str:
    p = (prog or "").strip()
    p = COMMON_PROG_FIXES.get(p, p).title()
    if p in CANON_PROGS:
        return p
    return _best_match(p, CANON_PROGS, cutoff=0.84) or p


def _post_normalize_university(uni: str) -> str:
    u = (uni or "").strip()
    for pat, full in ABBREV_UNI.items():
        if re.fullmatch(pat, u):
            u = full
            break
    u = COMMON_UNI_FIXES.get(u, u)
    if u:
        u = re.sub(r"\bOf\b", "of", u.title())
    if u in CANON_UNIS:
        return u
    return _best_match(u, CANON_UNIS, cutoff=0.86) or u or "Unknown"



def _canon_exact(name: str, candidates: List[str]) -> str | None:
    """Return canonical spelling for an exact case-insensitive match."""
    target = (name or "").strip().casefold()
    if not target:
        return None
    for candidate in candidates:
        if candidate.strip().casefold() == target:
            return candidate
    return None


def _normalized_terms(text: str, drop_degrees: bool = False) -> List[str]:
    """Create conservative comparison terms for semantic-drift checks."""
    words = re.findall(r"[A-Za-z0-9]+", text or "")
    out: List[str] = []

    degree_words = {
        "phd", "ma", "ms", "mfa", "mba", "jd",
        "master", "masters", "doctoral", "doctorate"
    }

    for word in words:
        token = word.casefold()

        if drop_degrees and token in degree_words:
            continue

        # Very light normalization so Communications ~= Communication
        # and Sciences ~= Science without doing aggressive stemming.
        if len(token) > 4 and token.endswith("ies"):
            token = token[:-3] + "y"
        elif (
            len(token) > 4
            and token.endswith("s")
            and not token.endswith(("ss", "us", "is"))
        ):
            token = token[:-1]

        out.append(token)

    return out


def _polish_program_case(candidate: str, source: str) -> str:
    """Restore source acronyms and normal conjunction capitalization."""
    value = (candidate or "").strip()

    value = re.sub(
        r"\b(And|Of|In|For|To|At)\b",
        lambda m: m.group(1).lower(),
        value,
    )

    # Preserve acronyms that were present in the source: MFA, MS, MBA, etc.
    for acronym in re.findall(r"\b[A-Z][A-Z0-9&-]{1,}\b", source or ""):
        value = re.sub(
            rf"\b{re.escape(acronym)}\b",
            acronym,
            value,
            flags=re.IGNORECASE,
        )

    return value


def _safe_program_output(source: str, candidate: str) -> str:
    """Accept LLM program changes only when they remain close to the source."""
    source = (source or "").strip()
    candidate = _polish_program_case(candidate or "", source)

    if not source:
        return candidate
    if not candidate:
        return source

    source_terms = set(_normalized_terms(source, drop_degrees=True))
    candidate_terms = set(_normalized_terms(candidate, drop_degrees=True))

    if not source_terms or not candidate_terms:
        return source

    if source_terms == candidate_terms:
        return candidate

    # Only accept program changes that preserve the same normalized
    # semantic terms. This still allows harmless singularization/case cleanup
    # such as Communications -> Communication, while rejecting expansions,
    # dropped specializations, and model-added institutions.
    if source_terms == candidate_terms:
        return candidate

    return source


KNOWN_UNIVERSITY_ABBREVIATIONS: Dict[str, str] = {
    "MIT": "Massachusetts Institute of Technology",
    "JHU": "Johns Hopkins University",
    "UBC": "University of British Columbia",
    "UCLA": "University of California, Los Angeles",
    "UCSF": "University of California, San Francisco",
    "UCSD": "University of California, San Diego",
    "UCSC": "University of California, Santa Cruz",
    "UCI": "University of California, Irvine",
    "UCD": "University of California, Davis",
    "UCR": "University of California, Riverside",
    "UCSB": "University of California, Santa Barbara",
}


def _safe_university_output(source: str, candidate: str) -> str:
    """Prefer known/canonical universities and reject suspicious mutations."""
    source = (source or "").strip()
    candidate = (candidate or "").strip()

    if not source:
        return candidate or "Unknown"

    # Handle a trustworthy acronym supplied in parentheses.
    parenthetical = re.search(r"\(([^()]*)\)\s*$", source)
    if parenthetical:
        abbreviation = parenthetical.group(1).strip().upper()
        if abbreviation in KNOWN_UNIVERSITY_ABBREVIATIONS:
            target = KNOWN_UNIVERSITY_ABBREVIATIONS[abbreviation]
            return _canon_exact(target, CANON_UNIS) or target

    # Remove noisy trailing parenthetical material before comparison.
    base_source = re.sub(r"\s*\([^()]*\)\s*$", "", source).strip()

    # If the cleaned source itself is canonical, trust it.
    canonical_source = _canon_exact(base_source, CANON_UNIS)
    if canonical_source:
        return canonical_source

    canonical_raw = _canon_exact(source, CANON_UNIS)
    if canonical_raw:
        return canonical_raw

    canonical_candidate = _canon_exact(candidate, CANON_UNIS)
    candidate_value = canonical_candidate or candidate

    if not candidate_value:
        return base_source or source

    stopwords = {
        "the", "university", "college", "of", "at", "and",
        "institute", "technology", "school"
    }

    source_terms = {
        t for t in _normalized_terms(base_source)
        if t not in stopwords
    }
    candidate_terms = {
        t for t in _normalized_terms(candidate_value)
        if t not in stopwords
    }

    if source_terms and candidate_terms:
        # Generic institution words such as University/College are removed
        # above. Require the remaining identifying terms to agree exactly.
        # Thus Yale -> Yale University is allowed, while
        # Yale -> Philadelphia, Yale is rejected.
        if source_terms == candidate_terms:
            return candidate_value

    # If the model mutation is questionable, preserve the cleaned source.
    return base_source or source

def _program_text_from_row(row: Dict[str, Any]) -> str:
    """Build one LLM input while preserving the original row unchanged.

    The current GradCafe layout puts program and university in separate cells,
    unlike the older sample where both were mixed in a single `program` field.
    We therefore combine the parsed program + university for the model.
    """
    program_name = str(row.get("program_name") or "").strip()
    university = str(row.get("university") or "").strip()
    if program_name or university:
        return ", ".join(x for x in (program_name, university) if x)
    legacy = str(row.get("program") or "").strip()
    if legacy:
        return legacy
    return str(row.get("raw_program_text") or "").strip()


def _call_llm(program_text: str) -> Dict[str, str]:
    if not program_text.strip():
        return {"standardized_program": "", "standardized_university": "Unknown"}
    llm = _load_llm()
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for x_in, x_out in FEW_SHOTS:
        messages.append({"role": "user", "content": json.dumps(x_in, ensure_ascii=False)})
        messages.append({"role": "assistant", "content": json.dumps(x_out, ensure_ascii=False)})
    messages.append({"role": "user", "content": json.dumps({"program": program_text}, ensure_ascii=False)})
    out = llm.create_chat_completion(messages=messages, temperature=0.0, max_tokens=96, top_p=1.0)
    text = (out["choices"][0]["message"]["content"] or "").strip()
    try:
        match = JSON_OBJ_RE.search(text)
        obj = json.loads(match.group(0) if match else text)
        std_prog = str(obj.get("standardized_program", "")).strip()
        std_uni = str(obj.get("standardized_university", "")).strip()
    except Exception:
        std_prog, std_uni = _split_fallback(program_text)
    return {
        "standardized_program": _post_normalize_program(std_prog),
        "standardized_university": _post_normalize_university(std_uni),
    }


def _standardize_one_text(text: str) -> Tuple[str, Dict[str, str]]:
    return text, _call_llm(text)


def standardize_rows(rows: Iterable[Dict[str, Any]], workers: int = 1) -> List[Dict[str, Any]]:
    """Standardize rows, caching repeated program/university inputs.

    Parallelism is applied to *unique* inputs. Each worker loads its own model,
    so keep workers small (typically 2 on a normal laptop) to avoid excess RAM.
    """
    rows_list = [dict(r) for r in rows]
    texts = [_program_text_from_row(r) for r in rows_list]
    unique_texts = list(dict.fromkeys(texts))
    print(f"Rows: {len(rows_list):,}; unique LLM inputs: {len(unique_texts):,}", file=sys.stderr)

    results: Dict[str, Dict[str, str]] = {}
    workers = max(1, int(workers))
    if workers == 1:
        for i, text in enumerate(unique_texts, 1):
            _, result = _standardize_one_text(text)
            results[text] = result
            if i % 100 == 0 or i == len(unique_texts):
                print(f"Standardized {i:,}/{len(unique_texts):,} unique inputs", file=sys.stderr)
    else:
        # Avoid giving every process all CPU threads.
        os.environ["N_THREADS"] = str(max(1, (os.cpu_count() or 2) // workers))
        with ProcessPoolExecutor(max_workers=workers) as pool:
            for i, (text, result) in enumerate(pool.map(_standardize_one_text, unique_texts, chunksize=1), 1):
                results[text] = result
                if i % 100 == 0 or i == len(unique_texts):
                    print(f"Standardized {i:,}/{len(unique_texts):,} unique inputs", file=sys.stderr)

    out: List[Dict[str, Any]] = []
    for row, text in zip(rows_list, texts):
        result = results[text]
        source_program = str(row.get("program_name") or "").strip()
        source_university = str(row.get("university") or "").strip()

        row["llm-generated-program"] = _safe_program_output(
            source_program,
            result["standardized_program"],
        )
        row["llm-generated-university"] = _safe_university_output(
            source_university,
            result["standardized_university"],
        )
        out.append(row)
    return out


def _normalize_input(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("rows"), list):
        return payload["rows"]
    return []


@app.get("/")
def health() -> Any:
    return jsonify({"ok": True})


@app.post("/standardize")
def standardize() -> Any:
    payload = request.get_json(force=True, silent=True)
    rows = _normalize_input(payload)
    return jsonify({"rows": standardize_rows(rows, workers=1)})


def _write_rows(rows: List[Dict[str, Any]], out_path: str | None, to_stdout: bool, fmt: str) -> None:
    sink = sys.stdout if to_stdout else open(out_path or "out.json", "w", encoding="utf-8")
    try:
        if fmt == "jsonl":
            for row in rows:
                json.dump(row, sink, ensure_ascii=False)
                sink.write("\n")
        else:
            json.dump(rows, sink, indent=2, ensure_ascii=False)
            sink.write("\n")
    finally:
        if sink is not sys.stdout:
            sink.close()


def _cli_process_file(in_path: str, out_path: str | None, to_stdout: bool, fmt: str, workers: int) -> None:
    with open(in_path, "r", encoding="utf-8") as f:
        rows = _normalize_input(json.load(f))
    out_rows = standardize_rows(rows, workers=workers)
    _write_rows(out_rows, out_path, to_stdout, fmt)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Standardize program/university with a tiny local LLM.")
    parser.add_argument("--file", default=None, help="Path to JSON input")
    parser.add_argument("--serve", action="store_true", help="Run Flask server")
    parser.add_argument("--out", default=None, help="Output path")
    parser.add_argument("--stdout", action="store_true", help="Write output to stdout")
    parser.add_argument("--format", choices=("json", "jsonl"), default="json")
    parser.add_argument("--workers", type=int, default=1, help="Parallel model workers; start with 1 or 2")
    args = parser.parse_args()

    if args.serve or args.file is None:
        port = int(os.getenv("PORT", "8000"))
        app.run(host="0.0.0.0", port=port, debug=False)
    else:
        _cli_process_file(args.file, args.out, args.stdout, args.format, args.workers)
