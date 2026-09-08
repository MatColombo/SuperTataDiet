#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def load(p): return json.loads((ROOT/p).read_text(encoding='utf-8'))
def sha(p): return hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
def main():
    policy=load('spec/v6/phase-e-policy.json'); manifest=load('v5_data/base/base-dataset-manifest.json'); core=load('qa/v6-phase-e/phase-e-core-report.json')
    assert policy['policy_version']=='6.0.0-phase-e.1'
    assert policy['energy']['target_min_kcal']==800 and policy['energy']['target_max_kcal']==2600
    assert policy['planner_contract']['fixed_recipe_servings'] is True
    assert policy['planner_contract']['no_silent_constraint_override'] is True
    assert policy['slots']['allow_optional_slot_skipping'] is True
    assert core['status']=='ok' and core['checks']['target_range_800_2600_covered'] is True
    assert core['checks']['range_planning_clean'] is True and core['checks']['fixed_serving_automatic'] is True
    ext=manifest.get('extensions',{}).get('v6_phase_e') or {}
    assert manifest.get('extensions',{}).get('v6_phase_e',{}).get('version')=='6.0.0-phase-e.1'
    assert ext.get('policy_sha256')==sha('spec/v6/phase-e-policy.json')
    for f in ext.get('runtime_modules',[]): assert (ROOT/f).exists(),f
    # Base food/content assets must remain C2 byte-identical.
    expected={
      'ingredients.base.v1.json':'1765f980c824b1d11b44155ac813a5b285ce57e527c0a9ace088468f24e84a1b',
      'recipes.base.v1.json':'535376cdea1d2508aa53a64c4bdf99a59cadbfd5644a5a3becd9f4fef87aa237',
      'plan-template.base.v1.json':'9a155f1bf900f55e83ad5c569d3529eba96c021fa503f14fa9a0becf9210428d',
    }
    for name,digest in expected.items():
        assert sha('v5_data/base/'+name)==digest,name
        assert manifest['files'][name]['sha256']==digest,name
        assert sha('docs/data/v5/'+name)==digest,'published '+name
    for name in ['phase-a-policy.json','phase-c1-policy.json','phase-c2-policy.json','phase-d-policy.json','phase-e-policy.json']:
        assert (ROOT/'docs/data/v6'/name).exists(),name
        assert sha('docs/data/v6/'+name)==sha('spec/v6/'+name),name
    for asset in ['v6-planner-core.js','v6-planner-store.js']:
        assert (ROOT/'docs/assets/js'/asset).exists(),asset
        assert sha('docs/assets/js/'+asset)==sha('static/assets/js/'+asset),asset
    html=(ROOT/'docs/index.html').read_text(encoding='utf-8')
    order=['v5-plan-core.js','v5-composer-core.js','v5-composer-store.js','v6-planner-core.js','v6-planner-store.js','v5-composer.js','v5-day-manager.js']
    positions=[html.find(x) for x in order]
    assert all(x>=0 for x in positions),positions
    assert positions==sorted(positions),f'unsafe script order: {list(zip(order,positions))}'
    sw=(ROOT/'docs/service-worker.js').read_text(encoding='utf-8')
    assert 'data/v6/phase-e-policy.json' in sw and 'v6-planner-core.js' in sw and 'v6-planner-store.js' in sw
    composer=(ROOT/'static/assets/js/v5-composer.js').read_text(encoding='utf-8')
    manager=(ROOT/'static/assets/js/v5-day-manager.js').read_text(encoding='utf-8')
    legacy=(ROOT/'static/assets/js/v5-planning-core.js').read_text(encoding='utf-8')
    assert 'plannerStore.previewDay' in composer and 'v6-plan-day' in composer
    assert 'v6Planner.planDay' in manager
    assert 'function portionForEnergy(oldNutrition,entry){return 1;}' in legacy
    report={'status':'ok','phase':'V6-E','policy_version':policy['policy_version'],'checks':{'manifest_extension':True,'base_c2_byte_identity':True,'published_policy':True,'published_runtime':True,'safe_script_order':True,'composer_uses_v6_planner':True,'day_manager_uses_v6_planner':True,'legacy_automatic_scaling_disabled':True,'service_worker_assets':True},'performance':core['performance']}
    out=ROOT/'qa/v6-phase-e/phase-e-release-report.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__': main()
