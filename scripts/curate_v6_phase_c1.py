#!/usr/bin/env python3
"""One-shot Phase C.1 curation of the 180-day V6 baseline.

Starts from the approved Phase C plan currently stored in v5_data/base and writes an
explicit Phase C.1 curation contract. The plan itself is not modified here.
"""
from __future__ import annotations
import copy, hashlib, importlib.util, json, math, statistics, sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[1]
POLICY=ROOT/'spec/v6/phase-a-policy.json'
C1POL=ROOT/'spec/v6/phase-c1-policy.json'
C1REC=ROOT/'spec/v6/phase-c1-recipes.json'
PLAN=ROOT/'v5_data/base/plan-template.base.v1.json'
RECIPES=ROOT/'v5_data/base/recipes.base.v1.json'
INGREDIENTS=ROOT/'v5_data/base/ingredients.base.v1.json'
OUT=ROOT/'spec/v6/phase-c1-curation.json'
STAMP='2026-09-08T13:15:00+02:00'
MAIN_TYPES={'Pranzo','Cena','Brunch','Pasto preturno'}

def load(p): return json.loads(p.read_text(encoding='utf-8'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def load_audit():
    spec=importlib.util.spec_from_file_location('audit_v6_c1',ROOT/'scripts/audit_v6_phase_a.py')
    mod=importlib.util.module_from_spec(spec);sys.modules['audit_v6_c1']=mod;spec.loader.exec_module(mod);return mod


def main():
    audit=load_audit(); base_plan=load(PLAN); rec=load(RECIPES); ing=load(INGREDIENTS); pol=load(POLICY); c1pol=load(C1POL); c1spec=load(C1REC)
    ds=audit.load_dataset(POLICY,PLAN,RECIPES,INGREDIENTS)
    cls={v['id']:audit.classify_recipe(v,ds) for v in rec['recipe_versions']}
    versions={v['id']:v for v in rec['recipe_versions']}; families={f['id']:f for f in rec['recipe_families']}
    spec_months={r['title']:set(r['season_months']) for r in c1spec['recipes']}
    all_vids=[v['id'] for v in rec['recipe_versions']]
    c1_vids=[]
    for v in rec['recipe_versions']:
        if str(v['recipe_id']).startswith('base:recipe:v6c1-'):
            c1_vids.append(v['id'])
    if len(c1_vids)!=len(c1spec['recipes']): raise RuntimeError('C1 catalog not built or count mismatch')

    entries=[]; by_day=[[] for _ in base_plan['days']]; pos_by_meal={}
    for di,d in enumerate(base_plan['days']):
        for mi,m in enumerate(d['meals']):
            e={'day_index':di,'global_day':int(d['base_global_day']),'month':d['month'],'month_num':audit.MONTH_NUMBERS[d['month']], 'day_type':d['day_type'],'meal_index':mi,'meal_id':m['id'],'meal_type':m['meal_type'],'time':m['time'],'original_vid':m['recipe_version_id'],'vid':m['recipe_version_id'],'reasons':[]}
            idx=len(entries);entries.append(e);by_day[di].append(idx);pos_by_meal[m['id']]=idx
    refs=pol['energy_diagnostics']['reference_kcal_by_day_type']
    energy=lambda vid: float(versions[vid]['nutrition']['values_per_serving']['energy_kcal'])
    day_energy=[sum(energy(entries[i]['vid']) for i in ids) for ids in by_day]

    season_map={c:set(ms) for c,ms in pol['soft_constraints']['seasonality']['fresh_ingredient_months'].items()}
    excluded_conc=set(pol['soft_constraints']['ingredient_concentration']['excluded_codes'])
    hard=pol['hard_constraints']; soft=pol['soft_constraints']
    activation=set(c1pol['rotation_activation_targets']['ingredient_codes'])
    cluster_codes=set(c1pol['purchase_reuse']['batch_reuse_preference_codes'])
    target_caps={
        'banana':c1pol['global_variety_targets']['max_banana_meals'],
        'carota':c1pol['global_variety_targets']['max_carrot_meals'],
        'spinaci':c1pol['global_variety_targets']['max_spinach_meals'],
        'zucca':c1pol['global_variety_targets']['max_pumpkin_meals'],
        'hummus':c1pol['global_variety_targets']['max_hummus_meals'],
        'salmone':c1pol['global_variety_targets']['max_salmon_meals'],
        'bresaola':c1pol['global_variety_targets']['max_bresaola_meals'],
        'tacchino_affettato':c1pol['global_variety_targets']['max_sliced_turkey_meals'],
        'burro_arachidi':c1pol['global_variety_targets']['max_peanut_butter_meals'],
        'tonno_naturale':c1pol['global_variety_targets']['max_tuna_meals'],
        'tacchino':c1pol['global_variety_targets']['max_fresh_turkey_meals'],
        'lupini':c1pol['global_variety_targets']['max_lupin_meals'],
    }
    family_cap=int(c1pol['global_variety_targets']['max_recipe_family_occurrences_180d'])
    dairy_codes=set(c1pol['purchase_reuse']['package_sensitive_dairy']['codes'])

    def family(vid): return versions[vid]['recipe_id']
    def codes(vid): return set(cls[vid]['ingredient_codes'])
    all_no_pkg_dairy=[v for v in all_vids if not (codes(v) & dairy_codes)]
    def current_family_counts(): return Counter(family(e['vid']) for e in entries)
    def current_ing_counts():
        c=Counter()
        for e in entries:
            c.update(codes(e['vid']))
        return c
    def neighbor_exists(code, day, ignore_idx=None, horizon=4):
        for j,e in enumerate(entries):
            if j==ignore_idx: continue
            if abs(e['global_day']-day)<=horizon and code in codes(e['vid']): return True
        return False
    def in_season(vid, month_num):
        title=families[family(vid)]['title']
        if vid in c1_vids and month_num not in spec_months.get(title,{month_num}): return False
        for code in codes(vid):
            allowed=season_map.get(code)
            if allowed is not None and month_num not in allowed: return False
        return True
    def signature_ok(oldvid,candvid,meal_type):
        if meal_type not in MAIN_TYPES: return True
        o=cls[oldvid]; c=cls[candvid]
        if bool(o['plant_protein_main']) != bool(c['plant_protein_main']): return False
        oc=o['primary_carb']; cc=c['primary_carb']
        if oc in {'pasta','rice'}: return cc==oc
        return cc not in {'pasta','rice'}
    def valid(idx,cand):
        e=entries[idx]; old=e['vid']
        if cand==old:return False
        if e['meal_type'] not in set(families[family(cand)].get('meal_types') or []): return False
        if not signature_ok(old,cand,e['meal_type']): return False
        if not in_season(cand,e['month_num']): return False
        # no family repeat inside 7d
        rid=family(cand)
        for j,x in enumerate(entries):
            if j==idx: continue
            if family(x['vid'])==rid and abs(x['global_day']-e['global_day'])<=7:return False
        # day energy and direct daily constraints
        new_energy=day_energy[e['day_index']]-energy(old)+energy(cand); ref=float(refs[e['day_type']])
        if not (0.95*ref-1e-9 <= new_energy <= 1.05*ref+1e-9): return False
        ids=by_day[e['day_index']]
        dairy=sum(1 for j in ids if cls[cand if j==idx else entries[j]['vid']]['dairy_occurrence'])
        eggs=sum(float(cls[cand if j==idx else entries[j]['vid']]['egg_equivalent_units']) for j in ids)
        if dairy>int(hard['cheese_dairy']['max_meals_per_day']): return False
        if eggs>float(soft['egg_daily_spread']['max_equivalent_units_per_day_before_warning'])+1e-9:return False
        # affected 7-day windows
        di=e['day_index']; starts=range(max(0,di-6),min(di,len(by_day)-7)+1)
        for st in starts:
            idxs=[j for dd in range(st,st+7) for j in by_day[dd]]
            def C(j): return cls[cand if j==idx else entries[j]['vid']]
            egg=sum(float(C(j)['egg_equivalent_units']) for j in idxs)
            dairy=sum(1 for j in idxs if C(j)['dairy_occurrence'])
            pr=sum(1 for j in idxs if C(j)['pasta_rice_primary'])
            pasta=sum(1 for j in idxs if C(j)['primary_carb']=='pasta')
            rice=sum(1 for j in idxs if C(j)['primary_carb']=='rice')
            plant=sum(1 for j in idxs if entries[j]['meal_type'] in MAIN_TYPES and C(j)['plant_protein_main'])
            if egg>float(hard['egg_equivalent']['max_per_window'])+1e-9:return False
            if dairy>int(hard['cheese_dairy']['max_meals_per_window']):return False
            if pr<int(hard['pasta_rice']['min_meals_per_window']):return False
            if plant<int(hard['plant_protein_main']['min_meals_per_window']):return False
            if pasta<int(soft['pasta_rice_balance']['min_pasta_primary_meals_per_window']):return False
            if rice<int(soft['pasta_rice_balance']['min_rice_primary_meals_per_window']):return False
            # protein concentration
            pc=Counter(); total=0
            for j in idxs:
                if entries[j]['meal_type'] not in MAIN_TYPES:continue
                g=C(j)['primary_protein']
                if g:pc[g]+=1;total+=1
            if total:
                for g,n in pc.items():
                    if n>=int(soft['primary_protein_concentration']['minimum_occurrences_to_warn']) and n/total>float(soft['primary_protein_concentration']['max_share_in_main_meals_per_window'])+1e-12:return False
            # ingredient concentration
            mc=Counter(); dsets=defaultdict(set)
            for j in idxs:
                cc=C(j)
                for code in set(cc['ingredient_codes']):
                    if code in excluded_conc:continue
                    mc[code]+=1;dsets[code].add(entries[j]['global_day'])
            for code,n in mc.items():
                if n>int(soft['ingredient_concentration']['max_meal_occurrences_per_window']) and len(dsets[code])>=int(soft['ingredient_concentration']['minimum_distinct_days']):return False
        return True
    def apply(idx,cand,reason):
        e=entries[idx];old=e['vid'];day_energy[e['day_index']]+=energy(cand)-energy(old);e['vid']=cand;e['reasons'].append(reason)
    def candidate_score(idx,cand,ing_counts=None,fam_counts=None,focus_code=None):
        e=entries[idx];old=e['vid']; ing_counts=ing_counts or current_ing_counts();fam_counts=fam_counts or current_family_counts()
        oldcodes=codes(old);newcodes=codes(cand);score=0.0
        if fam_counts[family(old)]>family_cap:score+=25+3*(fam_counts[family(old)]-family_cap)
        for code,cap in target_caps.items():
            if code in oldcodes and code not in newcodes and ing_counts[code]>cap:score+=12+2*(ing_counts[code]-cap)
            if code in newcodes and ing_counts[code]>=cap:score-=16
        for code in activation & newcodes:
            if ing_counts[code]<int(c1pol['rotation_activation_targets']['minimum_occurrences_180d']):score+=18+3*(6-ing_counts[code])
        if focus_code and focus_code in newcodes:score+=60
        # reward low-use ingredients and underused protein variety
        for code in newcodes:
            if code not in {'olio','pasta','pasta_integrale','riso_basmati','riso_integrale','riso_jasmine'}:
                score+=min(6.0,12.0/(1+ing_counts[code]))
        for code in {'sardine','cozze','polpo','sgombro','trota','coniglio','maiale_filetto','borlotti','cannellini','fave','lenticchie','piselli'} & newcodes:score+=4
        for code in cluster_codes & newcodes:
            if neighbor_exists(code,e['global_day'],ignore_idx=idx):score+=5
        score-=4*fam_counts[family(cand)]
        new_energy=day_energy[e['day_index']]-energy(old)+energy(cand);ref=float(refs[e['day_type']]);score-=abs(new_energy-ref)/ref*35
        return score
    def choose(idx,candidates=None,focus_code=None):
        candidates=candidates or c1_vids;ingc=current_ing_counts();famc=current_family_counts(); best=None
        for cand in candidates:
            if not valid(idx,cand):continue
            s=candidate_score(idx,cand,ingc,famc,focus_code)
            key=(s,-energy(cand),families[family(cand)]['title'])
            if best is None or key>best[0]:best=(key,cand)
        return best[1] if best else None

    # Pass 1: remove isolated package-sensitive cheese uses. Iterative so remaining uses form clusters.
    changed=True
    while changed:
        changed=False
        for idx,e in list(enumerate(entries)):
            oldcodes=codes(e['vid']); ds=oldcodes & dairy_codes
            if not ds:continue
            isolated=any(not neighbor_exists(code,e['global_day'],ignore_idx=idx,horizon=4) for code in ds)
            if isolated:
                cand=choose(idx)
                if cand:
                    apply(idx,cand,'riuso_acquisti:rimozione_latticino_isolato');changed=True
    # Pass 2: cap overused recipe families.
    safety=0
    while True:
        famc=current_family_counts(); over=[(n,rid) for rid,n in famc.items() if n>family_cap]
        if not over:break
        over.sort(reverse=True);n,rid=over[0];occ=[i for i,e in enumerate(entries) if family(e['vid'])==rid]
        # replace central/excess occurrences first, favour target-heavy meals
        occ.sort(key=lambda i:(-sum(current_ing_counts()[c]-target_caps.get(c,10**9) for c in codes(entries[i]['vid']) if c in target_caps),entries[i]['global_day']))
        done=False
        for idx in occ:
            cand=choose(idx)
            if cand:apply(idx,cand,'varieta:cap_famiglia_180g');done=True;break
        if not done:break
        safety+=1
        if safety>300:break
    # Pass 3: explicit ingredient caps.
    for code,cap in target_caps.items():
        guard=0
        while current_ing_counts()[code]>cap:
            famc=current_family_counts(); choices=[i for i,e in enumerate(entries) if code in codes(e['vid'])]
            choices.sort(key=lambda i:(-famc[family(entries[i]['vid'])], entries[i]['global_day']))
            done=False
            for idx in choices:
                cand=choose(idx,all_no_pkg_dairy)
                if cand and code not in codes(cand):
                    apply(idx,cand,f'varieta:riduzione_{code}');done=True;break
            if not done:break
            guard+=1
            if guard>200:break
    # Pass 4: activate dormant ingredients to at least 6 occurrences.
    for code in sorted(activation):
        guard=0
        while current_ing_counts()[code] < int(c1pol['rotation_activation_targets']['minimum_occurrences_180d']):
            candset=[v for v in c1_vids if code in codes(v)]
            best=None
            # Prefer replacing a meal within 4 days of an existing occurrence to create useful purchase clusters.
            existing_days=[e['global_day'] for e in entries if code in codes(e['vid'])]
            for idx,e in enumerate(entries):
                if code in codes(e['vid']):continue
                if not valid(idx, candset[0]) and len(candset)==1: continue
                cand=choose(idx,candset,focus_code=code)
                if not cand:continue
                near=min((abs(e['global_day']-d) for d in existing_days),default=99)
                s=candidate_score(idx,cand,focus_code=code)+(15 if near<=4 else 0)-(3 if near>7 and existing_days else 0)
                key=(s,-near,-e['global_day'])
                if best is None or key>best[0]:best=(key,idx,cand)
            if not best:break
            _,idx,cand=best;apply(idx,cand,f'varieta:attivazione_{code}')
            guard+=1
            if guard>20:break
    # Pass 5: improve purchase clustering for fresh/open-pack target codes where possible.
    horizon=int(c1pol['purchase_reuse']['reuse_horizon_days'])
    for code in sorted(cluster_codes & activation):
        for _ in range(10):
            occ=[(i,e['global_day']) for i,e in enumerate(entries) if code in codes(e['vid'])]
            unpaired=[(i,d) for i,d in occ if not any(j!=i and abs(d-d2)<=horizon for j,d2 in occ)]
            if not unpaired:break
            # add a different C1 recipe using the code near an unpaired occurrence
            target_idx,target_day=unpaired[0]; candset=[v for v in c1_vids if code in codes(v) and family(v)!=family(entries[target_idx]['vid'])]
            best=None
            for idx,e in enumerate(entries):
                if idx==target_idx or abs(e['global_day']-target_day)>horizon or code in codes(e['vid']):continue
                cand=choose(idx,candset,focus_code=code)
                if not cand:continue
                dist=abs(e['global_day']-target_day);key=(-dist,candidate_score(idx,cand,focus_code=code),-e['global_day'])
                if best is None or key>best[0]:best=(key,idx,cand)
            if not best:break
            _,idx,cand=best;apply(idx,cand,f'riuso_acquisti:cluster_{code}')

    # Pass 6: one more family-cap cleanup after activation/cluster additions.
    for _ in range(200):
        famc=current_family_counts(); over=[(n,r) for r,n in famc.items() if n>family_cap]
        if not over:break
        n,rid=max(over);done=False
        for idx in [i for i,e in enumerate(entries) if family(e['vid'])==rid]:
            cand=choose(idx)
            if cand:apply(idx,cand,'varieta:cap_famiglia_finale');done=True;break
        if not done:break

    # Pass 7: final purchase-aware dairy cleanup after all variety replacements.
    # Earlier passes can change neighborhood availability, so re-evaluate isolation here.
    for _ in range(80):
        progress=False; remaining=False
        for idx,e in enumerate(entries):
            ds=codes(e['vid']) & dairy_codes
            if not ds or not any(not neighbor_exists(code,e['global_day'],ignore_idx=idx,horizon=4) for code in ds):
                continue
            remaining=True
            cand=choose(idx,all_no_pkg_dairy)
            if cand:
                apply(idx,cand,'riuso_acquisti:rimozione_latticino_isolato_finale'); progress=True; break
        if not remaining or not progress: break

    # Pass 8: final family-cap cleanup after dairy replacements.
    for _ in range(100):
        famc=current_family_counts(); over=[(n,r) for r,n in famc.items() if n>family_cap]
        if not over: break
        n,rid=max(over); done=False
        for idx in [i for i,e in enumerate(entries) if family(e['vid'])==rid]:
            cand=choose(idx)
            if cand:
                apply(idx,cand,'varieta:cap_famiglia_post_dairy'); done=True; break
        if not done: break


    # Pass 9: final global cap repair using the full catalog, not only C1 recipes.
    for _ in range(300):
        ingc=current_ing_counts(); over=[(ingc[c]-cap,c,cap) for c,cap in target_caps.items() if ingc[c]>cap]
        if not over: break
        _,code,cap=max(over); done=False
        famc=current_family_counts(); choices=[i for i,e in enumerate(entries) if code in codes(e['vid'])]
        choices.sort(key=lambda i:(-famc[family(entries[i]['vid'])], entries[i]['global_day']))
        for idx in choices:
            cand=choose(idx,all_no_pkg_dairy)
            if cand and code not in codes(cand):
                # Do not fix one cap by worsening another already-at-cap ingredient.
                oldc=codes(entries[idx]['vid']); newc=codes(cand); now=current_ing_counts()
                if any(c in newc-oldc and now[c]>=target_caps[c] for c in target_caps):
                    continue
                apply(idx,cand,f'varieta:cap_finale_{code}'); done=True; break
        if not done: break

    # Pass 10: final activation repair for underused ingredients, using all compatible recipes.
    for code in sorted(activation):
        for _ in range(20):
            if current_ing_counts()[code] >= int(c1pol['rotation_activation_targets']['minimum_occurrences_180d']): break
            candset=[v for v in all_no_pkg_dairy if code in codes(v)]
            best=None
            for idx,e in enumerate(entries):
                if code in codes(e['vid']): continue
                cand=choose(idx,candset,focus_code=code)
                if not cand: continue
                existing=[x['global_day'] for x in entries if code in codes(x['vid'])]
                near=min((abs(e['global_day']-d) for d in existing),default=99)
                key=((12 if near<=4 else 0)+candidate_score(idx,cand,focus_code=code),-near,-e['global_day'])
                if best is None or key>best[0]: best=(key,idx,cand)
            if not best: break
            _,idx,cand=best; apply(idx,cand,f'varieta:attivazione_finale_{code}')

    # Pass 11: remove any package-sensitive dairy that became isolated after final repairs.
    for _ in range(100):
        progress=False
        for idx,e in enumerate(entries):
            ds=codes(e['vid']) & dairy_codes
            if ds and any(not neighbor_exists(code,e['global_day'],ignore_idx=idx,horizon=4) for code in ds):
                cand=choose(idx,all_no_pkg_dairy)
                if cand and not (codes(cand)&dairy_codes):
                    apply(idx,cand,'riuso_acquisti:rimozione_latticino_isolato_finalissimo'); progress=True; break
        if not progress: break

    # Pass 12: final family-cap cleanup after all repairs.
    for _ in range(200):
        famc=current_family_counts(); over=[(n,r) for r,n in famc.items() if n>family_cap]
        if not over: break
        n,rid=max(over); done=False
        for idx in [i for i,e in enumerate(entries) if family(e['vid'])==rid]:
            cand=choose(idx,c1_vids)
            if cand:
                apply(idx,cand,'varieta:cap_famiglia_chiusura'); done=True; break
        if not done: break

    # Build explicit curation object.
    days=[];changed_meals=0;changed_days=0
    for di,d in enumerate(base_plan['days']):
        ms=[]; day_changed=0
        for idx in by_day[di]:
            e=entries[idx]; orig=e['original_vid'];sel=e['vid']; ch=orig!=sel;changed_meals+=int(ch);day_changed+=int(ch)
            ms.append({'meal_id':e['meal_id'],'meal_type':e['meal_type'],'time':e['time'],'original_recipe_version_id':orig,'selected_recipe_version_id':sel,'selected_recipe_title':families[family(sel)]['title'],'changed':ch,'reasons':e['reasons'] or ['conservato_phase_c']})
        changed_days+=int(day_changed>0)
        eggs=sum(cls[entries[i]['vid']]['egg_equivalent_units'] for i in by_day[di]);dairy=sum(cls[entries[i]['vid']]['dairy_occurrence'] for i in by_day[di]);pr=sum(cls[entries[i]['vid']]['pasta_rice_primary'] for i in by_day[di]);plant=sum(entries[i]['meal_type'] in MAIN_TYPES and cls[entries[i]['vid']]['plant_protein_main'] for i in by_day[di]);ref=float(refs[d['day_type']])
        days.append({'global_day':int(d['base_global_day']),'month':d['month'],'day_type':d['day_type'],'review_status':'approved_c1','changed_meals':day_changed,'energy_kcal':round(day_energy[di],1),'energy_reference_kcal':ref,'energy_delta_pct':round((day_energy[di]-ref)/ref,4),'egg_equivalent_units':round(eggs,2),'dairy_meals':int(dairy),'pasta_rice_primary_meals':int(pr),'plant_protein_main_meals':int(plant),'meals':ms})
    out={'format':'tatadiet-v6-phase-c1-curation','schema_version':1,'dataset_version':'tatadiet-base-v2','policy_version':c1pol['policy_version'],'generated_at':STAMP,'methodology':{'base_plan_sha256':sha(PLAN),'approach':'deterministic one-shot editorial curation assisted by constraint-preserving local search; result is frozen explicitly and does not depend on runtime heuristics','signature_preservation':'Main-meal plant status and pasta/rice primary-carb class are preserved during replacements to protect rolling hard constraints.','shopping_reuse':'Isolated package-sensitive dairy is removed where possible; dormant ingredients are activated in reusable clusters.'},'summary':{'days':180,'meals':len(entries),'changed_days_vs_phase_c':changed_days,'changed_meals_vs_phase_c':changed_meals,'preserved_meals_vs_phase_c':len(entries)-changed_meals,'c1_recipe_occurrences':sum(str(family(e['vid'])).startswith('base:recipe:v6c1-') for e in entries)},'days':days}
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    # diagnostics
    ingc=current_ing_counts();famc=current_family_counts();
    print(json.dumps({'status':'ok','changed_meals':changed_meals,'changed_days':changed_days,'c1_occurrences':out['summary']['c1_recipe_occurrences'],'max_family':max(famc.values()),'target_counts':{k:ingc[k] for k in target_caps},'activation_counts':{k:ingc[k] for k in sorted(activation)}},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
