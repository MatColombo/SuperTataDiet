#!/usr/bin/env python3
from __future__ import annotations
import csv,json,statistics
from collections import Counter,defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'qa/v6-phase-c'
def load(p): return json.loads(p.read_text(encoding='utf-8'))
def write_json(p,x): p.write_text(json.dumps(x,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')
def write_csv(p,fields,rows):
    with p.open('w',newline='',encoding='utf-8-sig') as h:
        w=csv.DictWriter(h,fieldnames=fields); w.writeheader(); w.writerows(rows)
def main():
    OUT.mkdir(parents=True,exist_ok=True)
    cur=load(ROOT/'spec/v6/phase-c-curation.json'); plan=load(ROOT/'v5_data/base/plan-template.base.v1.json'); rec=load(ROOT/'v5_data/base/recipes.base.v1.json'); before=load(ROOT/'qa/v6-phase-a/summary.json'); after=load(OUT/'summary.json'); policy=load(ROOT/'spec/v6/phase-a-policy.json')
    versions={v['id']:v for v in rec['recipe_versions']}; families={f['id']:f for f in rec['recipe_families']}
    class_rows=list(csv.DictReader((OUT/'recipe-classification.csv').open(encoding='utf-8-sig'))); cl={r['recipe_version_id']:r for r in class_rows}
    day_rows=[]; meal_rows=[]
    for d in cur['days']:
        day_rows.append({k:d[k] for k in ['global_day','month','day_type','weekly_focus','review_status','changed_meals','energy_kcal','energy_reference_kcal','energy_delta_pct','egg_equivalent_units','dairy_meals','pasta_rice_primary_meals','plant_protein_main_meals']})
        for m in d['meals']:
            meal_rows.append({'global_day':d['global_day'],'month':d['month'],'day_type':d['day_type'],'weekly_focus':d['weekly_focus'],**m,'reasons':' | '.join(m['reasons'])})
    write_csv(OUT/'day-curation.csv',list(day_rows[0]),day_rows); write_csv(OUT/'meal-curation.csv',list(meal_rows[0]),meal_rows)
    usage=defaultdict(list)
    for d in plan['days']:
        for m in d['meals']: usage[versions[m['recipe_version_id']]['recipe_id']].append(d['base_global_day'])
    ur=[]
    for rid,days in usage.items():
        gaps=[b-a for a,b in zip(days,days[1:]) if b!=a]
        ur.append({'recipe_id':rid,'title':families[rid]['title'],'occurrences':len(days),'distinct_days':len(set(days)),'minimum_gap_days':min(gaps) if gaps else '','median_gap_days':round(statistics.median(gaps),1) if gaps else ''})
    ur.sort(key=lambda x:(-x['occurrences'],x['title'].casefold())); write_csv(OUT/'recipe-usage.csv',list(ur[0]),ur)
    month_order=['Settembre','Ottobre','Novembre','Dicembre','Gennaio','Febbraio']; mr=[]
    for month in month_order:
        ds=[d for d in plan['days'] if d['month']==month]; mids=[m for d in ds for m in d['meals']]; counts=Counter(); egg=0.0; kcal=[]
        for d in ds:
            kcal.append(float(d['source_total']['energy_kcal']))
            for m in d['meals']:
                c=cl[m['recipe_version_id']]; egg+=float(c['egg_equivalent_units']); counts['dairy']+=c['dairy_occurrence']=='yes'; counts['plant']+=c['plant_protein_main']=='yes'; counts['pasta']+=c['primary_carb']=='pasta'; counts['rice']+=c['primary_carb']=='rice'
        mr.append({'month':month,'days':len(ds),'meals':len(mids),'mean_kcal':round(statistics.mean(kcal),1),'egg_equivalent_units':round(egg,1),'dairy_meals':counts['dairy'],'plant_main_meals':counts['plant'],'pasta_primary_meals':counts['pasta'],'rice_primary_meals':counts['rice'],'pasta_rice_total':counts['pasta']+counts['rice']})
    write_csv(OUT/'monthly-balance.csv',list(mr[0]),mr)
    legcodes=set(policy['hard_constraints']['plant_protein_main']['legume_codes']); lc=Counter()
    for d in plan['days']:
        for m in d['meals']:
            if cl[m['recipe_version_id']]['plant_protein_main']!='yes': continue
            for line in versions[m['recipe_version_id']]['ingredient_lines']:
                if line['ingredient_code'] in legcodes: lc[line['ingredient_code']]+=1
    lrows=[{'ingredient_code':k,'plant_main_occurrences':v} for k,v in lc.most_common()]; write_csv(OUT/'plant-protein-distribution.csv',list(lrows[0]),lrows)
    refs=policy['energy_diagnostics']['reference_kcal_by_day_type']; deltas=[abs(float(d['source_total']['energy_kcal'])-float(refs[d['day_type']]))/float(refs[d['day_type']]) for d in plan['days']]
    summary={'phase':'V6-C','dataset_version':'tatadiet-base-v2','curation':cur['summary'],'catalog':{'recipe_families':len(rec['recipe_families']),'recipe_versions':len(rec['recipe_versions']),'phase_c_targeted_recipes':sum(str(v['recipe_id']).startswith('base:recipe:v6c-') for v in rec['recipe_versions']),'recipe_families_used':after['counts']['recipe_families_used']},'compliance':{'hard_violations':len(load(OUT/'violations.json')['hard_violations']),'soft_warning_counts':after['soft_constraints']['warning_counts'],'recipe_repeats_within_7d':after['soft_constraints']['recipe_repeats_within_7d'],'off_season_occurrences':after['soft_constraints']['off_season_occurrences'],'max_energy_delta_pct':round(max(deltas)*100,2),'median_energy_delta_pct':round(statistics.median(deltas)*100,2)},'rolling_7d':after['hard_constraints'],'global_variety':{'max_family_occurrences_180d':max(x['occurrences'] for x in ur),'families_over_15_occurrences':sum(x['occurrences']>15 for x in ur),'top_10_families':ur[:10]},'before_after':{'phase_a_hard_failure_counts':before['hard_constraints']['failure_counts'],'phase_a_recipe_repeats_7d':before['soft_constraints']['recipe_repeats_within_7d'],'phase_a_off_season':before['soft_constraints']['off_season_occurrences'],'phase_c_hard_failure_counts':after['hard_constraints']['failure_counts'],'phase_c_recipe_repeats_7d':after['soft_constraints']['recipe_repeats_within_7d'],'phase_c_off_season':after['soft_constraints']['off_season_occurrences']}}
    write_json(OUT/'phase-c-summary.json',summary); print(json.dumps(summary['compliance'],indent=2))
if __name__=='__main__': main()
