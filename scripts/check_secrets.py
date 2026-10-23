"""Fail closed on accidental known-secret inclusion in source/build output."""
from pathlib import Path
from dotenv import dotenv_values
import subprocess

ROOT=Path(__file__).resolve().parents[1]
values=dotenv_values(ROOT/'.env')
needles=[v.encode() for k,v in values.items() if k=='OPENAI_API_KEY' and v and len(v)>6]
files=subprocess.check_output(['git','ls-files','-co','--exclude-standard','-z'],cwd=ROOT).decode().split('\0')
leaks=[]
for rel in files:
    p=ROOT/rel
    if rel and p.is_file() and any(n in p.read_bytes() for n in needles):leaks.append(rel)
for p in (ROOT/'site/dist').rglob('*'):
    if p.is_file() and any(n in p.read_bytes() for n in needles):leaks.append(str(p.relative_to(ROOT)))
if leaks:
    print('Secret inclusion detected in:',leaks)
    raise SystemExit(1)
print('Known API key absent from Git-eligible files and build output. Local .env/.dev.vars are ignored.')
