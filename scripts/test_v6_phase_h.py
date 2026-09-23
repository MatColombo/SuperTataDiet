#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def load(p): return json.loads((ROOT/p).read_text(encoding='utf-8'))
def sha(p): return hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
def text(p): return (ROOT/p).read_text(encoding='utf-8')

def main():
    policy=load('spec/v6/phase-h-policy.json')
    manifest=load('v5_data/base/base-dataset-manifest.json')
    assert policy['policy_version']=='6.0.0'
    assert manifest['phase_version']=='6.0.0'
    ext=manifest.get('extensions',{}).get('v6_phase_h') or {}
    assert ext.get('version')=='6.0.0'
    assert ext.get('policy_sha256')==sha('spec/v6/phase-h-policy.json')
    expected={
      'ingredients.base.v1.json':'1765f980c824b1d11b44155ac813a5b285ce57e527c0a9ace088468f24e84a1b',
      'recipes.base.v1.json':'535376cdea1d2508aa53a64c4bdf99a59cadbfd5644a5a3becd9f4fef87aa237',
      'plan-template.base.v1.json':'9a155f1bf900f55e83ad5c569d3529eba96c021fa503f14fa9a0becf9210428d',
    }
    for name,digest in expected.items():
        assert sha('v5_data/base/'+name)==digest,name
        assert sha('docs/data/v5/'+name)==digest,'published '+name
    assert load('docs/data/build-meta.json')['version']=='6.0.4'
    assert sha('docs/data/v6/phase-h-policy.json')==sha('spec/v6/phase-h-policy.json')
    assert sha('docs/data/v5/base-dataset-manifest.json')==sha('v5_data/base/base-dataset-manifest.json')
    build=text('scripts/build_site.py'); validator=text('scripts/validate_site.py')
    assert 'VERSION = "6.0.4"' in build and 'VERSION = "6.0.4"' in validator
    db=text('static/assets/js/v5-db.js'); backup=text('static/assets/js/v5-backup.js'); pwa=text('static/assets/js/pwa.js')
    assert 'const APP_VERSION = "6.0.4";' in db
    assert 'const APP_VERSION = "6.0.4";' in backup
    assert 'const DB_VERSION = 2;' in db and 'const SCHEMA_VERSION = 2;' in db
    assert 'const DB_NAME = "tatadiet-v5";' in db
    assert 'const SCHEMA_VERSION = 2;' in backup
    assert '|| "6.0.4"' in pwa
    for rel in ['templates/base.html','templates/home.html','templates/preferences.html','templates/day_manager.html','templates/recipe_scheduler.html','templates/shopping_range.html']:
        assert 'V5.2.1' not in text(rel),rel
    home=text('docs/index.html'); today=text('docs/oggi/index.html')
    assert 'data-version="6.0.4"' in home and 'V6.0.4' in home
    assert 'data-version="6.0.4"' in today
    webmanifest=load('docs/manifest.webmanifest')
    assert any(x.get('url')=='diario/index.html' for x in webmanifest.get('shortcuts',[]))
    sw=text('docs/service-worker.js')
    required_core=['diario/index.html','assets/js/v6-recipe-converter.js','assets/js/v6-diary-core.js','assets/js/v6-diary-store.js','assets/js/v6-diary.js','data/v6/phase-f-policy.json','data/v6/phase-g-policy.json','data/v6/phase-h-policy.json']
    for item in required_core: assert f'"{item}"' in sw,item
    offline=load('docs/data/offline-assets.json')
    for item in required_core:
        assert item in offline['assets'],item
    # Prior regression reports must exist after the integrated runner.
    prior=[
      'qa/v6-phase-d/phase-d-core-report.json','qa/v6-phase-e/phase-e-core-report.json',
      'qa/v6-phase-f/phase-f-release-report.json','qa/v6-phase-g/phase-g-release-report.json'
    ]
    for rel in prior:
        assert load(rel).get('status')=='ok',rel
    report={'status':'ok','phase':'V6-H','release':'6.0.4','checks':{
      'release_version_coherent':True,'baseline_c2_byte_identity':True,'manifest_h_extension':True,
      'published_h_policy':True,'indexeddb_schema_v2':True,'backup_schema_v2':True,'legacy_db_name_retained':True,
      'user_facing_branding_v6':True,'offline_core_v6_complete':True,'diary_pwa_shortcut':True,'prior_phase_reports_green':True}}
    out=ROOT/'qa/v6-phase-h/phase-h-release-report.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__': main()
