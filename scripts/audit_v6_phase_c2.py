#!/usr/bin/env python3
from __future__ import annotations
import csv, importlib.util, json, statistics, sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
POL_A=ROOT/'spec/v6/phase-a-policy.json'
POL_C1=ROOT/'spec/v6/phase-c1-policy.json'
POL_C2=ROOT/'spec/v6/phase-c2-policy.json'
REC_SPEC=ROOT/'spec/v6/phase-c2-recipes.json'
CUR=ROOT/'spec/v6/phase-c2-curation.json'
PLAN=ROOT/'v5_data/base/plan-template.base.v1.json'
REC=ROOT/'v5_data/base/recipes.base.v1.json'
ING=ROOT/'v5_data/base/ingredients.base.v1.json'
OUT=ROOT/'qa/v6-phase-c2'


def load(p): return json.loads(p.read_text(encoding='utf-8'))
def wjson(p,x): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(x,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')
def wcsv(p,fields,rows):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('w',newline='',encoding='utf-8-sig') as h:
        w=csv.DictWriter(h,fieldnames=fields,extrasaction='ignore'); w.writeheader(); w.writerows(rows)
def audit_mod():
    sp=importlib.util.spec_from_file_location('audit_v6_c2_base',ROOT/'scripts/audit_v6_phase_a.py')
    m=importlib.util.module_from_spec(sp); sys.modules['audit_v6_c2_base']=m; sp.loader.exec_module(m); return m


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    a=audit_mod(); ds=a.load_dataset(POL_A,PLAN,REC,ING); a.validate_contract(ds); base=a.audit(ds); a.emit(base,ds,OUT)
    c1=load(POL_C1); c2=load(POL_C2); rspec=load(REC_SPEC); cur=load(CUR)
    plan=ds.plan; rec=ds.recipes; ing=ds.ingredients; versions=ds.versions_by_id; families=ds.families_by_id; ingredients=ds.ingredients_by_code
    dairy_codes=set(c2['counted_dairy']['included_codes']); fresh_dairy=set(c2['purchase_reuse']['fresh_dairy_codes']); avo_code=c2['avocado']['ingredient_code']
    ingredient_occ=defaultdict(list); family_occ=defaultdict(list); dairy_type_count=Counter(); avo_occ=[]
    for o in base['occurrences']:
        v=versions[o['recipe_version_id']]; family_occ[v['recipe_id']].append(o)
        for line in v.get('ingredient_lines',[]):
            code=line.get('ingredient_code')
            if not code: continue
            row={'global_day':o['global_day'],'meal_id':o['meal_id'],'meal_type':o['meal_type'],'quantity':float(line.get('base_quantity') or 0),'recipe_id':v['recipe_id'],'recipe_version_id':v['id']}
            ingredient_occ[code].append(row)
            if code in dairy_codes: dairy_type_count[code]+=1
            if code==avo_code: avo_occ.append(row)
    ing_count=Counter({c:len(rows) for c,rows in ingredient_occ.items()}); fam_count=Counter({r:len(rows) for r,rows in family_occ.items()})

    # Exact rolling-window contract.
    window_rows=[]; window_fail=0
    for st in range(0,len(plan['days'])-6):
        dairy_n=0; dtypes=set(); avo_n=0; avo_g=0.0
        for day in plan['days'][st:st+7]:
            for m in day['meals']:
                v=versions[m['recipe_version_id']]
                codes={l['ingredient_code'] for l in v.get('ingredient_lines',[])}
                hits=codes&dairy_codes
                if hits: dairy_n+=1; dtypes.update(hits)
                for l in v.get('ingredient_lines',[]):
                    if l.get('ingredient_code')==avo_code:
                        avo_n+=1; avo_g+=float(l.get('base_quantity') or 0)
        ok=(dairy_n==int(c2['counted_dairy']['min_meals_per_rolling_7d'])==int(c2['counted_dairy']['max_meals_per_rolling_7d']) and
            len(dtypes)>=int(c2['counted_dairy']['min_distinct_dairy_types_per_rolling_7d']) and
            avo_n==int(c2['avocado']['min_portions_per_rolling_7d'])==int(c2['avocado']['max_portions_per_rolling_7d']) and
            abs(avo_g-avo_n*float(c2['avocado']['portion_g']))<1e-9)
        window_fail+=int(not ok)
        window_rows.append({'start_day':st+1,'end_day':st+7,'dairy_portions':dairy_n,'distinct_dairy_types':len(dtypes),'dairy_types':','.join(sorted(dtypes)),
                            'avocado_portions':avo_n,'avocado_total_g':round(avo_g,1),'status':'OK' if ok else 'KO'})
    wcsv(OUT/'rolling-window-audit.csv',list(window_rows[0]),window_rows)

    # Daily dairy cap.
    daily_rows=[]; daily_fail=0
    for d in plan['days']:
        hits=[]
        for m in d['meals']:
            v=versions[m['recipe_version_id']]; codes={l['ingredient_code'] for l in v.get('ingredient_lines',[])}; hits.extend(sorted(codes&dairy_codes))
        ok=len(hits)<=int(c2['counted_dairy']['max_meals_per_day']); daily_fail+=int(not ok)
        daily_rows.append({'global_day':d['base_global_day'],'month':d['month'],'day_type':d['day_type'],'dairy_portions':len(hits),'dairy_types':','.join(hits),'status':'OK' if ok else 'KO'})
    wcsv(OUT/'daily-dairy-audit.csv',list(daily_rows[0]),daily_rows)

    # Fresh dairy purchase reuse and type variety.
    horizon=int(c2['purchase_reuse']['fresh_dairy_reuse_horizon_days']); dairy_rows=[]; isolated_fresh=0; type_min_fail=0
    min_type_occ=6
    for code in sorted(dairy_codes):
        rows=ingredient_occ[code]; isolated=[]
        if code in fresh_dairy:
            for i,r in enumerate(rows):
                if not any(i!=j and abs(r['global_day']-r2['global_day'])<=horizon for j,r2 in enumerate(rows)): isolated.append(r)
            isolated_fresh+=len(isolated)
            if len(rows)<min_type_occ: type_min_fail+=1
        dairy_rows.append({'ingredient_code':code,'ingredient_name':ingredients.get(code,{}).get('name',code),'occurrences':len(rows),'distinct_days':len({r['global_day'] for r in rows}),
                           'total_quantity_g':round(sum(r['quantity'] for r in rows),1),'isolated_fresh_occurrences':len(isolated),'minimum_semester_occurrences':min_type_occ if code in fresh_dairy else '',
                           'status':'OK' if (not isolated and (code not in fresh_dairy or len(rows)>=min_type_occ)) else 'KO'})
    wcsv(OUT/'dairy-type-rotation.csv',list(dairy_rows[0]),dairy_rows)

    # Avocado purchase reuse and portion contract.
    avo_isolated=[]; avo_bad_portions=[]; ah=int(c2['avocado']['reuse_horizon_days']); portion=float(c2['avocado']['portion_g'])
    for i,r in enumerate(avo_occ):
        if abs(r['quantity']-portion)>1e-9: avo_bad_portions.append(r)
        if not any(i!=j and abs(r['global_day']-r2['global_day'])<=ah for j,r2 in enumerate(avo_occ)): avo_isolated.append(r)
    avo_rows=[{'global_day':r['global_day'],'meal_id':r['meal_id'],'meal_type':r['meal_type'],'quantity_g':r['quantity'],
               'paired_within_4d':'SI' if r not in avo_isolated else 'NO','status':'OK' if r not in avo_isolated and abs(r['quantity']-portion)<1e-9 else 'KO'} for r in avo_occ]
    wcsv(OUT/'avocado-reuse-audit.csv',list(avo_rows[0]),avo_rows)

    # C1 global diversity gates preserved.
    g=c1['global_variety_targets']; cap_map={'banana':g['max_banana_meals'],'carota':g['max_carrot_meals'],'spinaci':g['max_spinach_meals'],'zucca':g['max_pumpkin_meals'],'hummus':g['max_hummus_meals'],'salmone':g['max_salmon_meals'],'bresaola':g['max_bresaola_meals'],'tacchino_affettato':g['max_sliced_turkey_meals'],'burro_arachidi':g['max_peanut_butter_meals'],'tonno_naturale':g['max_tuna_meals'],'tacchino':g['max_fresh_turkey_meals'],'lupini':g['max_lupin_meals']}
    cap_rows=[{'ingredient_code':c,'observed':ing_count[c],'limit':lim,'status':'OK' if ing_count[c]<=lim else 'KO'} for c,lim in cap_map.items()]; wcsv(OUT/'global-caps.csv',list(cap_rows[0]),cap_rows)
    amin=int(c1['rotation_activation_targets']['minimum_occurrences_180d']); act_rows=[{'ingredient_code':c,'observed':ing_count[c],'minimum':amin,'status':'OK' if ing_count[c]>=amin else 'KO'} for c in c1['rotation_activation_targets']['ingredient_codes']]; wcsv(OUT/'activation-audit.csv',list(act_rows[0]),act_rows)
    batch_rows=[]; batch_fail=0; batch_min=float(c1['purchase_reuse']['minimum_share_of_occurrences_with_neighbor_in_horizon']); bh=int(c1['purchase_reuse']['reuse_horizon_days'])
    for code in c1['purchase_reuse']['batch_reuse_preference_codes']:
        rows=ingredient_occ[code]; paired=sum(any(i!=j and abs(r['global_day']-r2['global_day'])<=bh for j,r2 in enumerate(rows)) for i,r in enumerate(rows)); share=paired/len(rows) if rows else 0.0; ok=share+1e-12>=batch_min; batch_fail+=int(not ok)
        batch_rows.append({'ingredient_code':code,'occurrences':len(rows),'paired_within_4d':paired,'paired_share':round(share,4),'target_share':batch_min,'status':'OK' if ok else 'REVIEW'})
    wcsv(OUT/'purchase-reuse-audit.csv',list(batch_rows[0]),batch_rows)

    fruit=set(c1['diversity_groups']['fruit_codes'])|{avo_code}; all_ortho={x['code'] for x in ing['ingredients'] if x.get('category_name')=='Ortofrutta'}; veg=all_ortho-fruit
    fruitc=Counter({c:ing_count[c] for c in fruit}); vegc=Counter({c:ing_count[c] for c in veg}); legumes=c1['diversity_groups']['legume_codes']; leg_total=sum(ing_count[c] for c in legumes)
    fruit_share=sum(n for _,n in fruitc.most_common(3))/sum(fruitc.values()); veg_share=sum(n for _,n in vegc.most_common(3))/sum(vegc.values()); chick_share=(ing_count['ceci']+ing_count['hummus'])/leg_total if leg_total else 0
    distribution={'fruit_top3':fruitc.most_common(3),'fruit_top3_share':round(fruit_share,4),'fruit_limit':g['max_top3_fruit_share'],'vegetable_top3':vegc.most_common(3),'vegetable_top3_share':round(veg_share,4),'vegetable_limit':g['max_top3_vegetable_share'],'chickpea_plus_hummus_share':round(chick_share,4),'chickpea_plus_hummus_limit':g['max_chickpea_plus_hummus_share_of_legume_meals']}
    wjson(OUT/'distribution-shares.json',distribution)

    # Energy and recipe-family diversity.
    refs=ds.policy['energy_diagnostics']['reference_kcal_by_day_type']; energy_rows=[]
    for d in plan['days']:
        ref=float(refs[d['day_type']]); val=float(d['source_total']['energy_kcal']); pct=(val-ref)/ref
        energy_rows.append({'global_day':d['base_global_day'],'month':d['month'],'day_type':d['day_type'],'energy_kcal':round(val,2),'reference_kcal':ref,'delta_pct':round(pct,4),'status':'OK' if abs(pct)<=.05+1e-9 else 'KO'})
    wcsv(OUT/'energy-audit.csv',list(energy_rows[0]),energy_rows)
    recipe_rows=[]
    for rid,rows in family_occ.items():
        days=sorted(o['global_day'] for o in rows); gaps=[b-a for a,b in zip(days,days[1:])]
        recipe_rows.append({'recipe_id':rid,'title':families[rid]['title'],'occurrences':len(rows),'distinct_days':len(set(days)),'minimum_gap_days':min(gaps) if gaps else '','median_gap_days':round(statistics.median(gaps),1) if gaps else ''})
    recipe_rows.sort(key=lambda x:(-x['occurrences'],x['title'].casefold())); wcsv(OUT/'recipe-usage.csv',list(recipe_rows[0]),recipe_rows)

    # C2 recipe contract.
    spec_by_title={r['title']:r for r in rspec['recipes']}; c2versions=[v for v in rec['recipe_versions'] if str(v['recipe_id']).startswith('base:recipe:v6c2-')]
    contract_fail=[]
    for v in c2versions:
        title=families[v['recipe_id']]['title']; sr=spec_by_title.get(title)
        if sr is None: contract_fail.append({'title':title,'reason':'missing_from_spec'}); continue
        if float(v.get('servings') or 0)!=1.0: contract_fail.append({'title':title,'reason':'servings_not_1'})
        codes={l['ingredient_code'] for l in v.get('ingredient_lines',[])}
        if codes&set(c2['explicit_exclusions']): contract_fail.append({'title':title,'reason':'forbidden_ingredient'})
        if avo_code in codes:
            q=sum(float(l.get('base_quantity') or 0) for l in v['ingredient_lines'] if l['ingredient_code']==avo_code)
            if abs(q-portion)>1e-9: contract_fail.append({'title':title,'reason':'avocado_portion_not_75g'})
        for code in codes&fresh_dairy:
            expected=float(c2['purchase_reuse']['fresh_dairy_pair_quantities_g'][code]); q=sum(float(l.get('base_quantity') or 0) for l in v['ingredient_lines'] if l['ingredient_code']==code)
            if abs(q-expected)>1e-9: contract_fail.append({'title':title,'reason':f'{code}_portion_mismatch'})

    # Review table.
    curmeal={m['meal_id']:m for d in cur['days'] for m in d['meals']}; review=[]
    for o in base['occurrences']:
        v=versions[o['recipe_version_id']]; lines=sorted(v.get('ingredient_lines',[]),key=lambda x:float(x.get('base_quantity') or 0),reverse=True)[:3]; cl=o['classification']; cm=curmeal[o['meal_id']]
        review.append({'giorno':o['global_day'],'mese':o['month'],'turno':o['day_type'],'pasto':o['meal_type'],'nome_ricetta':families[v['recipe_id']]['title'],'kcal':round(float(v['nutrition']['values_per_serving']['energy_kcal']),1),'ingredienti_principali':' | '.join(l.get('label') or l.get('ingredient_code','') for l in lines),'uova_albume':'SI' if float(cl['egg_equivalent_units'])>0 else 'NO','latticini_conteggiati':'SI' if cl['dairy_occurrence'] else 'NO','tipo_latticino':','.join(cl['dairy_codes']),'avocado':'SI' if avo_code in cl['ingredient_codes'] else 'NO','proteine_g':round(float(v['nutrition']['values_per_serving']['protein_g']),1),'fibre_g':round(float(v['nutrition']['values_per_serving']['fiber_g']),1),'modificato_vs_c1':'SI' if cm['changed'] else 'NO'})
    wcsv(OUT/'meal-review.csv',list(review[0]),review)

    hard_n=len(base['hard_violations']); soft_n=len(base['soft_warnings']); rep_n=len(base['repeats']); sea_n=len(base['seasonality'])
    energy_fail=sum(r['status']=='KO' for r in energy_rows); max_energy=max(abs(r['delta_pct']) for r in energy_rows)
    gates={'phase_a_hard_violations':hard_n,'phase_a_soft_warnings':soft_n,'recipe_repeats_within_7d':rep_n,'off_season_occurrences':sea_n,
           'energy_days_outside_5pct':energy_fail,'max_energy_delta_pct':round(max_energy*100,2),'rolling_contract_failures':window_fail,
           'daily_dairy_failures':daily_fail,'fresh_dairy_isolated_occurrences':isolated_fresh,'fresh_dairy_type_min_failures':type_min_fail,
           'avocado_bad_portions':len(avo_bad_portions),'avocado_isolated_occurrences':len(avo_isolated),'avocado_occurrences_180d':len(avo_occ),
           'dairy_occurrences_180d':sum(dairy_type_count.values()),'max_recipe_family_occurrences':max(fam_count.values()),'family_cap':g['max_recipe_family_occurrences_180d'],
           'global_cap_failures':sum(r['status']=='KO' for r in cap_rows),'activation_failures':sum(r['status']=='KO' for r in act_rows),'batch_reuse_preference_failures':batch_fail,
           'fruit_top3_share':round(fruit_share,4),'fruit_top3_limit':g['max_top3_fruit_share'],'vegetable_top3_share':round(veg_share,4),'vegetable_top3_limit':g['max_top3_vegetable_share'],
           'chickpea_hummus_share':round(chick_share,4),'chickpea_hummus_limit':g['max_chickpea_plus_hummus_share_of_legume_meals'],'c2_recipe_contract_failures':len(contract_fail)}
    all_ok=not any([hard_n,soft_n,rep_n,sea_n,energy_fail,window_fail,daily_fail,isolated_fresh,type_min_fail,len(avo_bad_portions),len(avo_isolated),gates['global_cap_failures'],gates['activation_failures'],batch_fail,len(contract_fail)]) and max(fam_count.values())<=g['max_recipe_family_occurrences_180d'] and fruit_share<=g['max_top3_fruit_share']+1e-12 and veg_share<=g['max_top3_vegetable_share']+1e-12 and chick_share<=g['max_chickpea_plus_hummus_share_of_legume_meals']+1e-12 and len(avo_occ)==52 and sum(dairy_type_count.values())==77
    summary={'phase':'V6-C2','status':'ok' if all_ok else 'review','dataset_version':plan.get('dataset_version'),'policy_version':c2['policy_version'],'curation':cur['summary'],
             'catalog':{'ingredients':len(ing['ingredients']),'recipe_families':len(rec['recipe_families']),'recipe_versions':len(rec['recipe_versions']),'c2_recipe_families':len(c2versions),'recipe_families_used':len(fam_count)},
             'dairy':{'total_portions':sum(dairy_type_count.values()),'type_counts':dict(sorted(dairy_type_count.items())),'rolling_min':min(r['dairy_portions'] for r in window_rows),'rolling_max':max(r['dairy_portions'] for r in window_rows),'rolling_min_distinct_types':min(r['distinct_dairy_types'] for r in window_rows)},
             'avocado':{'portions':len(avo_occ),'portion_g':portion,'total_g':round(sum(r['quantity'] for r in avo_occ),1),'rolling_min':min(r['avocado_portions'] for r in window_rows),'rolling_max':max(r['avocado_portions'] for r in window_rows)},
             'distribution':distribution,'gates':gates,'top_recipe_families':recipe_rows[:12]}
    wjson(OUT/'phase-c2-summary.json',summary)
    print(json.dumps({'status':summary['status'],'dairy':summary['dairy'],'avocado':summary['avocado'],'gates':gates},ensure_ascii=False,indent=2))
    if not all_ok: raise SystemExit(2)

if __name__=='__main__': main()
