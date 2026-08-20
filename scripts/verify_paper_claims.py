#!/usr/bin/env python3
"""Verify PAPER.md's quantitative claim ledger and immutable evidence bindings."""
from __future__ import annotations
import hashlib,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def sha(path:Path)->str:return hashlib.sha256(path.read_bytes()).hexdigest()
def pointer(value,raw:str):
    for part in raw.lstrip('/').split('/') if raw else []:
        part=part.replace('~1','/').replace('~0','~')
        value=value[int(part)] if isinstance(value,list) else value[part]
    return value

def verify_claims(ledger:dict,paper:str,root:Path=ROOT)->dict:
    claims=ledger['claims']; ids=[row['id'] for row in claims]
    if len(ids)!=len(set(ids)):raise SystemExit('duplicate claim IDs')
    for row in claims:
        marker=f"[{row['id']}]"
        if marker not in paper:raise SystemExit(f'claim absent from PAPER.md: {marker}')
        for selector in row.get('paper_selectors',[]):
            if paper.count(selector)!=1:raise SystemExit(f"paper selector drift {row['id']}:{selector!r}")
        if row['status'] not in {'valid','exploratory','technical-invalid','unsupported','development-prescore'}:raise SystemExit(f"bad status {row['id']}")
        for ev in row['evidence']:
            path=root/ev['path']
            if not path.is_file() or sha(path)!=ev['sha256']:raise SystemExit(f"evidence drift {row['id']}:{path}")
            if 'pointer' in ev:
                observed=pointer(json.loads(path.read_text()),ev['pointer'])
                if observed!=ev['expected']:raise SystemExit(f"pointer drift {row['id']}:{ev['pointer']} got={observed!r}")
            if 'selector' in ev and path.read_text().count(ev['selector'])!=1:raise SystemExit(f"selector drift {row['id']}:{path}")
    known=set(ids)
    for marker in re.findall(r'\[(C\d{3})\]',paper):
        if marker not in known:raise SystemExit(f'unknown PAPER marker {marker}')
    in_fence=False
    for number,line in enumerate(paper.splitlines(),1):
        if line.startswith('```'):in_fence=not in_fence;continue
        if in_fence or line.startswith('#') or line.startswith('>') or line.startswith('<!--') or not line.strip():continue
        if re.search(r'(?<![A-Za-z])(?:\d+\.\d+|\d+/\d+|\d+%|rank-\d+)',line,re.I) and not re.search(r'\[C\d{3}\]',line):
            raise SystemExit(f'quantitative line lacks claim marker at PAPER.md:{number}: {line}')
    return {'status':'PASS','claims':len(claims),'evidence_bindings':sum(len(x['evidence']) for x in claims),'paper_selectors':sum(len(x.get('paper_selectors',[])) for x in claims)}

def main()->None:
    ledger=json.loads((ROOT/'reports/paper_claim_ledger_v1.json').read_text()); paper=(ROOT/'PAPER.md').read_text()
    print(json.dumps(verify_claims(ledger,paper),sort_keys=True))
if __name__=='__main__':main()
