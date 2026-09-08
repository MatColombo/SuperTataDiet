#!/usr/bin/env python3
"""Add the small Phase C targeted recipe tranche to the already-built Phase B catalog."""
from __future__ import annotations
import argparse, hashlib, json, re, unicodedata
from pathlib import Path
from typing import Any
ROOT=Path(__file__).resolve().parents[1]
SPEC=ROOT/'spec/v6/phase-c-recipes.json'; RECIPES=ROOT/'v5_data/base/recipes.base.v1.json'; INGREDIENTS=ROOT/'v5_data/base/ingredients.base.v1.json'; MANIFEST=ROOT/'v5_data/base/base-dataset-manifest.json'
PREFIX='v6c-'; STAMP='2026-09-08T09:00:00+00:00'
def load(p): return json.loads(p.read_text(encoding='utf-8'))
def dump(p,x): p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def slugify(v): return re.sub(r'[^a-z0-9]+','-',unicodedata.normalize('NFKD',v).encode('ascii','ignore').decode().lower()).strip('-')
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def token(d): return hashlib.sha256(json.dumps({'title':d['title'],'ingredients':d['ingredients']},ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()[:16]
def nutrition(d,ib):
 out={k:0.0 for k in ['energy_kcal','protein_g','carbohydrate_g','fat_g','fiber_g']}
 for z in d['ingredients']:
  i=ib[z['code']]; f=float(z['quantity'])/float((i.get('nutrition_basis') or {}).get('amount') or 100)
  for k in out: out[k]+=f*float((i.get('nutrients') or {}).get(k) or 0)
 return {k:round(v,4) for k,v in out.items()}
def lines(d,ib):
 out=[]
 for z in d['ingredients']:
  i=ib[z['code']]; q=float(z['quantity']); q=int(q) if q.is_integer() else q; u=(i.get('nutrition_basis') or {}).get('unit') or 'g'
  out.append({'ingredient_id':i['id'],'ingredient_revision_id':i['revision_id'],'ingredient_code':i['code'],'label':i['name'],'quantity':q,'unit':u,'base_quantity':q,'base_unit':u,'conversion_id':None,'preparation_note':None,'source_text':f"{i['name']} {q} {u}"})
 return out
def build(spec_path=SPEC,recipes_path=RECIPES,ingredients_path=INGREDIENTS,manifest_path=MANIFEST):
 spec=load(spec_path); r=load(recipes_path); ing=load(ingredients_path); man=load(manifest_path); ib={x['code']:x for x in ing['ingredients']}
 r['recipe_families']=[x for x in r['recipe_families'] if not str(x.get('slug','')).startswith(PREFIX)]
 r['recipe_versions']=[x for x in r['recipe_versions'] if not str(x.get('recipe_id','')).startswith('base:recipe:'+PREFIX)]
 titles={x['title'] for x in r['recipe_families']}; slugs={x['slug'] for x in r['recipe_families']}; cf=[]; cv=[]
 for d in spec['recipes']:
  if d['title'] in titles: raise ValueError('duplicate title '+d['title'])
  if any(z['code'] not in ib for z in d['ingredients']): raise ValueError('missing ingredient '+d['title'])
  slug=PREFIX+slugify(d['title']); rid='base:recipe:'+slug; vid='base:recipe-version:'+slug+':'+token(d); ls=lines(d,ib); n=nutrition(d,ib)
  fam={'id':rid,'slug':slug,'title':d['title'],'description':'Ricetta V6 aggiunta durante la curation dei 180 giorni: porzione fissa.','origin':'base','immutable':True,'status':'active','meal_types':d['meal_types'],'cuisines':[d['cuisine']],'version_ids':[vid],'instructions_status':'available','default_version_id':vid}
  ver={'id':vid,'recipe_id':rid,'revision':1,'servings':1.0,'servings_source':'explicit','origin':'base','immutable':True,'status':'active','composition_status':'structured','ingredient_lines':ls,'source_ingredient_text':'; '.join(x['source_text'] for x in ls),'nutrition':{'mode':'calculated_from_ingredients','values_per_serving':n,'source_values_per_serving':{k:round(v,1) for k,v in n.items()},'rounded_match_to_source':True,'calculation_version':'v6-phase-c-1'},'prep_minutes':int(d['prep_minutes']),'meal_prep':{'prepare_ahead':'Sì, 1 giorno prima','cold':'Possibile; preferibile tiepido','reheat':'Facoltativo, 1-2 min','fridge':'2 giorni'},'cuisine':d['cuisine'],'spices':d.get('spices','Nessuna'),'instructions':['Cuoci la fonte di carboidrati nella quantità indicata.','Cuoci separatamente la componente proteica e le verdure con una preparazione semplice.','Unisci gli ingredienti con l’olio previsto e servi l’intera porzione.'],'instructions_status':'available','practical_notes':'V6 Phase C · brunch completo per la curation del semestre · porzione fissa.','editable_ingredient_composition':True,'source_occurrence_ids':[],'source_occurrence_count':0}
  cf.append(fam);cv.append(ver);titles.add(d['title']);slugs.add(slug)
 r['recipe_families']+=cf;r['recipe_versions']+=cv;r['recipe_families'].sort(key=lambda x:x['title'].casefold());r['recipe_versions'].sort(key=lambda x:(x['recipe_id'],x.get('revision',1),x['id']));r['generated_at']=STAMP
 ext=r.setdefault('catalog_extensions',{});ext['v6_phase_b']=r.get('catalog_extension');ext['v6_phase_c']={'version':spec['policy_version'],'source':'spec/v6/phase-c-recipes.json','fixed_portions_only':True,'families_added':len(cf),'recipe_versions_added':len(cv)};r['catalog_extension']=ext['v6_phase_c'];dump(recipes_path,r)
 man['generated_at']=STAMP;man.setdefault('extensions',{})['v6_phase_c']={'version':spec['policy_version'],'source':'spec/v6/phase-c-recipes.json','source_sha256':sha(spec_path),'note':'Targeted fixed-portion recipes added during the one-shot 180-day curation.'};man['files']['recipes.base.v1.json']={'sha256':sha(recipes_path),'recipe_families':len(r['recipe_families']),'recipe_versions':len(r['recipe_versions'])};dump(manifest_path,man)
 return {'families_added':len(cf),'versions_added':len(cv),'family_total':len(r['recipe_families']),'version_total':len(r['recipe_versions'])}
if __name__=='__main__': print(json.dumps(build(),ensure_ascii=False,indent=2))
