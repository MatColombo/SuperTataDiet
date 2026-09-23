#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def txt(p): return (ROOT/p).read_text(encoding='utf-8')
def load(p): return json.loads(txt(p))
def sha(p): return hashlib.sha256((ROOT/p).read_bytes()).hexdigest()

def main():
    assert load('docs/data/build-meta.json')['version']=='6.0.3'
    assert 'VERSION = "6.0.3"' in txt('scripts/build_site.py')
    assert 'VERSION = "6.0.3"' in txt('scripts/validate_site.py')
    assert 'const APP_VERSION = "6.0.3";' in txt('static/assets/js/v5-db.js')
    assert 'const APP_VERSION = "6.0.3";' in txt('static/assets/js/v5-backup.js')
    tools=txt('templates/tools.html')
    assert 'Ripristina tutto dal backup' in tools
    assert 'data-v5-restore-backup' in tools
    for forbidden in ['Compatibilità V4','data-import-preferences','data-v5-import-mode','>Unisci<','Sostituisci dati personali']:
        assert forbidden not in tools, forbidden
    plan=txt('static/assets/js/v5-plan-core.js')
    for token in ['templateDayOfType','seedNightTail','dropOvernightTail']:
        assert token in plan, token
    expected={
      'ingredients.base.v1.json':'1765f980c824b1d11b44155ac813a5b285ce57e527c0a9ace088468f24e84a1b',
      'recipes.base.v1.json':'535376cdea1d2508aa53a64c4bdf99a59cadbfd5644a5a3becd9f4fef87aa237',
      'plan-template.base.v1.json':'9a155f1bf900f55e83ad5c569d3529eba96c021fa503f14fa9a0becf9210428d',
    }
    for name,digest in expected.items(): assert sha('v5_data/base/'+name)==digest,name
    report={'status':'ok','release':'6.0.3','checks':{
      'version_coherent':True,'night_tail_core':True,'single_backup_restore_ui':True,'legacy_preferences_removed':True,'baseline_c2_byte_identity':True}}
    out=ROOT/'qa/v6-0-3/release-report.json'; out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__': main()
