#!/usr/bin/env python3
from __future__ import annotations
import hashlib, importlib.util, json, sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POL_A = ROOT / 'spec/v6/phase-a-policy.json'
POL_C1 = ROOT / 'spec/v6/phase-c1-policy.json'
POL_C2 = ROOT / 'spec/v6/phase-c2-policy.json'
REC_C2 = ROOT / 'spec/v6/phase-c2-recipes.json'
PLAN = ROOT / 'v5_data/base/plan-template.base.v1.json'
RECIPES = ROOT / 'v5_data/base/recipes.base.v1.json'
INGREDIENTS = ROOT / 'v5_data/base/ingredients.base.v1.json'
OUT = ROOT / 'spec/v6/phase-c2-curation.json'
STAMP = '2026-09-08T14:45:00+02:00'
ELIGIBLE_TARGET_TYPES = {'Colazione','Spuntino','Spuntino notturno','Mini-pasto pre-sonno'}
MAIN_TYPES = {'Pranzo','Cena','Brunch','Pasto preturno'}


def load(p): return json.loads(p.read_text(encoding='utf-8'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def audit_mod():
    sp = importlib.util.spec_from_file_location('audit_v6_c2_base', ROOT / 'scripts/audit_v6_phase_a.py')
    m = importlib.util.module_from_spec(sp); sys.modules['audit_v6_c2_base'] = m; sp.loader.exec_module(m); return m


def main():
    audit = audit_mod()
    plan = load(PLAN); rec = load(RECIPES); ing = load(INGREDIENTS); pa = load(POL_A); pc1 = load(POL_C1); pc2 = load(POL_C2); rspec = load(REC_C2)
    ds = audit.load_dataset(POL_A, PLAN, RECIPES, INGREDIENTS)
    cls = {v['id']: audit.classify_recipe(v, ds) for v in rec['recipe_versions']}
    versions = {v['id']: v for v in rec['recipe_versions']}; families = {f['id']: f for f in rec['recipe_families']}
    dairy_codes = set(pc2['counted_dairy']['included_codes']); avocado_code = pc2['avocado']['ingredient_code']
    activation = set(pc1['rotation_activation_targets']['ingredient_codes'])
    caps_cfg = pc1['global_variety_targets']
    cap_map = {
        'banana':caps_cfg['max_banana_meals'],'carota':caps_cfg['max_carrot_meals'],'spinaci':caps_cfg['max_spinach_meals'],
        'zucca':caps_cfg['max_pumpkin_meals'],'hummus':caps_cfg['max_hummus_meals'],'salmone':caps_cfg['max_salmon_meals'],
        'bresaola':caps_cfg['max_bresaola_meals'],'tacchino_affettato':caps_cfg['max_sliced_turkey_meals'],
        'burro_arachidi':caps_cfg['max_peanut_butter_meals'],'tonno_naturale':caps_cfg['max_tuna_meals'],
        'tacchino':caps_cfg['max_fresh_turkey_meals'],'lupini':caps_cfg['max_lupin_meals']}
    family_cap = int(caps_cfg['max_recipe_family_occurrences_180d'])
    refs = pa['energy_diagnostics']['reference_kcal_by_day_type']
    hard = pa['hard_constraints']; soft = pa['soft_constraints']
    season_map = {c:set(ms) for c,ms in soft['seasonality']['fresh_ingredient_months'].items()}
    excluded_conc = set(soft['ingredient_concentration']['excluded_codes'])

    entries=[]; by_day=[[] for _ in plan['days']]
    for di,d in enumerate(plan['days']):
        for mi,m in enumerate(d['meals']):
            e={'day_index':di,'global_day':int(d['base_global_day']),'month':d['month'],'month_num':audit.MONTH_NUMBERS[d['month']],
               'day_type':d['day_type'],'meal_index':mi,'meal_id':m['id'],'meal_type':m['meal_type'],'time':m['time'],
               'original_vid':m['recipe_version_id'],'vid':m['recipe_version_id'],'reasons':[]}
            idx=len(entries); entries.append(e); by_day[di].append(idx)

    def family(vid): return versions[vid]['recipe_id']
    def codes(vid): return set(cls[vid]['ingredient_codes'])
    def energy(vid): return float(versions[vid]['nutrition']['values_per_serving']['energy_kcal'])
    day_energy=[sum(energy(entries[i]['vid']) for i in ids) for ids in by_day]
    def fam_counts(): return Counter(family(e['vid']) for e in entries)
    def ing_counts():
        c=Counter()
        for e in entries: c.update(codes(e['vid']))
        return c
    def in_season(vid, month_num):
        for code in codes(vid):
            allowed=season_map.get(code)
            if allowed is not None and month_num not in allowed: return False
        return True
    def signature_ok(oldvid,candvid,meal_type):
        if meal_type not in MAIN_TYPES: return True
        o,c=cls[oldvid],cls[candvid]
        if bool(o['plant_protein_main']) != bool(c['plant_protein_main']): return False
        oc,cc=o['primary_carb'],c['primary_carb']
        if oc in {'pasta','rice'}: return cc==oc
        return cc not in {'pasta','rice'}

    def valid(idx,cand,allow_dairy=True,allow_avocado=True):
        e=entries[idx]; old=e['vid']
        if cand==old: return False
        if e['meal_type'] not in set(families[family(cand)].get('meal_types') or []): return False
        if not signature_ok(old,cand,e['meal_type']): return False
        if not in_season(cand,e['month_num']): return False
        if not allow_dairy and cls[cand]['dairy_occurrence']: return False
        if not allow_avocado and avocado_code in codes(cand): return False
        rid=family(cand)
        for j,x in enumerate(entries):
            if j!=idx and family(x['vid'])==rid and abs(x['global_day']-e['global_day'])<=7: return False
        fc=fam_counts(); new_count=fc[rid]+(0 if family(old)==rid else 1)
        if new_count>family_cap: return False
        new_energy=day_energy[e['day_index']]-energy(old)+energy(cand); ref=float(refs[e['day_type']])
        if not (0.95*ref-1e-9 <= new_energy <= 1.05*ref+1e-9): return False
        ids=by_day[e['day_index']]
        dairy=sum(1 for j in ids if cls[cand if j==idx else entries[j]['vid']]['dairy_occurrence'])
        eggs=sum(float(cls[cand if j==idx else entries[j]['vid']]['egg_equivalent_units']) for j in ids)
        if dairy>1: return False
        if eggs>float(soft['egg_daily_spread']['max_equivalent_units_per_day_before_warning'])+1e-9: return False
        di=e['day_index']
        for st in range(max(0,di-6), min(di,len(by_day)-7)+1):
            idxs=[j for dd in range(st,st+7) for j in by_day[dd]]
            def C(j): return cls[cand if j==idx else entries[j]['vid']]
            egg=sum(float(C(j)['egg_equivalent_units']) for j in idxs)
            dairy_n=sum(1 for j in idxs if C(j)['dairy_occurrence'])
            pr=sum(1 for j in idxs if C(j)['pasta_rice_primary'])
            pasta=sum(1 for j in idxs if C(j)['primary_carb']=='pasta')
            rice=sum(1 for j in idxs if C(j)['primary_carb']=='rice')
            plant=sum(1 for j in idxs if entries[j]['meal_type'] in MAIN_TYPES and C(j)['plant_protein_main'])
            if egg>float(hard['egg_equivalent']['max_per_window'])+1e-9: return False
            if dairy_n>int(pc2['counted_dairy']['max_meals_per_rolling_7d']): return False
            if pr<int(hard['pasta_rice']['min_meals_per_window']): return False
            if plant<int(hard['plant_protein_main']['min_meals_per_window']): return False
            if pasta<int(soft['pasta_rice_balance']['min_pasta_primary_meals_per_window']): return False
            if rice<int(soft['pasta_rice_balance']['min_rice_primary_meals_per_window']): return False
            pc=Counter(); total=0
            for j in idxs:
                if entries[j]['meal_type'] not in MAIN_TYPES: continue
                g=C(j)['primary_protein']
                if g: pc[g]+=1; total+=1
            if total:
                for g,n in pc.items():
                    if n>=int(soft['primary_protein_concentration']['minimum_occurrences_to_warn']) and n/total>float(soft['primary_protein_concentration']['max_share_in_main_meals_per_window'])+1e-12: return False
            mc=Counter(); dsets=defaultdict(set)
            for j in idxs:
                for code in set(C(j)['ingredient_codes']):
                    if code in excluded_conc: continue
                    mc[code]+=1; dsets[code].add(entries[j]['global_day'])
            for code,n in mc.items():
                if n>int(soft['ingredient_concentration']['max_meal_occurrences_per_window']) and len(dsets[code])>=int(soft['ingredient_concentration']['minimum_distinct_days']): return False
        # Do not exceed C1 global caps.
        oldcodes,newcodes=codes(old),codes(cand); now=ing_counts()
        for code,cap in cap_map.items():
            projected=now[code] + (1 if code in newcodes and code not in oldcodes else 0) - (1 if code in oldcodes and code not in newcodes else 0)
            if projected>cap: return False
        return True

    def score(idx,cand):
        e=entries[idx]; old=e['vid']; ref=float(refs[e['day_type']]); newe=day_energy[e['day_index']]-energy(old)+energy(cand)
        fc=fam_counts(); ic=ing_counts(); oldc,newc=codes(old),codes(cand)
        s=-abs(newe-ref)*2.0 - fc[family(cand)]*2.0
        for code in activation:
            if code in oldc and code not in newc:
                s -= 80 if ic[code]<=6 else 25 if ic[code]<=8 else 5
        # Prefer replacing already-common family/ingredients rather than rare activated ones.
        s += max(0,fc[family(old)]-6)*3
        return s

    def choose_from_day(day_index,candidates,allow_dairy=True,allow_avocado=True,required_indices=None):
        best=None
        allowed_indices=set(required_indices) if required_indices is not None else None
        for idx in by_day[day_index]:
            if allowed_indices is not None and idx not in allowed_indices: continue
            if entries[idx]['meal_type'] not in ELIGIBLE_TARGET_TYPES: continue
            for cand in candidates:
                if not valid(idx,cand,allow_dairy,allow_avocado): continue
                key=(score(idx,cand), -abs(energy(cand)-energy(entries[idx]['vid'])), -idx)
                if best is None or key>best[0]: best=(key,idx,cand)
        return best[1:] if best else None

    def choose_nondairy(idx):
        pool=[]
        for v in versions.values():
            vid=v['id']
            if cls[vid]['dairy_occurrence'] or avocado_code in codes(vid): continue
            if entries[idx]['meal_type'] not in set(families[family(vid)].get('meal_types') or []): continue
            pool.append(vid)
        best=None
        for cand in pool:
            if valid(idx,cand,allow_dairy=False,allow_avocado=False):
                key=(score(idx,cand),-abs(energy(cand)-energy(entries[idx]['vid'])))
                if best is None or key>best[0]: best=(key,cand)
        return best[1] if best else None

    def apply(idx,cand,reason):
        old=entries[idx]['vid']; day_energy[entries[idx]['day_index']]+=energy(cand)-energy(old); entries[idx]['vid']=cand; entries[idx]['reasons'].append(reason)

    dairy_positions=set(pc2['counted_dairy']['weekly_pattern_positions'])
    avo_positions=set(pc2['avocado']['weekly_pattern_positions'])
    # 1) Clear counted dairy only where it cannot be directly overwritten by the new pattern.
    # Existing dairy in an eligible target slot is retained temporarily and replaced in-place.
    for idx,e in enumerate(entries):
        if not cls[e['vid']]['dairy_occurrence']:
            continue
        pos=(e['global_day']-1)%7+1
        if e['meal_type'] in ELIGIBLE_TARGET_TYPES and pos in dairy_positions:
            continue
        if e['meal_type'] in ELIGIBLE_TARGET_TYPES and pos in avo_positions:
            cand=choose_nondairy(idx)
            if cand:
                apply(idx,cand,'c2:latticini:rimozione_prima_di_avocado')
            # If no neutral replacement is feasible, avocado will replace this dairy in-place.
            continue
        cand=choose_nondairy(idx)
        if not cand: raise RuntimeError(f'cannot clear dairy from {e["meal_id"]}')
        apply(idx,cand,'c2:latticini:rimozione_pattern_precedente')

    # Build C2 candidate maps.
    c2vids=[v['id'] for v in versions.values() if str(v['recipe_id']).startswith('base:recipe:v6c2-')]
    dairy_by_code=defaultdict(list); avo=[]
    for vid in c2vids:
        cs=codes(vid)
        if avocado_code in cs: avo.append(vid)
        for code in dairy_codes & cs: dairy_by_code[code].append(vid)
    for arr in dairy_by_code.values(): arr.sort(key=lambda x:(energy(x),families[family(x)]['title']))
    avo.sort(key=lambda x:(energy(x),families[family(x)]['title']))

    pair_rotation=pc2['counted_dairy']['fresh_pair_rotation']
    # 2) Insert exact patterned avocado servings.
    for di,d in enumerate(plan['days']):
        g=int(d['base_global_day']); pos=(g-1)%7+1
        if pos not in avo_positions: continue
        dairy_idxs=[idx for idx in by_day[di] if cls[entries[idx]['vid']]['dairy_occurrence']]
        choice=choose_from_day(di,avo,allow_dairy=False,allow_avocado=True,required_indices=dairy_idxs or None)
        if not choice: raise RuntimeError(f'cannot place avocado on day {g}')
        idx,cand=choice; apply(idx,cand,f'c2:avocado:75g:pos{pos}')

    # 3) Insert exact patterned dairy servings. The two fresh servings in each 7-day block
    # use the same dairy type to close a plausible package; the type is selected jointly
    # for both days, with a rotating preference to keep semester-wide variety.
    pair_use=Counter()
    for week in range((len(plan['days'])+6)//7):
        g1=week*7+1; g4=week*7+4
        if g1>len(plan['days']): break
        d1=g1-1; d4=g4-1 if g4<=len(plan['days']) else None
        order=list(pair_rotation[week % len(pair_rotation):])+list(pair_rotation[:week % len(pair_rotation)])
        pref_rank={c:i for i,c in enumerate(order)}
        order.sort(key=lambda c:(pair_use[c], pref_rank[c]))
        placed=False
        for code in order:
            choice1=choose_from_day(d1,dairy_by_code[code],allow_dairy=True,allow_avocado=False)
            if not choice1: continue
            idx1,cand1=choice1; old1=entries[idx1]['vid']; oldr1=list(entries[idx1]['reasons']); olde1=day_energy[d1]
            apply(idx1,cand1,f'c2:latticini:{code}:pos1')
            if d4 is None:
                pair_use[code]+=1; placed=True; break
            choice4=choose_from_day(d4,dairy_by_code[code],allow_dairy=True,allow_avocado=False)
            if choice4:
                idx4,cand4=choice4; apply(idx4,cand4,f'c2:latticini:{code}:pos4'); pair_use[code]+=2; placed=True; break
            entries[idx1]['vid']=old1; entries[idx1]['reasons']=oldr1; day_energy[d1]=olde1
        if not placed:
            raise RuntimeError(f'cannot place paired fresh dairy in week {week+1} days {g1}/{g4}')
    # Third weekly portion: storage-flexible Grana on position 6.
    for week in range((len(plan['days'])+6)//7):
        g=week*7+6
        if g>len(plan['days']): continue
        di=g-1
        choice=choose_from_day(di,dairy_by_code['grana'],allow_dairy=True,allow_avocado=False)
        if not choice: raise RuntimeError(f'cannot place grana on day {g}')
        idx,cand=choice; apply(idx,cand,'c2:latticini:grana:pos6')

    # Build curation contract.
    days=[]; changed_meals=0; changed_days=0
    for di,d in enumerate(plan['days']):
        ms=[]; dc=0
        for idx in by_day[di]:
            e=entries[idx]; ch=e['vid']!=e['original_vid']; changed_meals+=int(ch); dc+=int(ch)
            ms.append({'meal_id':e['meal_id'],'meal_type':e['meal_type'],'time':e['time'],'original_recipe_version_id':e['original_vid'],
                       'selected_recipe_version_id':e['vid'],'selected_recipe_title':families[family(e['vid'])]['title'],'changed':ch,
                       'reasons':e['reasons'] or ['conservato_phase_c1']})
        changed_days += int(dc>0)
        dairies=[]; avos=0
        for idx in by_day[di]:
            cs=codes(entries[idx]['vid']); dairies.extend(sorted(cs & dairy_codes)); avos += int(avocado_code in cs)
        ref=float(refs[d['day_type']])
        days.append({'global_day':int(d['base_global_day']),'month':d['month'],'day_type':d['day_type'],'review_status':'approved_c2',
                     'changed_meals':dc,'energy_kcal':round(day_energy[di],2),'energy_reference_kcal':ref,
                     'energy_delta_pct':round((day_energy[di]-ref)/ref,4),'dairy_meals':len(dairies),'dairy_types':dairies,
                     'avocado_portions':avos,'meals':ms})
    out={'format':'tatadiet-v6-phase-c2-curation','schema_version':1,'dataset_version':'tatadiet-base-v2','policy_version':pc2['policy_version'],
         'generated_at':STAMP,'methodology':{'base_plan_sha256':sha(PLAN),'approach':'deterministic editorial overlay on the approved C1 baseline',
         'dairy_pattern':'positions 1,4,6 in each repeating 7-day block; positions 1 and 4 reuse the same fresh dairy type, position 6 uses storage-flexible Grana',
         'avocado_pattern':'positions 2 and 5 in each repeating 7-day block, 75 g each; this yields exactly two portions in every rolling 7-day window and a 150 g purchase pair within 4 days'},
         'summary':{'days':180,'meals':len(entries),'changed_days_vs_phase_c1':changed_days,'changed_meals_vs_phase_c1':changed_meals,
                    'preserved_meals_vs_phase_c1':len(entries)-changed_meals,'c2_recipe_occurrences':sum(family(e['vid']).startswith('base:recipe:v6c2-') for e in entries)},'days':days}
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':'ok','changed_days':changed_days,'changed_meals':changed_meals,'c2_occurrences':out['summary']['c2_recipe_occurrences'],
                      'final_dairy_meals':sum(d['dairy_meals'] for d in days),'final_avocado_meals':sum(d['avocado_portions'] for d in days)},indent=2))

if __name__=='__main__': main()
