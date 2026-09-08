#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, statistics
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CURATION=ROOT/'spec/v6/phase-c-curation.json'
PLAN=ROOT/'v5_data/base/plan-template.base.v1.json'
RECIPES=ROOT/'v5_data/base/recipes.base.v1.json'
INGREDIENTS=ROOT/'v5_data/base/ingredients.base.v1.json'
MANIFEST=ROOT/'v5_data/base/base-dataset-manifest.json'
STAMP='2026-09-08T10:30:00+02:00'
DATASET='tatadiet-base-v2'
PHASE='6.0.0-phase-c.1'
NUTRIENTS=('energy_kcal','protein_g','carbohydrate_g','fat_g','fiber_g')
def load(p): return json.loads(p.read_text(encoding='utf-8'))
def dump(p,x): p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    cur=load(CURATION); plan=load(PLAN); rec=load(RECIPES); ing=load(INGREDIENTS); man=load(MANIFEST)
    versions={v['id']:v for v in rec['recipe_versions']}
    cdays={int(d['global_day']):d for d in cur['days']}
    if len(plan.get('days',[]))!=180 or len(cdays)!=180: raise ValueError('Phase C requires 180 days')
    selected_ids=[]
    for day in plan['days']:
        g=int(day['base_global_day']); cd=cdays[g]
        assignments={m['meal_id']:m for m in cd['meals']}
        if len(assignments)!=len(day['meals']): raise ValueError(f'meal count mismatch day {g}')
        if 'original_source_total' not in day: day['original_source_total']=dict(day.get('source_total') or {})
        totals={k:0.0 for k in NUTRIENTS}
        for meal in day['meals']:
            cm=assignments.get(meal['id'])
            if not cm: raise ValueError(f'missing curation assignment {meal["id"]}')
            vid=cm['selected_recipe_version_id']
            if vid not in versions: raise ValueError(f'unknown recipe version {vid}')
            version=versions[vid]
            meal['recipe_version_id']=vid; meal['recipe_id']=version['recipe_id']
            selected_ids.append((meal['id'],vid))
            n=version['nutrition']['values_per_serving']
            for key in NUTRIENTS: totals[key]+=float(n.get(key) or 0)
        day['source_total']={k:round(v,3) for k,v in totals.items()}
    plan['dataset_version']=DATASET; plan['generated_at']=STAMP
    values={k:[float(d['source_total'][k]) for d in plan['days']] for k in NUTRIENTS}
    plan['summary']={
        'energy_kcal':{'min':round(min(values['energy_kcal']),3),'max':round(max(values['energy_kcal']),3),'mean':round(statistics.mean(values['energy_kcal']),3)},
        'protein_g':round(statistics.mean(values['protein_g']),6),
        'carbohydrate_g':round(statistics.mean(values['carbohydrate_g']),6),
        'fat_g':round(statistics.mean(values['fat_g']),6),
        'fiber_g':round(statistics.mean(values['fiber_g']),6),
    }
    occurrence={v['id']:[] for v in rec['recipe_versions']}
    for mid,vid in selected_ids: occurrence[vid].append(mid)
    for v in rec['recipe_versions']:
        v['curated_occurrence_ids']=occurrence[v['id']]
        v['curated_occurrence_count']=len(occurrence[v['id']])
    rec['dataset_version']=DATASET; rec['generated_at']=STAMP
    ing['dataset_version']=DATASET; ing['generated_at']=STAMP
    dump(PLAN,plan); dump(RECIPES,rec); dump(INGREDIENTS,ing)
    man['dataset_version']=DATASET; man['phase_version']=PHASE; man['generated_at']=STAMP
    man.setdefault('extensions',{})['v6_phase_c_curation']={
        'version':PHASE,'source':'spec/v6/phase-c-curation.json','source_sha256':sha(CURATION),
        'days_reviewed':180,'changed_days':cur['summary']['changed_days'],'changed_meals':cur['summary']['changed_meals'],
        'note':'Explicit one-shot curation of all 180 days; no runtime heuristic is required to reproduce the baseline.'}
    man['files']['ingredients.base.v1.json']={'sha256':sha(INGREDIENTS),'records':len(ing['ingredients'])}
    man['files']['recipes.base.v1.json']={'sha256':sha(RECIPES),'recipe_families':len(rec['recipe_families']),'recipe_versions':len(rec['recipe_versions'])}
    man['files']['plan-template.base.v1.json']={'sha256':sha(PLAN),'days':len(plan['days']),'meals':sum(len(d['meals']) for d in plan['days'])}
    dump(MANIFEST,man)
    print(json.dumps({'status':'ok','dataset_version':DATASET,'days':180,'meals':len(selected_ids),'changed_meals':cur['summary']['changed_meals']},indent=2))
if __name__=='__main__': main()
