#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, statistics
from collections import defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CURATION=ROOT/'spec/v6/phase-c2-curation.json'
POLICY=ROOT/'spec/v6/phase-c2-policy.json'
REC_SPEC=ROOT/'spec/v6/phase-c2-recipes.json'
PLAN=ROOT/'v5_data/base/plan-template.base.v1.json'
RECIPES=ROOT/'v5_data/base/recipes.base.v1.json'
INGREDIENTS=ROOT/'v5_data/base/ingredients.base.v1.json'
MANIFEST=ROOT/'v5_data/base/base-dataset-manifest.json'
STAMP='2026-09-08T15:05:00+02:00'
DATASET='tatadiet-base-v2'
PHASE='6.0.0-phase-c2.1'
NUTRIENTS=('energy_kcal','protein_g','carbohydrate_g','fat_g','fiber_g')

def load(p): return json.loads(p.read_text(encoding='utf-8'))
def dump(p,x): p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    cur=load(CURATION); plan=load(PLAN); rec=load(RECIPES); ing=load(INGREDIENTS); man=load(MANIFEST)
    versions={v['id']:v for v in rec['recipe_versions']}
    cdays={int(d['global_day']):d for d in cur['days']}
    if len(plan.get('days',[]))!=180 or len(cdays)!=180: raise ValueError('C2 requires exactly 180 days')
    selected=[]
    ingredient_days=defaultdict(set); ingredient_qty=defaultdict(float)
    for day in plan['days']:
        g=int(day['base_global_day']); cd=cdays[g]; amap={m['meal_id']:m for m in cd['meals']}
        if len(amap)!=len(day['meals']): raise ValueError(f'meal count mismatch day {g}')
        totals={k:0.0 for k in NUTRIENTS}
        for meal in day['meals']:
            cm=amap.get(meal['id'])
            if not cm: raise ValueError(f'missing C2 assignment {meal["id"]}')
            vid=cm['selected_recipe_version_id']
            if vid not in versions: raise ValueError(f'unknown recipe version {vid}')
            v=versions[vid]
            meal['recipe_version_id']=vid; meal['recipe_id']=v['recipe_id']; selected.append((meal['id'],vid))
            n=v['nutrition']['values_per_serving']
            for key in NUTRIENTS: totals[key]+=float(n.get(key) or 0)
            for line in v.get('ingredient_lines',[]):
                code=line.get('ingredient_code')
                if not code: continue
                ingredient_days[code].add(g); ingredient_qty[code]+=float(line.get('base_quantity') or 0)
        day['source_total']={k:round(v,3) for k,v in totals.items()}
    plan['dataset_version']=DATASET; plan['generated_at']=STAMP
    vals={k:[float(d['source_total'][k]) for d in plan['days']] for k in NUTRIENTS}
    plan['summary']={
        'energy_kcal':{'min':round(min(vals['energy_kcal']),3),'max':round(max(vals['energy_kcal']),3),'mean':round(statistics.mean(vals['energy_kcal']),3)},
        'protein_g':round(statistics.mean(vals['protein_g']),6),'carbohydrate_g':round(statistics.mean(vals['carbohydrate_g']),6),
        'fat_g':round(statistics.mean(vals['fat_g']),6),'fiber_g':round(statistics.mean(vals['fiber_g']),6),
    }
    occurrence={v['id']:[] for v in rec['recipe_versions']}
    for mid,vid in selected: occurrence[vid].append(mid)
    for v in rec['recipe_versions']:
        v['curated_occurrence_ids']=occurrence[v['id']]; v['curated_occurrence_count']=len(occurrence[v['id']])
    rec['dataset_version']=DATASET; rec['generated_at']=STAMP
    for item in ing['ingredients']:
        code=item['code']; basis=item.get('nutrition_basis') or {}
        item['usage']={
            'used_in_base_plan':bool(ingredient_days[code]),
            'occurrence_days':len(ingredient_days[code]),
            'total_base_quantity':round(ingredient_qty[code],3),
            'base_unit':basis.get('unit') or 'g',
        }
    ing['dataset_version']=DATASET; ing['generated_at']=STAMP
    dump(PLAN,plan); dump(RECIPES,rec); dump(INGREDIENTS,ing)
    man['dataset_version']=DATASET; man['phase_version']=PHASE; man['generated_at']=STAMP
    man.setdefault('extensions',{})['v6_phase_c2_curation']={
        'version':PHASE,'source':'spec/v6/phase-c2-curation.json','source_sha256':sha(CURATION),
        'policy_source':'spec/v6/phase-c2-policy.json','policy_sha256':sha(POLICY),
        'recipe_source':'spec/v6/phase-c2-recipes.json','recipe_source_sha256':sha(REC_SPEC),
        'days_reviewed':180,'changed_days_vs_phase_c1':cur['summary']['changed_days_vs_phase_c1'],
        'changed_meals_vs_phase_c1':cur['summary']['changed_meals_vs_phase_c1'],
        'note':'Frozen C2 editorial curation: exactly three counted dairy portions and two 75 g avocado portions per rolling 7 days, with dairy variety and purchase reuse.'
    }
    man['files']['ingredients.base.v1.json']={'sha256':sha(INGREDIENTS),'records':len(ing['ingredients'])}
    man['files']['recipes.base.v1.json']={'sha256':sha(RECIPES),'recipe_families':len(rec['recipe_families']),'recipe_versions':len(rec['recipe_versions'])}
    man['files']['plan-template.base.v1.json']={'sha256':sha(PLAN),'days':len(plan['days']),'meals':sum(len(d['meals']) for d in plan['days'])}
    dump(MANIFEST,man)
    print(json.dumps({'status':'ok','dataset_version':DATASET,'phase_version':PHASE,'days':180,'meals':len(selected),'changed_meals_vs_phase_c1':cur['summary']['changed_meals_vs_phase_c1']},ensure_ascii=False,indent=2))
if __name__=='__main__': main()
