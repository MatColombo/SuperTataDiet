#!/usr/bin/env python3
from __future__ import annotations
import csv, importlib.util, json, statistics, sys
from collections import Counter, defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
POL_A=ROOT/'spec/v6/phase-a-policy.json'
POL_C1=ROOT/'spec/v6/phase-c1-policy.json'
REC_SPEC=ROOT/'spec/v6/phase-c1-recipes.json'
CUR=ROOT/'spec/v6/phase-c1-curation.json'
PLAN=ROOT/'v5_data/base/plan-template.base.v1.json'
REC=ROOT/'v5_data/base/recipes.base.v1.json'
ING=ROOT/'v5_data/base/ingredients.base.v1.json'
OUT=ROOT/'qa/v6-phase-c1'

def load(p): return json.loads(p.read_text(encoding='utf-8'))
def wjson(p,x): p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')
def wcsv(p,fields,rows):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('w',newline='',encoding='utf-8-sig') as h:
        w=csv.DictWriter(h,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows)
def audit_mod():
    sp=importlib.util.spec_from_file_location('audit_v6_c1_base',ROOT/'scripts/audit_v6_phase_a.py');m=importlib.util.module_from_spec(sp);sys.modules['audit_v6_c1_base']=m;sp.loader.exec_module(m);return m

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    a=audit_mod(); ds=a.load_dataset(POL_A,PLAN,REC,ING); a.validate_contract(ds); base=a.audit(ds); a.emit(base,ds,OUT)
    c1=load(POL_C1); rspec=load(REC_SPEC); cur=load(CUR); plan=ds.plan; rec=ds.recipes; ing=ds.ingredients
    versions=ds.versions_by_id; families=ds.families_by_id; ingredients=ds.ingredients_by_code
    # Occurrence tables.
    ingredient_occ=defaultdict(list); family_occ=defaultdict(list); slot_families=defaultdict(set)
    protein_codes=set(sum(ds.policy['classification']['protein_groups'].values(),[]))
    for o in base['occurrences']:
        v=versions[o['recipe_version_id']]; family_occ[v['recipe_id']].append(o); slot_families[o['meal_type']].add(v['recipe_id'])
        seen=set()
        for line in v.get('ingredient_lines',[]):
            code=line.get('ingredient_code')
            if not code: continue
            ingredient_occ[code].append({'global_day':o['global_day'],'meal_id':o['meal_id'],'meal_type':o['meal_type'],'quantity':float(line.get('base_quantity') or 0),'recipe_id':v['recipe_id'],'recipe_version_id':v['id']})
            seen.add(code)
    ing_count=Counter({c:len(rows) for c,rows in ingredient_occ.items()}); fam_count=Counter({r:len(rows) for r,rows in family_occ.items()})
    # Recipe usage.
    recipe_rows=[]
    for rid,rows in family_occ.items():
        days=sorted(o['global_day'] for o in rows); gaps=[b-a for a,b in zip(days,days[1:])]
        recipe_rows.append({'recipe_id':rid,'title':families[rid]['title'],'occurrences':len(rows),'distinct_days':len(set(days)),'minimum_gap_days':min(gaps) if gaps else '','median_gap_days':round(statistics.median(gaps),1) if gaps else ''})
    recipe_rows.sort(key=lambda x:(-x['occurrences'],x['title'].casefold()));wcsv(OUT/'recipe-usage.csv',list(recipe_rows[0]),recipe_rows)
    # Ingredient frequency.
    freq_rows=[]
    for code,n in ing_count.most_common():
        rows=ingredient_occ[code]; item=ingredients.get(code,{})
        freq_rows.append({'ingredient_code':code,'ingredient_name':item.get('name',code),'category':item.get('category_name',''),'meal_occurrences':n,'distinct_days':len({r['global_day'] for r in rows}),'total_base_quantity':round(sum(r['quantity'] for r in rows),2),'base_unit':(item.get('nutrition_basis') or {}).get('unit','g')})
    wcsv(OUT/'ingredient-frequency.csv',list(freq_rows[0]),freq_rows)
    # Package-sensitive dairy audit.
    horizon=int(c1['purchase_reuse']['reuse_horizon_days']); dairy_rows=[]; dairy_fail=0
    for code in c1['purchase_reuse']['package_sensitive_dairy']['codes']:
        rows=ingredient_occ[code]; isolated=[]
        for i,r in enumerate(rows):
            if not any(i!=j and abs(r['global_day']-r2['global_day'])<=horizon for j,r2 in enumerate(rows)): isolated.append(r)
        dairy_fail+=len(isolated)
        dairy_rows.append({'ingredient_code':code,'ingredient_name':ingredients.get(code,{}).get('name',code),'occurrences':len(rows),'distinct_days':len({r['global_day'] for r in rows}),'total_quantity_g':round(sum(r['quantity'] for r in rows),1),'isolated_occurrences':len(isolated),'isolated_days':','.join(map(str,sorted(r['global_day'] for r in isolated))),'status':'OK' if not isolated else 'KO'})
    wcsv(OUT/'dairy-reuse-audit.csv',list(dairy_rows[0]),dairy_rows)
    # Batch-reuse preference audit (not shelf-stable items).
    batch_rows=[]; batch_fail=0; batch_min=float(c1['purchase_reuse']['minimum_share_of_occurrences_with_neighbor_in_horizon'])
    for code in c1['purchase_reuse']['batch_reuse_preference_codes']:
        rows=ingredient_occ[code]; paired=0
        for i,r in enumerate(rows):
            if any(i!=j and abs(r['global_day']-r2['global_day'])<=horizon for j,r2 in enumerate(rows)): paired+=1
        share=paired/len(rows) if rows else 0.0; ok=share+1e-12>=batch_min; batch_fail+=int(not ok)
        batch_rows.append({'ingredient_code':code,'ingredient_name':ingredients.get(code,{}).get('name',code),'occurrences':len(rows),'paired_within_4d':paired,'paired_share':round(share,4),'target_share':batch_min,'status':'OK' if ok else 'REVIEW'})
    wcsv(OUT/'purchase-reuse-audit.csv',list(batch_rows[0]),batch_rows)
    # Global caps and activation.
    g=c1['global_variety_targets']; cap_map={
        'banana':g['max_banana_meals'],'carota':g['max_carrot_meals'],'spinaci':g['max_spinach_meals'],'zucca':g['max_pumpkin_meals'],'hummus':g['max_hummus_meals'],'salmone':g['max_salmon_meals'],'bresaola':g['max_bresaola_meals'],'tacchino_affettato':g['max_sliced_turkey_meals'],'burro_arachidi':g['max_peanut_butter_meals'],'tonno_naturale':g['max_tuna_meals'],'tacchino':g['max_fresh_turkey_meals'],'lupini':g['max_lupin_meals']}
    cap_rows=[{'ingredient_code':c,'observed':ing_count[c],'limit':lim,'status':'OK' if ing_count[c]<=lim else 'KO'} for c,lim in cap_map.items()]
    wcsv(OUT/'global-caps.csv',list(cap_rows[0]),cap_rows)
    amin=int(c1['rotation_activation_targets']['minimum_occurrences_180d']); act_rows=[{'ingredient_code':c,'ingredient_name':ingredients.get(c,{}).get('name',c),'observed':ing_count[c],'minimum':amin,'status':'OK' if ing_count[c]>=amin else 'KO'} for c in c1['rotation_activation_targets']['ingredient_codes']]
    wcsv(OUT/'activation-audit.csv',list(act_rows[0]),act_rows)
    # Distribution shares.
    fruit=set(c1['diversity_groups']['fruit_codes']); all_ortho={x['code'] for x in ing['ingredients'] if x.get('category_name')=='Ortofrutta'}; veg=all_ortho-fruit
    fruitc=Counter({c:ing_count[c] for c in fruit}); vegc=Counter({c:ing_count[c] for c in veg}); legumes=c1['diversity_groups']['legume_codes']; leg_total=sum(ing_count[c] for c in legumes)
    fruit_share=sum(n for _,n in fruitc.most_common(3))/sum(fruitc.values()); veg_share=sum(n for _,n in vegc.most_common(3))/sum(vegc.values()); chick_share=(ing_count['ceci']+ing_count['hummus'])/leg_total if leg_total else 0
    distribution={'fruit_top3':fruitc.most_common(3),'fruit_top3_share':round(fruit_share,4),'fruit_limit':g['max_top3_fruit_share'],'vegetable_top3':vegc.most_common(3),'vegetable_top3_share':round(veg_share,4),'vegetable_limit':g['max_top3_vegetable_share'],'legume_counts':{c:ing_count[c] for c in legumes},'chickpea_plus_hummus_share':round(chick_share,4),'chickpea_plus_hummus_limit':g['max_chickpea_plus_hummus_share_of_legume_meals']}
    wjson(OUT/'distribution-shares.json',distribution)
    # Protein rotation by ingredient.
    protein_rows=[]
    rev={c:group for group,codes in ds.policy['classification']['protein_groups'].items() for c in codes}
    for code in sorted(protein_codes,key=lambda c:(rev.get(c,''),-ing_count[c],c)):
        if ing_count[code]: protein_rows.append({'protein_group':rev.get(code,''),'ingredient_code':code,'ingredient_name':ingredients.get(code,{}).get('name',code),'meal_occurrences':ing_count[code],'distinct_days':len({r['global_day'] for r in ingredient_occ[code]})})
    wcsv(OUT/'protein-rotation.csv',list(protein_rows[0]),protein_rows)
    # C1 recipe contract: fixed portions, exclusions, meaningful animal main quantities, moderate fiber.
    role_by_title={r['title']:r for r in rspec['recipes']}; c1_versions=[v for v in rec['recipe_versions'] if str(v['recipe_id']).startswith('base:recipe:v6c1-')]
    forbidden=set(c1['explicit_exclusions']); forbidden_hits=[]; portion_fail=[]; fiber_fail=[]
    animal=set(c1['diversity_groups']['fresh_animal_protein_codes']); main_roles={'main_other','curation_brunch','pasta_animal'}
    for v in c1_versions:
        title=families[v['recipe_id']]['title']; sr=role_by_title[title]; codes={l['ingredient_code'] for l in v['ingredient_lines']}
        if codes&forbidden or any(x in title.casefold() for x in forbidden): forbidden_hits.append(title)
        if float(v.get('servings') or 0)!=1.0: portion_fail.append({'title':title,'kind':'servings','observed':v.get('servings')})
        if sr['role'] in main_roles:
            for l in v['ingredient_lines']:
                if l['ingredient_code'] in animal and float(l.get('base_quantity') or 0)<float(c1['purchase_reuse']['full_portion_minimums_g']['fresh_meat_or_fish_in_main_meal']): portion_fail.append({'title':title,'kind':'animal_main_quantity','ingredient_code':l['ingredient_code'],'observed':l.get('base_quantity')})
            fiber=float(v['nutrition']['values_per_serving']['fiber_g'])
            if fiber>12.0+1e-9: fiber_fail.append({'title':title,'fiber_g':fiber})
    # Energy gate.
    refs=ds.policy['energy_diagnostics']['reference_kcal_by_day_type']; energy_rows=[]
    for d in plan['days']:
        ref=float(refs[d['day_type']]); val=float(d['source_total']['energy_kcal']); pct=(val-ref)/ref
        energy_rows.append({'global_day':d['base_global_day'],'month':d['month'],'day_type':d['day_type'],'energy_kcal':round(val,2),'reference_kcal':ref,'delta_pct':round(pct,4),'status':'OK' if abs(pct)<=.05+1e-9 else 'KO'})
    wcsv(OUT/'energy-audit.csv',list(energy_rows[0]),energy_rows)
    # 864-row review sheet as CSV.
    curmeal={m['meal_id']:m for d in cur['days'] for m in d['meals']}; review=[]
    for o in base['occurrences']:
        v=versions[o['recipe_version_id']]; lines=sorted(v.get('ingredient_lines',[]),key=lambda x:float(x.get('base_quantity') or 0),reverse=True)[:3]; cl=o['classification']; cm=curmeal[o['meal_id']]
        review.append({'giorno':o['global_day'],'mese':o['month'],'turno':o['day_type'],'pasto':o['meal_type'],'nome_ricetta':families[v['recipe_id']]['title'],'kcal':round(float(v['nutrition']['values_per_serving']['energy_kcal']),1),'ingredienti_principali':' · '.join(l.get('label') or l.get('ingredient_code','') for l in lines),'uova_albume':'SI' if float(cl['egg_equivalent_units'])>0 else 'NO','latticini_conteggiati':'SI' if cl['dairy_occurrence'] else 'NO','proteine_g':round(float(v['nutrition']['values_per_serving']['protein_g']),1),'fibre_g':round(float(v['nutrition']['values_per_serving']['fiber_g']),1),'modificato_vs_phase_c':'SI' if cm['changed'] else 'NO'})
    wcsv(OUT/'meal-review.csv',list(review[0]),review)
    # Slot diversity.
    slot_rows=[]
    for mt in sorted(slot_families):
        meals=sum(1 for o in base['occurrences'] if o['meal_type']==mt);slot_rows.append({'meal_type':mt,'meals':meals,'distinct_recipe_families':len(slot_families[mt]),'meals_per_family':round(meals/len(slot_families[mt]),2)})
    wcsv(OUT/'slot-diversity.csv',list(slot_rows[0]),slot_rows)
    # Summary / gates.
    hard_n=len(base['hard_violations']); soft_n=len(base['soft_warnings']); rep_n=len(base['repeats']); sea_n=len(base['seasonality']); max_energy=max(abs(r['delta_pct']) for r in energy_rows)
    gates={
        'phase_a_hard_violations':hard_n,'phase_a_soft_warnings':soft_n,'recipe_repeats_within_7d':rep_n,'off_season_occurrences':sea_n,
        'energy_days_outside_5pct':sum(r['status']=='KO' for r in energy_rows),'max_energy_delta_pct':round(max_energy*100,2),
        'max_recipe_family_occurrences':max(fam_count.values()),'family_cap':g['max_recipe_family_occurrences_180d'],
        'global_cap_failures':sum(r['status']=='KO' for r in cap_rows),'activation_failures':sum(r['status']=='KO' for r in act_rows),
        'isolated_package_sensitive_dairy_occurrences':dairy_fail,'batch_reuse_preference_failures':batch_fail,
        'fruit_top3_share':round(fruit_share,4),'fruit_top3_limit':g['max_top3_fruit_share'],'vegetable_top3_share':round(veg_share,4),'vegetable_top3_limit':g['max_top3_vegetable_share'],
        'chickpea_hummus_share':round(chick_share,4),'chickpea_hummus_limit':g['max_chickpea_plus_hummus_share_of_legume_meals'],
        'forbidden_ingredient_hits':len(forbidden_hits),'fixed_or_portion_contract_failures':len(portion_fail),'c1_main_fiber_failures':len(fiber_fail),
    }
    all_ok=not any([hard_n,soft_n,rep_n,sea_n,gates['energy_days_outside_5pct'],gates['global_cap_failures'],gates['activation_failures'],dairy_fail,batch_fail,len(forbidden_hits),len(portion_fail),len(fiber_fail)]) and fruit_share<=g['max_top3_fruit_share']+1e-12 and veg_share<=g['max_top3_vegetable_share']+1e-12 and chick_share<=g['max_chickpea_plus_hummus_share_of_legume_meals']+1e-12 and max(fam_count.values())<=g['max_recipe_family_occurrences_180d']
    prev={}
    prevp=ROOT/'qa/v6-phase-c/phase-c-summary.json'
    if prevp.exists():
        x=load(prevp); prev={'phase_c_recipe_families_used':x.get('catalog',{}).get('recipe_families_used'),'phase_c_max_family_occurrences':x.get('global_variety',{}).get('max_family_occurrences_180d')}
    summary={'phase':'V6-C1','status':'ok' if all_ok else 'review','dataset_version':plan.get('dataset_version'),'policy_version':c1['policy_version'],'curation':cur['summary'],'catalog':{'recipe_families':len(rec['recipe_families']),'recipe_versions':len(rec['recipe_versions']),'c1_recipe_families':len(c1_versions),'recipe_families_used':len(fam_count)},'gates':gates,'distribution':distribution,'slot_diversity':slot_rows,'previous_phase':prev,'top_recipe_families':recipe_rows[:12]}
    wjson(OUT/'phase-c1-summary.json',summary)
    print(json.dumps({'status':summary['status'],'families_used':len(fam_count),'max_family':max(fam_count.values()),'changed_meals_vs_phase_c':cur['summary']['changed_meals_vs_phase_c'],'gates':gates},ensure_ascii=False,indent=2))
    if not all_ok: raise SystemExit(2)
if __name__=='__main__': main()
