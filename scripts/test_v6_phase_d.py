#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def load(p): return json.loads((ROOT/p).read_text(encoding='utf-8'))
def sha(p): return hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
def main():
    d=load('spec/v6/phase-d-policy.json'); manifest=load('v5_data/base/base-dataset-manifest.json'); c2=load('qa/v6-phase-c2/phase-c2-summary.json'); core=load('qa/v6-phase-d/phase-d-core-report.json')
    assert d['policy_version']=='6.0.0-phase-d.1'
    assert d['planner_contract']['fixed_recipe_servings'] is True
    assert d['planner_contract']['ingredient_conversion_is_read_only'] is True
    assert d['conversion']['allow_energy_only_in_greedy'] is False
    assert core['status']=='ok' and core['baseline']['hardViolations']==0 and core['baseline']['softWarnings']==0
    assert core['counts']['ingredients']==c2['catalog']['ingredients']==131
    assert core['counts']['recipeVersions']==c2['catalog']['recipe_versions']==797
    ext=manifest.get('extensions',{}).get('v6_phase_d') or {}
    assert ext.get('policy_sha256')==sha('spec/v6/phase-d-policy.json')
    for f in ext.get('runtime_modules',[]): assert (ROOT/f).exists(),f
    for name in ['phase-a-policy.json','phase-c1-policy.json','phase-c2-policy.json','phase-d-policy.json']:
        assert (ROOT/'docs/data/v6'/name).exists(),name
        assert sha('docs/data/v6/'+name)==sha('spec/v6/'+name),name
    for asset in ['v6-ingredient-intelligence-core.js','v6-constraint-core.js','v6-intelligence-store.js']:
        assert (ROOT/'docs/assets/js'/asset).exists(),asset
        assert sha('docs/assets/js/'+asset)==sha('static/assets/js/'+asset),asset
    html=(ROOT/'docs/index.html').read_text(encoding='utf-8')
    for asset in ['v6-ingredient-intelligence-core.js','v6-constraint-core.js','v6-intelligence-store.js']: assert asset in html
    sw=(ROOT/'docs/service-worker.js').read_text(encoding='utf-8')
    assert 'data/v6/phase-d-policy.json' in sw and 'v6-ingredient-intelligence-core.js' in sw
    report={'status':'ok','phase':'V6-D','policy_version':d['policy_version'],'checks':{'policy_contract':True,'manifest_extension':True,'published_policy_bundle':True,'published_runtime_modules':True,'baseline_c2_preserved':True,'service_worker_assets':True},'core_performance':core['performance']}
    out=ROOT/'qa/v6-phase-d/phase-d-release-report.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__': main()
