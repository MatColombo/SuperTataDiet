#!/usr/bin/env python3
from __future__ import annotations
import csv,json
from collections import Counter,defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'qa/v6-phase-c1'
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def wcsv(p,fields,rows):
    with p.open('w',newline='',encoding='utf-8-sig') as h:
        w=csv.DictWriter(h,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows)
def main():
    cur=load(ROOT/'spec/v6/phase-c1-curation.json');rec=load(ROOT/'v5_data/base/recipes.base.v1.json');rs=load(ROOT/'spec/v6/phase-c1-recipes.json');ver={v['id']:v for v in rec['recipe_versions']};fam={f['id']:f for f in rec['recipe_families']}
    before_i=Counter();after_i=Counter();before_f=Counter();after_f=Counter();before_s=defaultdict(set);after_s=defaultdict(set)
    for d in cur['days']:
        for m in d['meals']:
            for key,fc,ic,sc in [('original_recipe_version_id',before_f,before_i,before_s),('selected_recipe_version_id',after_f,after_i,after_s)]:
                v=ver[m[key]];fc[v['recipe_id']]+=1;sc[m['meal_type']].add(v['recipe_id']);ic.update({x['ingredient_code'] for x in v['ingredient_lines']})
    focus=['banana','pera','mela','carota','spinaci','zucca','hummus','ceci','lenticchie','cannellini','borlotti','piselli','fave','lupini','salmone','tonno_naturale','sgombro','trota','sardine','cozze','polpo','bresaola','tacchino_affettato','tacchino','pollo','manzo_magro','maiale_filetto','coniglio','burro_arachidi','barbabietola','castagna','cavoletti','cicoria','gnocchi','indivia','mais','patata_dolce','rapa','semi_zucca','tortilla']
    rows=[{'metric':'ingredient','key':c,'phase_c':before_i[c],'phase_c1':after_i[c],'delta':after_i[c]-before_i[c]} for c in focus]
    rows += [{'metric':'global','key':'recipe_families_used','phase_c':len(before_f),'phase_c1':len(after_f),'delta':len(after_f)-len(before_f)},{'metric':'global','key':'max_family_occurrences','phase_c':max(before_f.values()),'phase_c1':max(after_f.values()),'delta':max(after_f.values())-max(before_f.values())}]
    for mt in sorted(set(before_s)|set(after_s)):
        rows.append({'metric':'slot_families','key':mt,'phase_c':len(before_s[mt]),'phase_c1':len(after_s[mt]),'delta':len(after_s[mt])-len(before_s[mt])})
    wcsv(OUT/'comparison-phase-c-vs-c1.csv',['metric','key','phase_c','phase_c1','delta'],rows)
    # New recipe inventory.
    vids={fam[v['recipe_id']]['title']:v for v in rec['recipe_versions'] if str(v['recipe_id']).startswith('base:recipe:v6c1-')}
    nr=[]
    for r in rs['recipes']:
        v=vids[r['title']];n=v['nutrition']['values_per_serving'];nr.append({'title':r['title'],'role':r['role'],'meal_types':' | '.join(r['meal_types']),'ingredients':' | '.join(f"{x['code']} {x['quantity']}g" for x in r['ingredients']),'season_months':','.join(map(str,r['season_months'])),'kcal':round(float(n['energy_kcal']),1),'protein_g':round(float(n['protein_g']),1),'fiber_g':round(float(n['fiber_g']),1),'curated_occurrences':int(v.get('curated_occurrence_count') or 0)})
    wcsv(OUT/'new-recipes.csv',list(nr[0]),nr)
    print(json.dumps({'status':'ok','comparison_rows':len(rows),'new_recipes':len(nr)},indent=2))
if __name__=='__main__':main()
