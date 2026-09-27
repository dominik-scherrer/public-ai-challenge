#!/usr/bin/env python3
"""Deterministic finalizer/validator for one municipality dir (or all under baseline/).
- validates JSON against schemas
- checks every source_ref resolves; discovery-only sources never used as evidence
- checks every populated field path has field_provenance
- recomputes trust.evidence_coverage and writes it back (services.jsonl rewritten in place)
Usage: finalize.py <baseline/muni> [...]   (exit 1 on errors)"""
import json, sys, pathlib, re
import jsonschema
ROOT = pathlib.Path(__file__).resolve().parent.parent
S = {n: json.load(open(ROOT/'schemas'/f'{n}.schema.json')) for n in ['service','source','municipality','crawl-report']}

def populated_paths(s):
    p = []
    for k, v in s['labels'].items():
        if k != 'alt' and v: p.append(f'labels.{k}')
    if s.get('description'): p.append('description')
    for k in ('name', 'department'):
        if s['provider'].get(k): p.append(f'provider.{k}')
    for arr in ('eligibility', 'requirements', 'documents', 'actions', 'contacts'):
        p += [f'{arr}[{i}]' for i in range(len(s[arr]))]
    for i, f in enumerate(s['fees']):
        p.append(f'fees[{i}].raw_text')
        if f.get('amount') is not None: p.append(f'fees[{i}].amount')
    if s.get('processing_time'): p.append('processing_time')
    p += [f'channels.{k}' for k, v in s['channels'].items() if v is not None]
    return p

def run(d):
    d = pathlib.Path(d); errs, warns = [], []
    def load_jsonl(f):
        out = []
        for i, line in enumerate(open(d/f, encoding='utf-8'), 1):
            if line.strip():
                try: out.append(json.loads(line))
                except Exception as e: errs.append(f'{f}:{i} bad json {e}')
        return out
    srcs = load_jsonl('sources.jsonl'); svcs = load_jsonl('services.jsonl')
    for n, f in (('municipality', 'municipality.json'), ('crawl-report', 'crawl-report.json')):
        try: jsonschema.validate(json.load(open(d/f, encoding='utf-8')), S[n])
        except Exception as e: errs.append(f'{f}: {str(e).splitlines()[0]}')
    sid = {}
    for s in srcs:
        try: jsonschema.validate(s, S['source'])
        except jsonschema.ValidationError as e: errs.append(f"source {s.get('source_id')}: {e.message} @ {list(e.path)}")
        if s.get('source_id') in sid: errs.append(f"dup source {s['source_id']}")
        sid[s.get('source_id')] = s
    ids = set(); stats = {'verified': 0, 'partial': 0, 'candidate': 0}; cov = []
    for s in svcs:
        tag = s.get('service_id')
        try: jsonschema.validate(s, S['service'])
        except jsonschema.ValidationError as e: errs.append(f'service {tag}: {e.message} @ {list(e.path)}'); continue
        if tag in ids: errs.append(f'dup service {tag}')
        ids.add(tag); stats[s['status']] += 1
        for r in s['source_refs']:
            if r not in sid: errs.append(f'{tag}: unknown source_ref {r}')
        fp = s['field_provenance']; paths = populated_paths(s); covered = 0
        for p in paths:
            if p not in fp: errs.append(f'{tag}: populated field {p} has no provenance'); continue
            e = fp[p]
            for r in e['source_refs']:
                if r not in sid: errs.append(f'{tag}.{p}: unknown source_ref {r}')
            for ev in e['evidence']:
                src = sid.get(ev['source_ref'])
                if src and src['snapshot_quality'] == 'discovery_summary_only':
                    errs.append(f'{tag}.{p}: evidence cites discovery-only source {ev["source_ref"]}')
            if e['classification'] == 'derived' and not e.get('derived_from'):
                errs.append(f'{tag}.{p}: derived without derived_from')
        def has_ev(p, depth=0):
            e = fp.get(p)
            if not e or depth > 3: return False
            if any(ev['quote_check'] != 'not_checked' for ev in e['evidence']): return True
            return e['classification'] == 'derived' and has_ev(e.get('derived_from') or '', depth+1)
        for p in paths:
            if has_ev(p): covered += 1
        c = round(covered/len(paths), 2) if paths else 0.0
        s['trust']['evidence_coverage'] = c; cov.append(c)
        if s['status'] == 'verified' and c < 0.5: warns.append(f'{tag}: verified but coverage {c}')
        stray = [k for k in fp if k not in paths]
        if stray: warns.append(f'{tag}: provenance for unpopulated paths {stray}')
    if not errs:
        with open(d/'services.jsonl', 'w', encoding='utf-8') as f:
            for s in svcs: f.write(json.dumps(s, ensure_ascii=False)+'\n')
    rep = {'dir': d.name, 'sources': len(srcs), 'services': len(svcs), 'by_status': stats,
           'mean_evidence_coverage': round(sum(cov)/len(cov), 2) if cov else None,
           'errors': errs, 'warnings': warns}
    print(json.dumps(rep, ensure_ascii=False, indent=1)); return not errs

if __name__ == '__main__':
    ok = all([run(a) for a in sys.argv[1:]]); sys.exit(0 if ok else 1)
