from __future__ import annotations
import argparse, json
from pathlib import Path

parser=argparse.ArgumentParser()
parser.add_argument('raw', nargs='?', default='applicant_data.json')
parser.add_argument('cleaned', nargs='?', default='llm_extend_applicant_data.json')
args=parser.parse_args()

raw=json.loads(Path(args.raw).read_text(encoding='utf-8'))
cleaned=json.loads(Path(args.cleaned).read_text(encoding='utf-8'))
assert isinstance(raw,list) and isinstance(cleaned,list)
print(f'raw rows: {len(raw):,}')
print(f'cleaned rows: {len(cleaned):,}')
print('row count match:', len(raw)==len(cleaned))
need=('llm-generated-program','llm-generated-university')
missing=sum(1 for r in cleaned if any(k not in r for k in need))
empty_program=sum(1 for r in cleaned if not r.get('llm-generated-program'))
unknown_uni=sum(1 for r in cleaned if r.get('llm-generated-university') in (None,'','Unknown'))
print('rows missing LLM keys:', missing)
print('empty standardized program:', empty_program)
print('unknown/empty standardized university:', unknown_uni)
# Traceability: every cleaned row should retain at least one original program representation.
trace_missing=sum(1 for r in cleaned if not any(k in r for k in ('raw_program_text','program','program_name')))
print('rows missing original program trace field:', trace_missing)
if len(raw)!=len(cleaned) or missing or trace_missing:
    raise SystemExit(1)
