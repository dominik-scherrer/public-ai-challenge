"""Build helpers: municipality builders (baseline/<m>/build.py) declare sources + services compactly.
Quote checking: every evidence quote starts 'not_checked'. `python3 build.py quotes` prints {url:[quotes]} for
browser __verify. The verify result is stored in quote_checks.json {"checked_at", "results":{url:{quote:bool}}};
only quotes with a True result become quote_check='exact'."""
import json, pathlib, sys, re
class B:
    def __init__(s, d, canton, muni, slug, pub=None):
        s.d = pathlib.Path(d); s.canton, s.muni, s.slug = canton, muni, slug; s.muni_pub = pub or muni
        s.sources, s.services, s.n = {}, [], 0
        qf = s.d/'quote_checks.json'
        s.qc = json.load(open(qf, encoding='utf-8')) if qf.exists() else {'results': {}}
    def src(s, key, url, title, cap=None, **kw):
        """cap: dict returned by __cap (subset ok). kw overrides."""
        s.n += 1; cap = cap or {}
        r = {'source_id': f'src_{s.slug}_{s.n:03d}', 'classification': kw.pop('classification','official'),
             'source_type': kw.pop('source_type','municipality_website'),
             'publisher': kw.pop('publisher', {'name': s.muni_pub, 'authority_level':'municipality', 'department': None}),
             'url': url, 'final_url': cap.get('final_url'), 'canonical_url': cap.get('canonical'),
             'hreflang': cap.get('hreflang', []), 'retrieved_at': cap.get('retrieved_at') or kw.pop('retrieved_at'),
             'http_status': cap.get('http_status'), 'source_modified_at': None, 'source_modified_basis': None,
             'last_modified': cap.get('last_modified'), 'etag': cap.get('etag'), 'content_hash': cap.get('content_hash'),
             'capture_method': kw.pop('capture_method','browser_sameorigin_refetch'),
             'snapshot_quality': kw.pop('snapshot_quality','raw_hash_text'),
             'content_type': cap.get('content_type') or kw.pop('content_type','text/html'),
             'language': kw.pop('language','de'), 'html_lang': cap.get('html_lang'), 'title': title,
             'page_role': kw.pop('page_role','service_page'), 'notes': kw.pop('notes', None)}
        if r['last_modified'] and not kw.get('source_modified_at'):
            r['source_modified_at'], r['source_modified_basis'] = r['last_modified'], 'http_last_modified'
        r.update(kw); s.sources[key] = r; return key
    def _ev(s, key, text):
        url = s.sources[key]['url']
        ok = s.qc['results'].get(url, {}).get(text)
        return {'source_ref': s.sources[key]['source_id'], 'text': text, 'quote_check': 'exact' if ok else 'not_checked'}
    def P(s, cls, *pairs, derived_from=None, method=None, note=None):
        """pairs: (srckey, quote) tuples or bare srckey (ref without quote)."""
        refs, evs = [], []
        for p in pairs:
            k, q = (p if isinstance(p, tuple) else (p, None))
            sid = s.sources[k]['source_id']
            if sid not in refs: refs.append(sid)
            if q: evs.append(s._ev(k, q))
        d = {'classification': cls, 'source_refs': refs, 'evidence': evs}
        if derived_from: d['derived_from'] = derived_from
        if method: d['method'] = method
        if note: d['note'] = note
        return d
    def svc(s, sid, concept, labels, prov, status='verified', **f):
        lab = {'de':None,'fr':None,'it':None,'rm':None}; lab.update(labels)
        rec = {'service_id': f'ch.{s.canton.lower()}.{s.slug}.{sid}', 'concept': concept, 'labels': lab,
               'description': f.pop('description', None), 'audience': f.pop('audience', ['residents']),
               'provider': f.pop('provider'), 'jurisdiction': {'country':'CH','canton':s.canton,'municipality':s.muni},
               'eligibility': f.pop('eligibility', []), 'requirements': f.pop('requirements', []),
               'documents': f.pop('documents', []), 'fees': f.pop('fees', []),
               'processing_time': f.pop('processing_time', None),
               'channels': {**{'online':None,'in_person':None,'postal':None,'telephone':None,'email':None}, **f.pop('channels', {})},
               'actions': f.pop('actions', []), 'contacts': f.pop('contacts', []),
               'source_refs': [], 'field_provenance': prov, 'conflicts': f.pop('conflicts', []),
               'trust': {'authority': f.pop('authority','high'), 'directness': f.pop('directness','primary'),
                         'freshness': f.pop('freshness','unknown'), 'freshness_basis': f.pop('freshness_basis', None),
                         'evidence_coverage': 0.0, 'conflicts': []},
               'judgement_notes': [{'kind':k,'text':t} for k,t in f.pop('notes', [])], 'status': status}
        assert not f, f'unknown fields {f}'
        rec['trust']['conflicts'] = rec['conflicts']
        refs = []
        for p in prov.values():
            for r in p['source_refs']:
                if r not in refs: refs.append(r)
        rec['source_refs'] = refs; s.services.append(rec)
    def write(s):
        if len(sys.argv) > 1 and sys.argv[1] == 'quotes':
            out = {}
            for r in s.services:
                for p in r['field_provenance'].values():
                    for e in p['evidence']:
                        url = next(x['url'] for x in s.sources.values() if x['source_id']==e['source_ref'])
                        out.setdefault(url, [])
                        if e['text'] not in out[url]: out[url].append(e['text'])
            print(json.dumps(out, ensure_ascii=False)); return
        with open(s.d/'sources.jsonl','w',encoding='utf-8') as f:
            for r in s.sources.values(): f.write(json.dumps(r, ensure_ascii=False)+'\n')
        with open(s.d/'services.jsonl','w',encoding='utf-8') as f:
            for r in s.services: f.write(json.dumps(r, ensure_ascii=False)+'\n')
        print(f'wrote {len(s.sources)} sources, {len(s.services)} services')
