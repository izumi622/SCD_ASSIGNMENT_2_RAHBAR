#!/usr/bin/env python3
"""RAHBAR controlled semantic-cache threshold probe.

On the Windows host, copies itself to a running API pod, runs there using the
actual app.services.cache.SemanticCache class, and writes measured evidence.

Only creates short-lived Redis cache keys in unique probe namespaces. It does
not modify production cache thresholds, deployments, Chroma collections, or source data.
"""
from __future__ import annotations
import json
import os
import subprocess
import sys
from pathlib import Path

PAIRS = [
    {
        'id':'P01', 'topic':'summer versus regular course limits',
        'a':'Under current FAST-NUCES rules, what is the maximum number of courses in a summer semester?',
        'a_answer':'Two courses.',
        'b':'Under current FAST-NUCES rules, what is the maximum number of courses in a regular semester?',
        'b_answer':'Five courses normally.',
        'citation_page':9,
    },
    {
        'id':'P02', 'topic':'summer versus regular course limits, alternate phrasing',
        'a':'How many courses may a FAST-NUCES student register for during a summer semester?',
        'a_answer':'Two courses.',
        'b':'How many courses may a FAST-NUCES student register for during a regular semester?',
        'b_answer':'Five courses normally.',
        'citation_page':9,
    },
    {
        'id':'P03', 'topic':'required attendance versus condonable absence',
        'a':'Under FAST-NUCES rules, what percentage attendance is required in lectures and labs?',
        'a_answer':'100% attendance required.',
        'b':'Under FAST-NUCES rules, what percentage absence may be condoned for genuine reasons?',
        'b_answer':'Up to 20% absence may be condoned.',
        'citation_page':10,
    },
    {
        'id':'P04', 'topic':'attendance versus exception, close phrasing',
        'a':'What is the FAST-NUCES attendance percentage requirement for a course?',
        'a_answer':'100% attendance required.',
        'b':'What is the FAST-NUCES absence percentage that can be condoned for a course?',
        'b_answer':'Up to 20% absence may be condoned.',
        'citation_page':10,
    },
    {
        'id':'P05', 'topic':'semester freeze versus summer courses',
        'a':'Under FAST-NUCES rules, how many semesters may a student freeze?',
        'a_answer':'Two semesters.',
        'b':'Under FAST-NUCES rules, how many courses may a student take in summer?',
        'b_answer':'Two courses, not semesters.',
        'citation_page':22,
    },
    {
        'id':'P06', 'topic':'current withdrawal versus extra course rule',
        'a':'According to current June 2026 FAST-NUCES Rule 4.25, when is the course withdrawal deadline?',
        'a_answer':'Last day of the makeup week.',
        'b':'According to current June 2026 FAST-NUCES Rule 4.3, who may register for an extra regular-semester course?',
        'b_answer':'Eligible final-year students.',
        'citation_page':23,
    },
    {
        'id':'P07', 'topic':'minimum CGPA versus attendance minimum',
        'a':'What is the minimum CGPA required for bachelor graduation under FAST-NUCES rules?',
        'a_answer':'2.00 CGPA.',
        'b':'What is the minimum attendance percentage required for lectures under FAST-NUCES rules?',
        'b_answer':'100% attendance.',
        'citation_page':10,
    },
    {
        'id':'P08', 'topic':'academic warning versus withdrawal',
        'a':'Under June 2026 FAST-NUCES academic rules, what minimum CGPA avoids academic warning?',
        'a_answer':'2.00 CGPA.',
        'b':'Under June 2026 FAST-NUCES academic rules, what is the deadline to withdraw from a course?',
        'b_answer':'Last day of makeup week.',
        'citation_page':24,
    },
    {
        'id':'P09', 'topic':'maximum summer courses versus maximum freeze semesters',
        'a':'What is the maximum number of courses allowed in summer at FAST-NUCES?',
        'a_answer':'Two summer courses.',
        'b':'What is the maximum number of semesters a student may freeze at FAST-NUCES?',
        'b_answer':'Two semesters.',
        'citation_page':9,
    },
    {
        'id':'P10', 'topic':'regular maximum versus final-year exception',
        'a':'Under current FAST-NUCES rules, what is the regular-semester course limit for most students?',
        'a_answer':'Five courses normally.',
        'b':'Under current FAST-NUCES rules, who is eligible for a sixth regular-semester course?',
        'b_answer':'Final-year students.',
        'citation_page':19,
    },
]
THRESHOLDS = [0.85, 0.90, 0.95]


