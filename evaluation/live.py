"""Small, explicit live-proxy smoke evaluation. Never logs configuration values."""
import json
import time
from pathlib import Path
from dotenv import load_dotenv
from app.agent import recommend
from app.models import SearchRequest
from app.retrieval import Index

ROOT=Path(__file__).resolve().parents[1]


def main():
    load_dotenv(ROOT/'.env',override=True)
    index=Index()
    cases=[
        {'id':'quiet-office','question':'แนะนำเมาส์เงียบสำหรับทำงาน ใช้ Bluetooth งบไม่เกิน 30 USD พร้อมข้อควรระวัง', 'filters':{'budget':30,'connection':'bluetooth','use_case':'office'}, 'expected':['logitech-pebble-2-m350s']},
        {'id':'left-impossible','question':'อยากได้เมาส์มือซ้าย Bluetooth น้ำหนักไม่เกิน 80 กรัม งบ 100 USD ถ้าไม่มีให้บอกว่าไม่มี', 'filters':{'budget':100,'max_weight':80,'handedness':'left','connection':'bluetooth'}, 'expected':[]},
        {'id':'gaming-light','question':'เลือกเมาส์เล่นเกมน้ำหนักเบาไม่เกิน 60 กรัม งบ 70 USD ช่วยเทียบ 2 รุ่นและอ้างอิงสเปก', 'filters':{'budget':70,'max_weight':60,'use_case':'gaming'},'expected':['keychron-m2-4k','keychron-m2-mini-8k','keychron-m3-mini-8k','razer-cobra']},
    ]
    out={'model':'gemma-4-E4B-it','temperature':0,'cases':[],'scope':'Live native function-calling smoke tests, separate from the 30-example offline retrieval benchmark.'}
    for case in cases:
        started=time.perf_counter()
        debug=[]
        try:
            result=recommend(SearchRequest(question=case['question'],filters=case['filters']),index,debug_sink=debug)
            predicted=[r['product_id'] for r in result['answer']['recommendations']]
            passed=(set(predicted).issubset(case['expected']) and bool(predicted)) if case['expected'] else (not predicted and result['answer']['abstain'])
            row={'id':case['id'],'question':case['question'],'filters':case['filters'],'expected':case['expected'],'passed':passed,'result':result}
        except Exception as exc:
            row={'id':case['id'],'passed':False,'error_type':type(exc).__name__,'reason':str(exc) if isinstance(exc,RuntimeError) else 'Class proxy error; configuration values omitted','elapsed_ms':round((time.perf_counter()-started)*1000),'model_turns':debug}
        out['cases'].append(row)
        (ROOT/'evaluation/live-results.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps({'id':row['id'],'passed':row['passed'],'error_type':row.get('error_type'),'elapsed_ms':row.get('result',{}).get('elapsed_ms',row.get('elapsed_ms'))}),flush=True)
    print('Live smoke cases passed:',sum(c['passed'] for c in out['cases']),'/',len(out['cases']))


if __name__=='__main__':main()
