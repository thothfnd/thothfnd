from __future__ import annotations
from pathlib import Path
import json, re, base64

ROOT = Path(__file__).resolve().parents[1]

def load_json(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))

def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding='utf-8')

def slugify(value: str) -> str:
    value = value.strip().lower().replace('_','-')
    value = re.sub(r'[^a-z0-9-]+','-', value)
    return re.sub(r'-+','-',value).strip('-')

def b64decode_text(content: str) -> str:
    return base64.b64decode(content.encode('ascii')).decode('utf-8', errors='replace')

def parse_desc_md(text: str) -> dict:
    sections = {}
    current = None
    buf = []
    for raw in text.splitlines():
        if raw.startswith('# '):
            if current:
                sections[current] = '\n'.join(buf).strip()
            current = raw[2:].strip().lower()
            buf=[]
        else:
            buf.append(raw)
    if current:
        sections[current] = '\n'.join(buf).strip()
    out={}
    if sections.get('headline'): out['headline']=sections['headline'].replace('\n',' ').strip()
    if sections.get('overview'): out['overview']=' '.join(x.strip() for x in sections['overview'].splitlines() if x.strip())
    if sections.get('pillars'):
        out['pillars']=[re.sub(r'^[-*]\s*','',x).strip() for x in sections['pillars'].splitlines() if x.strip()][:6]
    return out
