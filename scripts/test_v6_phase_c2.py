#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def load(p): return json.loads(p.read_text(encoding='utf-8'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def fail(m): raise AssertionError(m)

def main():
    planp=ROOT/'v5_data/base/plan-template.base.v1.json'; recp=ROOT/'v5_data/base/recipes.base.v1.json'; ingp=ROOT/'v5_data/base/ingredients.base.v1.json'; manp=ROOT/'v5_data/base/base-dataset-manifest.json'
    curp=ROOT/'spec/v6/phase-c2-curation.json'; polp=ROOT/'spec/v6/phase-c2-policy.json'; specp=ROOT/'spec/v6/phase-c2-recipes.json'; sump=ROOT/'qa/v6-phase-c2/phase-c2-summary.json'
    plan,rec,ing,man,cur,pol,rspec,summ=map(load,(planp,recp,ingp,manp,curp,polp,specp,sump))
    if summ.get('status')!='ok': fail('C2 audit summary is not OK')
    if len(plan.get('days',[]))!=180 or sum(len(d['meals']) for d in plan['days'])!=864: fail('plan size mismatch')
    if len(cur.get('days',[]))!=180 or cur['summary']['meals']!=864: fail('curation size mismatch')
    if cur['summary']['changed_meals_vs_phase_c1']!=138 or cur['summary']['changed_days_vs_phase_c1']!=133: fail('unexpected C2 curation delta')
    versions={v['id']:v for v in rec['recipe_versions']}; families={f['id']:f for f in rec['recipe_families']}
    assign={m['meal_id']:m['selected_recipe_version_id'] for d in cur['days'] for m in d['meals']}
    for d in plan['days']:
        for m in d['meals']:
            if assign.get(m['id'])!=m['recipe_version_id']: fail('curation mismatch '+m['id'])
            if m['recipe_version_id'] not in versions: fail('unknown recipe '+m['recipe_version_id'])
    c2v=[v for v in rec['recipe_versions'] if str(v['recipe_id']).startswith('base:recipe:v6c2-')]
    if len(c2v)!=len(rspec['recipes']) or len(c2v)!=56: fail('C2 recipe count mismatch')
    if any(float(v.get('servings') or 0)!=1.0 for v in c2v): fail('scaled C2 serving found')
    avocado=[x for x in ing['ingredients'] if x['code']=='avocado']
    if len(avocado)!=1: fail('avocado ingredient missing/duplicated')
    if avocado[0]['provenance'].get('source_url')!='https://www.alimentinutrizione.it/tabelle-nutrizionali/007490': fail('avocado source mismatch')
    g=summ['gates']
    zero=['phase_a_hard_violations','phase_a_soft_warnings','recipe_repeats_within_7d','off_season_occurrences','energy_days_outside_5pct','rolling_contract_failures','daily_dairy_failures','fresh_dairy_isolated_occurrences','fresh_dairy_type_min_failures','avocado_bad_portions','avocado_isolated_occurrences','global_cap_failures','activation_failures','batch_reuse_preference_failures','c2_recipe_contract_failures']
    for k in zero:
        if g.get(k)!=0: fail(f'gate {k} failed: {g.get(k)}')
    if summ['dairy']['rolling_min']!=3 or summ['dairy']['rolling_max']!=3 or summ['dairy']['rolling_min_distinct_types']<2: fail('dairy rolling contract failed')
    if summ['dairy']['total_portions']!=77: fail('dairy semester count failed')
    if summ['avocado']['portions']!=52 or summ['avocado']['rolling_min']!=2 or summ['avocado']['rolling_max']!=2 or summ['avocado']['portion_g']!=75.0: fail('avocado contract failed')
    if g['max_recipe_family_occurrences']>g['family_cap']: fail('family cap failed')
    if g['fruit_top3_share']>g['fruit_top3_limit']+1e-9 or g['vegetable_top3_share']>g['vegetable_top3_limit']+1e-9 or g['chickpea_hummus_share']>g['chickpea_hummus_limit']+1e-9: fail('distribution gate failed')
    for name,path in [('ingredients.base.v1.json',ingp),('recipes.base.v1.json',recp),('plan-template.base.v1.json',planp)]:
        if man['files'][name]['sha256']!=sha(path): fail('manifest hash mismatch '+name)
    ext=man.get('extensions',{}).get('v6_phase_c2_curation') or {}
    if ext.get('source_sha256')!=sha(curp) or ext.get('policy_sha256')!=sha(polp) or ext.get('recipe_source_sha256')!=sha(specp): fail('C2 manifest extension hash mismatch')
    for name,path in [('ingredients.base.v1.json',ingp),('recipes.base.v1.json',recp),('plan-template.base.v1.json',planp),('base-dataset-manifest.json',manp)]:
        out=ROOT/'docs/data/v5'/name
        if not out.exists() or sha(out)!=sha(path): fail('PWA seed mismatch '+name)
    print(json.dumps({'status':'ok','days':180,'meals':864,'changed_days_vs_c1':133,'changed_meals_vs_c1':138,'c2_recipe_families':len(c2v),'catalog_families':len(rec['recipe_families']),'families_used':summ['catalog']['recipe_families_used'],'dairy_portions':summ['dairy']['total_portions'],'avocado_portions':summ['avocado']['portions'],'max_energy_delta_pct':g['max_energy_delta_pct']},ensure_ascii=False,indent=2))
if __name__=='__main__': main()
