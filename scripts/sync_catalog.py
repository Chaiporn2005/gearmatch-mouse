"""Copy the canonical source-backed catalog into the web bundle."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
data=json.loads((ROOT/'data/catalog.json').read_text())
assert len(data)==len({p['id'] for p in data})
assert all(p['sources'] and p['currency']=='USD' for p in data)
(ROOT/'site/lib/catalog.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
print('Synchronized',len(data),'catalog entries')
