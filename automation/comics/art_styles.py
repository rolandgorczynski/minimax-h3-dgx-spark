"""Gemeinsamer Stil-Katalog von Dashboard und nativem Comic-Renderer."""
import json
from pathlib import Path
ROOT=Path('/app/comic-design')
if not ROOT.exists():ROOT=Path(__file__).resolve().parents[2]/'extensions/dgx-comics'
CATALOG=json.loads((ROOT/'style_catalog.json').read_text())
NAMES=[s['name'] for s in CATALOG]
BY_ID={s['id']:s for s in CATALOG}
BY_NAME={s['name']:s for s in CATALOG}
def public():return [{k:s[k] for k in ('id','name','category','description')}|{'preview':'/style-previews/'+s['id']+'.webp'} for s in CATALOG]
