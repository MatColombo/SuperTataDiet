#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, statistics
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def load(p): return json.loads(p.read_text(encoding='utf-8'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def fail(msg): raise AssertionError(msg)

def main():
    planp=ROOT/'v5_data/base/plan-template.base.v1.json'; recp=ROOT/'v5_data/base/recipes.base.v1.json'; ingp=ROOT/'v5_data/base/ingredients.base.v1.json'; manp=ROOT/'v5_data/base/base-dataset-manifest.json'; curp=ROOT/'spec/v6/phase-c1-curation.json'; polp=ROOT/'spec/v6/phase-c1-policy.json'; specp=ROOT/'spec/v6/phase-c1-recipes.json'; sump=ROOT/'qa/v6-phase-c1/phase-c1-summary.json'
    plan,rec,ing,man,cur,pol,rspec,summ=map(load,(planp,recp,ingp,manp,curp,polp,specp,sump))
    if summ.get('status')!='ok': fail('C1 audit summary is not OK')
    if len(plan.get('days',[]))!=180 or sum(len(d['meals']) for d in plan['days'])!=864: fail('plan size mismatch')
    if len(cur.get('days',[]))!=180 or cur['summary']['meals']!=864: fail('curation size mismatch')
    if cur['summary']['changed_meals_vs_phase_c']!=254 or cur['summary']['changed_days_vs_phase_c']!=131: fail('unexpected C1 curation deltas')
    versions={v['id']:v for v in rec['recipe_versions']}; families={f['id']:f for f in rec['recipe_families']}
    assign={m['meal_id']:m['selected_recipe_version_id'] for d in cur['days'] for m in d['meals']}
    for d in plan['days']:
        for m in d['meals']:
            if assign.get(m['id'])!=m['recipe_version_id']: fail(f'curation mismatch {m["id"]}')
            if m['recipe_version_id'] not in versions: fail(f'unknown recipe {m["recipe_version_id"]}')
    c1v=[v for v in rec['recipe_versions'] if str(v['recipe_id']).startswith('base:recipe:v6c1-')]
    if len(c1v)!=len(rspec['recipes']) or len(c1v)!=95: fail(f'C1 recipe count mismatch: {len(c1v)} vs spec {len(rspec["recipes"])}')
    if any(float(v.get('servings') or 0)!=1.0 for v in c1v): fail('scaled C1 serving found')
    forbidden=set(pol['explicit_exclusions'])
    for v in c1v:
        title=families[v['recipe_id']]['title'].casefold();codes={x.get('ingredient_code') for x in v.get('ingredient_lines',[])}
        if codes&forbidden or any(x in title for x in forbidden): fail(f'forbidden ingredient in C1: {title}')
    if sum(int(v.get('curated_occurrence_count') or 0) for v in rec['recipe_versions'])!=864: fail('curated occurrence metadata mismatch')
    g=summ['gates']
    zero_keys=['phase_a_hard_violations','phase_a_soft_warnings','recipe_repeats_within_7d','off_season_occurrences','energy_days_outside_5pct','global_cap_failures','activation_failures','isolated_package_sensitive_dairy_occurrences','batch_reuse_preference_failures','forbidden_ingredient_hits','fixed_or_portion_contract_failures','c1_main_fiber_failures']
    for k in zero_keys:
        if g.get(k)!=0: fail(f'gate {k} failed: {g.get(k)}')
    if g['max_recipe_family_occurrences']>g['family_cap']: fail('family cap failed')
    if g['fruit_top3_share']>g['fruit_top3_limit']+1e-9: fail('fruit concentration failed')
    if g['vegetable_top3_share']>g['vegetable_top3_limit']+1e-9: fail('vegetable concentration failed')
    if g['chickpea_hummus_share']>g['chickpea_hummus_limit']+1e-9: fail('legume distribution failed')
    # Manifest hashes and C1 extension.
    for name,path in [('ingredients.base.v1.json',ingp),('recipes.base.v1.json',recp),('plan-template.base.v1.json',planp)]:
        if man['files'][name]['sha256']!=sha(path): fail(f'manifest hash mismatch {name}')
    ext=man.get('extensions',{}).get('v6_phase_c1_curation') or {}
    if ext.get('source_sha256')!=sha(curp) or ext.get('policy_sha256')!=sha(polp) or ext.get('recipe_source_sha256')!=sha(specp): fail('C1 manifest extension hashes mismatch')
    # Built PWA seed must match source bytes.
    for name,path in [('ingredients.base.v1.json',ingp),('recipes.base.v1.json',recp),('plan-template.base.v1.json',planp),('base-dataset-manifest.json',manp)]:
        out=ROOT/'docs/data/v5'/name
        if not out.exists() or sha(out)!=sha(path): fail(f'PWA seed mismatch {name}')
    print(json.dumps({'status':'ok','days':180,'meals':864,'changed_days_vs_phase_c':cur['summary']['changed_days_vs_phase_c'],'changed_meals_vs_phase_c':cur['summary']['changed_meals_vs_phase_c'],'c1_recipe_families':len(c1v),'catalog_families':len(rec['recipe_families']),'families_used':summ['catalog']['recipe_families_used'],'max_family_occurrences':g['max_recipe_family_occurrences'],'max_energy_delta_pct':g['max_energy_delta_pct'],'isolated_dairy':g['isolated_package_sensitive_dairy_occurrences']},ensure_ascii=False,indent=2))
if __name__=='__main__': main()