def pod_main():
    import uuid
    import httpx
    from dataclasses import replace
    from app.config import get_settings
    from app.schemas import AskResponse, Citation
    from app.services.cache import SemanticCache, _cosine

    settings = get_settings()
    texts = [t for pair in PAIRS for t in (pair['a'], pair['b'])]
    with httpx.Client(timeout=httpx.Timeout(180.0, connect=10.0)) as client:
        resp = client.post(settings.ollama_url.rstrip('/')+'/api/embed',
                           json={'model':settings.embed_model,'input':texts})
        resp.raise_for_status()
        embeddings = resp.json()['embeddings']
    assert len(embeddings) == len(texts)

    outcomes = []
    for i, pair in enumerate(PAIRS):
        a, b = embeddings[2*i], embeddings[2*i+1]
        score = _cosine(a, b)
        hits = {}
        for threshold in THRESHOLDS:
            probe = uuid.uuid4().hex
            # This suffix is used by the real SemanticCache constructor, separating
            # the probe from all existing production cache keys and other probes.
            os.environ['RAHBAR_RETRIEVAL_REV'] = 'threshold-probe-'+probe
            cache = SemanticCache(replace(settings,cache_threshold=threshold))
            try:
                # This is an intentional *control fixture*, not an LLM result.
                # The real cache.store()/lookup() and Redis serialization are used.
                seeded = AskResponse(
                    request_id='controlled-threshold-probe', answer=pair['a_answer'],
                    citations=[Citation(source='academic-rules-handbook-jun-2026.pdf',
                                        section='Unheaded section',page=pair['citation_page'])],
                    answered_from_context=True, confidence='high',retrieved=[],
                    provider='controlled-probe',cached=False)
                cache.vec = a
                cache.store(pair['a'], seeded)
                cache.vec = b
                got = cache.lookup(pair['b'])
                hits[f'{threshold:.2f}'] = got is not None and got.answer == seeded.answer
            finally:
                # Remove *only* our isolated probe keys. Production keys untouched.
                keys=list(cache.conn.scan_iter(match=f'rahbar:cache:{cache.revision}:*'))
                if keys: cache.conn.delete(*keys)
                cache.close()
        outcomes.append({**{k:pair[k] for k in ('id','topic','a','a_answer','b','b_answer')},
                         'cosine_similarity': round(score,6),
                         'false_hit_by_threshold': hits})
    totals = {f'{t:.2f}':sum(p['false_hit_by_threshold'][f'{t:.2f}'] for p in outcomes)
              for t in THRESHOLDS}
    safe = [t for t in THRESHOLDS if totals[f'{t:.2f}'] == 0]
    print(json.dumps({'method':'Isolated Redis cache-store/lookup probe using production '
                               'SemanticCache, real Ollama vectors and a controlled cached '
                               'response fixture; not end-to-end API requests.',
                      'embedding_model':settings.embed_model,
                      'probe_count':len(PAIRS),
                      'thresholds':THRESHOLDS,'false_hit_counts':totals,
                      'lowest_zero_false_hit_threshold_in_test_set':min(safe) if safe else None,
                      'cases':outcomes},indent=2))


def cmd(*args, timeout=180):
    program = ['minikube', 'kubectl', '--', *args]
    return subprocess.run(program,check=True,text=True,capture_output=True,timeout=timeout)


