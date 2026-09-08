#!/usr/bin/env python3
from __future__ import annotations
import hashlib, importlib.util, json, statistics, sys
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def load(p): return json.loads(p.read_text(encoding='utf-8'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def fail(msg): raise AssertionError(msg)
def main():
    planp=ROOT/'v5_data/base/plan-template.base.v1.json'; recp=ROOT/'v5_data/base/recipes.base.v1.json'; ingp=ROOT/'v5_data/base/ingredients.base.v1.json'; manp=ROOT/'v5_data/base/base-dataset-manifest.json'; curp=ROOT/'spec/v6/phase-c-curation.json'; polp=ROOT/'spec/v6/phase-a-policy.json'
    plan,rec,ing,man,cur=map(load,(planp,recp,ingp,manp,curp))
    for name,obj in [('plan',plan),('recipes',rec),('ingredients',ing),('manifest',man)]:
        if obj.get('dataset_version')!='tatadiet-base-v2': fail(f'{name} is not v2')
    if len(plan['days'])!=180 or sum(len(d['meals']) for d in plan['days'])!=864: fail('plan size mismatch')
    if len(cur['days'])!=180 or cur['summary']['meals']!=864: fail('curation size mismatch')
    versions={v['id']:v for v in rec['recipe_versions']}; families={f['id']:f for f in rec['recipe_families']}
    assignments={m['meal_id']:m['selected_recipe_version_id'] for d in cur['days'] for m in d['meals']}
    changed=0
    for d in plan['days']:
        for m in d['meals']:
            if assignments.get(m['id'])!=m['recipe_version_id']: fail(f'curation mismatch {m["id"]}')
            if m['recipe_version_id'] not in versions: fail(f'unknown version {m["recipe_version_id"]}')
            cm=next(x for x in next(x for x in cur['days'] if x['global_day']==d['base_global_day'])['meals'] if x['meal_id']==m['id'])
            changed+=int(cm['changed'])
    if changed!=709 or cur['summary']['changed_meals']!=709: fail('changed meal count mismatch')
    phaseb=[v for v in rec['recipe_versions'] if str(v['recipe_id']).startswith('base:recipe:v6-')]
    phasec=[v for v in rec['recipe_versions'] if str(v['recipe_id']).startswith('base:recipe:v6c-')]
    if len(phaseb)!=84 or len(phasec)!=15: fail(f'extension counts mismatch B={len(phaseb)} C={len(phasec)}')
    if any(float(v.get('servings') or 0)!=1.0 for v in phaseb+phasec): fail('scaled V6 serving found')
    if sum(int(v.get('curated_occurrence_count') or 0) for v in rec['recipe_versions'])!=864: fail('curated occurrence metadata mismatch')
    spec=importlib.util.spec_from_file_location('audit_v6',ROOT/'scripts/audit_v6_phase_a.py'); mod=importlib.util.module_from_spec(spec); sys.modules['audit_v6']=mod; spec.loader.exec_module(mod)
    ds=mod.load_dataset(polp,planp,recp,ingp); mod.validate_contract(ds); result=mod.audit(ds)
    if result['hard_violations']: fail(f'hard violations: {len(result["hard_violations"])}')
    if result['soft_warnings'] or result['repeats'] or result['seasonality']: fail('soft/repeat/seasonality warnings remain')
    refs=load(polp)['energy_diagnostics']['reference_kcal_by_day_type']; deltas=[]
    for d in plan['days']:
        ref=float(refs[d['day_type']]); delta=abs(float(d['source_total']['energy_kcal'])-ref)/ref; deltas.append(delta)
        if delta>0.05+1e-9: fail(f'energy curation gate failed day {d["base_global_day"]}: {delta:.4f}')
    family_use=Counter(versions[m['recipe_version_id']]['recipe_id'] for d in plan['days'] for m in d['meals'])
    for name,path in [('ingredients.base.v1.json',ingp),('recipes.base.v1.json',recp),('plan-template.base.v1.json',planp)]:
        if man['files'][name]['sha256']!=sha(path): fail(f'manifest hash mismatch {name}')
    ext=man['extensions']['v6_phase_c_curation']
    if ext['source_sha256']!=sha(curp): fail('curation hash mismatch')
    s=result['summary']; print(json.dumps({'status':'ok','dataset_version':'tatadiet-base-v2','days':180,'meals':864,'changed_days':cur['summary']['changed_days'],'changed_meals':709,'families_used':s['counts']['recipe_families_used'],'hard_violations':0,'soft_warnings':0,'max_energy_delta_pct':round(max(deltas)*100,2),'median_energy_delta_pct':round(statistics.median(deltas)*100,2),'max_family_occurrences_180d':max(family_use.values()),'phase_b_recipes':len(phaseb),'phase_c_targeted_recipes':len(phasec)},ensure_ascii=False,indent=2))
if __name__=='__main__': main()
