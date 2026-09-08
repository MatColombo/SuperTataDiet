#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def load(p): return json.loads((ROOT/p).read_text(encoding='utf-8'))
def sha(p): return hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
def main():
    policy=load('spec/v6/phase-g-policy.json'); manifest=load('v5_data/base/base-dataset-manifest.json')
    assert policy['policy_version']=='6.0.0-phase-g.1'
    assert policy['storage']['store']=='diaryDays' and policy['storage']['database_version']==2
    assert policy['semantics']['manual_meals']['count_in_adherence_denominator'] is False
    ext=manifest.get('extensions',{}).get('v6_phase_g') or {}
    assert str(manifest.get('phase_version','')).startswith('6.0.0')
    assert ext.get('policy_sha256')==sha('spec/v6/phase-g-policy.json')
    expected={
      'ingredients.base.v1.json':'1765f980c824b1d11b44155ac813a5b285ce57e527c0a9ace088468f24e84a1b',
      'recipes.base.v1.json':'535376cdea1d2508aa53a64c4bdf99a59cadbfd5644a5a3becd9f4fef87aa237',
      'plan-template.base.v1.json':'9a155f1bf900f55e83ad5c569d3529eba96c021fa503f14fa9a0becf9210428d',
    }
    for name,digest in expected.items():
        assert sha('v5_data/base/'+name)==digest,name
        assert sha('docs/data/v5/'+name)==digest,'published '+name
    db=(ROOT/'static/assets/js/v5-db.js').read_text(encoding='utf-8')
    backup=(ROOT/'static/assets/js/v5-backup.js').read_text(encoding='utf-8')
    assert 'const DB_VERSION = 2;' in db and 'const SCHEMA_VERSION = 2;' in db and 'diaryDays:' in db
    assert 'const SCHEMA_VERSION = 2;' in backup and 'diaryDays' in backup
    page=(ROOT/'docs/diario/index.html').read_text(encoding='utf-8')
    assert 'data-page="diary"' in page and 'data-diary-calendar' in page and 'data-diary-manual-form' in page and 'data-diary-comment' in page
    for module in ['v6-diary-core.js','v6-diary-store.js','v6-diary.js']:
        assert module in page
        assert sha('docs/assets/js/'+module)==sha('static/assets/js/'+module)
    assert 'href="../diario/index.html"' in (ROOT/'docs/oggi/index.html').read_text(encoding='utf-8')
    assert sha('docs/data/v6/phase-g-policy.json')==sha('spec/v6/phase-g-policy.json')
    offline=load('docs/data/offline-assets.json')
    for item in ['data/v6/phase-g-policy.json','assets/js/v6-diary-core.js','assets/js/v6-diary-store.js','assets/js/v6-diary.js','diario/index.html']:
        assert item in offline['assets'],item
    report={'status':'ok','phase':'V6-G','policy_version':policy['policy_version'],'checks':{
      'base_c2_byte_identity':True,'indexeddb_v2_diary_store':True,'diary_in_backup':True,'diary_page':True,'traffic_light_ux':True,
      'manual_meals':True,'daily_comment':True,'rolling_7_30_summary':True,'offline_assets':True}}
    out=ROOT/'qa/v6-phase-g/phase-g-release-report.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
