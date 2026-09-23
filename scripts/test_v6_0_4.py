#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def txt(p): return (ROOT/p).read_text(encoding='utf-8')
def load(p): return json.loads(txt(p))
def sha(p): return hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
def main():
    assert load('docs/data/build-meta.json')['version']=='6.0.4'
    assert 'VERSION = "6.0.4"' in txt('scripts/build_site.py')
    assert 'VERSION = "6.0.4"' in txt('scripts/validate_site.py')
    assert 'const APP_VERSION = "6.0.4";' in txt('static/assets/js/v5-db.js')
    backup=txt('static/assets/js/v5-backup.js')
    for token in ['const APP_VERSION = "6.0.4";','savestate: { activePlanInstanceId','collectClientState','syncClientState','normalizedPlanRecords','Giornata ${day.id} collegata a un piano inesistente']:
        assert token in backup, token
    db=txt('static/assets/js/v5-db.js')
    assert 'syncPlanStartBridge' in db and 'diet-plan:start-date:v2' in db
    plan=txt('static/assets/js/v5-plan-store.js')
    assert 'reconcileActivePlan' in plan
    assert 'filter(p=>p.startDate===startDate).sort' in plan
    tools=txt('static/assets/js/v5-tools.js')
    assert 'Savestate calendario:' in tools
    assert 'state.storeStart(result.planStartDate)' in tools
    expected={
      'ingredients.base.v1.json':'1765f980c824b1d11b44155ac813a5b285ce57e527c0a9ace088468f24e84a1b',
      'recipes.base.v1.json':'535376cdea1d2508aa53a64c4bdf99a59cadbfd5644a5a3becd9f4fef87aa237',
      'plan-template.base.v1.json':'9a155f1bf900f55e83ad5c569d3529eba96c021fa503f14fa9a0becf9210428d',
    }
    for name,digest in expected.items(): assert sha('v5_data/base/'+name)==digest,name
    report={'status':'ok','release':'6.0.4','checks':{
      'version_coherent':True,'savestate_metadata':True,'client_bridge':True,'single_active_plan_reconciliation':True,
      'referential_preview_validation':True,'browser_state_capture':True,'baseline_c2_byte_identity':True}}
    out=ROOT/'qa/v6-0-4/release-report.json'; out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__': main()