def host_main():
    project = Path.cwd()
    if not (project/'api'/'app'/'services'/'cache.py').is_file():
        sys.exit('ERROR: Run this script from the rahbar-starter project root.')
    print('Locating a running RAHBAR API pod...',flush=True)
    found = json.loads(cmd('get','pods','-n','rahbar','-o','json').stdout)
    names = [p['metadata']['name'] for p in found['items']
             if p['metadata']['name'].startswith('api-')
             and p.get('status',{}).get('phase') == 'Running']
    if not names: sys.exit('ERROR: No running API pod found in rahbar namespace.')
    pod = names[0]
    localfile=Path(__file__).resolve()
    remotefile='/tmp/rahbar_cache_threshold_experiment.py'
    print('Copying probe to '+pod+' (production deployments unchanged)...',flush=True)
    cmd('cp',str(localfile),f'rahbar/{pod}:{remotefile}',timeout=120)
    print('Embedding '+str(2*len(PAIRS))+' questions and testing 3 thresholds...',flush=True)
    result=cmd('exec','-n','rahbar',pod,'--','python',remotefile,'--inside-pod',timeout=360)
    data=json.loads(result.stdout)
    docs=project/'docs'; docs.mkdir(exist_ok=True)
    output_json=docs/'cache-threshold-experiment.json'
    output_md=docs/'CACHE-THRESHOLD-EXPERIMENT.md'
    output_json.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
    lines=['# Controlled semantic-cache threshold experiment','',
           '**Method:** '+data['method'],'',
           f"Embedding model: `{data['embedding_model']}`. "
           f"{data['probe_count']} deliberately non-equivalent question pairs.",
           'Every pair used a separate temporary Redis revision. '
           'After each test the probe keys were deleted; the production cache was not changed.','',
           '| Threshold | Observed false hits |', '|---:|---:|']
    for t in THRESHOLDS:
        key=f'{t:.2f}'
        lines.append(f"| {key} | {data['false_hit_counts'][key]}/{data['probe_count']} |")
    lines.extend(['','**Lowest threshold with zero observed false hits in these probes:** '+
                  (str(data['lowest_zero_false_hit_threshold_in_test_set'])
                   if data['lowest_zero_false_hit_threshold_in_test_set'] is not None
                   else 'none of the three tested thresholds'),'',
                  '## Per-pair evidence','',
                  '| Pair | Scenario | Cosine similarity | 0.85 | 0.90 | 0.95 |',
                  '|---|---|---:|---|---|---|'])
    for p in data['cases']:
        flags=['FALSE HIT' if p['false_hit_by_threshold'][f'{t:.2f}'] else 'miss'
               for t in THRESHOLDS]
        lines.append(f"| {p['id']} | {p['topic']} | {p['cosine_similarity']:.4f} | " +
                     ' | '.join(flags) + ' |')
    lines.extend(['','## Exact prompts and controlled answers',''])
    for p in data['cases']:
        lines.extend([f"### {p['id']} — {p['topic']}",
                     f"- Cached question A: {p['a']}",
                     f"- Controlled cached answer A: {p['a_answer']}",
                     f"- Incoming question B: {p['b']}",
                     f"- Distinct expected answer B: {p['b_answer']}",
                     f"- Similarity: {p['cosine_similarity']:.6f}",''])
    lines.extend(['## Limits and interpretation','',
                  'These are observed real semantic-cache `store` and `lookup` results '
                  'on controlled fixtures with live Redis and real `nomic-embed-text` '
                  'question embeddings. This is **not** an end-to-end RAG answer '
                  'accuracy or latency test, nor a statistically representative '
                  'estimate of real-world false-hit rates. The fixtures were injected '
                  'directly into an isolated namespace; the normal grounded-answer '
                  'eligibility guard was not exercised. A zero-false-hit threshold '
                  'is only safe on these tested pairs, not a universal guarantee.',''])
    output_md.write_text('\n'.join(lines),encoding='utf-8')
    print('\nOBSERVED false hits by threshold:',data['false_hit_counts'])
    print('Lowest zero-false-hit threshold on test pairs:',
          data['lowest_zero_false_hit_threshold_in_test_set'])
    print('SAVED',output_md)
    print('SAVED',output_json)


if __name__=='__main__':
    try:
        if '--inside-pod' in sys.argv: pod_main()
        else: host_main()
    except subprocess.CalledProcessError as e:
        print('COMMAND FAILED:',e.cmd, file=sys.stderr)
        print((e.stderr or '')[-4000:],file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(type(e).__name__+': '+str(e),file=sys.stderr)
        raise
