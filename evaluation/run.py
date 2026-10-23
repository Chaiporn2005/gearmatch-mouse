"""python -m evaluation.run -- no model or network required."""
import hashlib
import json
import platform
from pathlib import Path
from app.models import Filters
from app.retrieval import Index, matches

ROOT=Path(__file__).resolve().parents[1]


def score(rows, strategy, index, k=3):
    result=[]
    for case in rows:
        filters=Filters.model_validate(case['filters'])
        hits=index.search(case['query'],filters,k=k,strategy=strategy)
        ids=[x['product']['id'] for x in hits]
        relevant=set(case['relevant'])
        rr=next((1/(i+1) for i,x in enumerate(ids) if x in relevant),0.0)
        result.append({'id':case['id'],'split':case['split'],'query':case['query'],'expected':case['relevant'],'retrieved':ids,
                       'recall_at_3':len(relevant&set(ids))/len(relevant) if relevant else None,
                       'reciprocal_rank':rr if relevant else None,
                       'constraint_violations':sum(not matches(x['product'],filters) for x in hits),
                       'abstention_correct':not bool(ids) if not relevant else None})
    return result


def aggregate(rows):
    answerable=[r for r in rows if r['recall_at_3'] is not None]
    unanswerable=[r for r in rows if r['abstention_correct'] is not None]
    return {'n':len(rows),'answerable_n':len(answerable),'unanswerable_n':len(unanswerable),
            'recall_at_3':sum(r['recall_at_3'] for r in answerable)/max(len(answerable),1),
            'mrr_at_3':sum(r['reciprocal_rank'] for r in answerable)/max(len(answerable),1),
            'constraint_violations':sum(r['constraint_violations'] for r in rows),
            'abstention_accuracy':sum(r['abstention_correct'] for r in unanswerable)/max(len(unanswerable),1)}


def main():
    data=(ROOT/'evaluation/gold.json').read_bytes();gold=json.loads(data);index=Index()
    out={'dataset_sha256':hashlib.sha256(data).hexdigest(),'catalog_sha256':hashlib.sha256((ROOT/'data/catalog.json').read_bytes()).hexdigest(),'python':platform.python_version(),
         'protocol':'Author-curated 20 dev / 10 held-out examples. No tuning on held-out labels. Corpus-sized lexical-vector evaluation, not LLM answer quality. Baseline intentionally ignores metadata filters; filtered BM25 isolates this factor. No claim of statistical significance.', 'systems':{}}
    for strategy in ['bm25','filtered_bm25','hybrid']:
        rows=score(gold,strategy,index)
        out['systems'][strategy]={'all':aggregate(rows),'dev':aggregate([r for r in rows if r['split']=='dev']),'test':aggregate([r for r in rows if r['split']=='test']),'cases':rows}
    (ROOT/'evaluation/results.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    lines=['# Retrieval evaluation results','','These are real offline retrieval measurements, not LLM answer scores.','', '| System | Split | Recall@3 | MRR@3 | Constraint violations | Empty-answer accuracy |','|---|---|---:|---:|---:|---:|']
    for name, system in out['systems'].items():
        for split in ['dev','test','all']:
            r=system[split];lines.append(f"| {name} | {split} | {r['recall_at_3']:.3f} | {r['mrr_at_3']:.3f} | {r['constraint_violations']} | {r['abstention_accuracy']:.3f} |")
    lines += ['', '## Interpretation and limits','','30 author-curated cases (24 answerable, 6 unanswerable), based on this 21-SKU convenience sample. Relevance IDs and rationales are committed before evaluation. They have not been independently annotated. Test contains Thai paraphrases and specific filters. Recall@3 excludes unanswerable cases; their empty-result correctness is scored separately. One test case has 4 relevant products, so its best possible recall@3 is0.75. MRR is truncated at3. No faithfulness, Thai fluency or user preference metric is inferred from these numbers.','',out['protocol'],'','## Per-case failures','']
    for r in out['systems']['hybrid']['cases']:
        if r['recall_at_3'] is not None and r['recall_at_3']<1 or r['abstention_correct'] is False:
            lines.append(f"- {r['id']}: {r['query']} -> {r['retrieved']}; expected {r['expected']}")
    (ROOT/'evaluation/RESULTS.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({name:{split:system[split] for split in ['dev','test','all']} for name,system in out['systems'].items()},indent=2))


if __name__=='__main__':main()
