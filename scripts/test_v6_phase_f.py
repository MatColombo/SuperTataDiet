#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def load(p): return json.loads((ROOT/p).read_text(encoding='utf-8'))
def sha(p): return hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
def main():
    policy=load('spec/v6/phase-f-policy.json'); manifest=load('v5_data/base/base-dataset-manifest.json')
    assert policy['policy_version']=='6.0.0-phase-f.1'
    assert policy['recipe_converter']['mode']=='read-only' and policy['recipe_converter']['writes_recipe_or_plan'] is False
    assert 'ingredient_name' in policy['recipe_picker']['search_fields'] and 'ingredient_alias' in policy['recipe_picker']['search_fields']
    assert policy['servings']['manual_recipe_portion_multiplier']==1 and policy['servings']['editable_in_composer'] is False
    ext=manifest.get('extensions',{}).get('v6_phase_f') or {}
    assert ext.get('version')=='6.0.0-phase-f.1'
    assert ext.get('policy_sha256')==sha('spec/v6/phase-f-policy.json')
    expected={
      'ingredients.base.v1.json':'1765f980c824b1d11b44155ac813a5b285ce57e527c0a9ace088468f24e84a1b',
      'recipes.base.v1.json':'535376cdea1d2508aa53a64c4bdf99a59cadbfd5644a5a3becd9f4fef87aa237',
      'plan-template.base.v1.json':'9a155f1bf900f55e83ad5c569d3529eba96c021fa503f14fa9a0becf9210428d',
    }
    for name,digest in expected.items():
        assert sha('v5_data/base/'+name)==digest,name
        assert sha('docs/data/v5/'+name)==digest,'published '+name
    assert sha('docs/data/v6/phase-f-policy.json')==sha('spec/v6/phase-f-policy.json')
    assert sha('docs/assets/js/v6-recipe-converter.js')==sha('static/assets/js/v6-recipe-converter.js')
    recipes=[p for p in (ROOT/'docs/ricette').glob('*/index.html') if p.parent.name not in {'studio','programma'}]
    assert len(recipes)==556,len(recipes)
    assert all('data-v6-recipe-converter' in p.read_text(encoding='utf-8') for p in recipes)
    sample=(ROOT/'docs/ricette/banana-e-latte/index.html').read_text(encoding='utf-8')
    assert 'v6-recipe-converter.js' in sample and 'READ only' in sample
    manager=(ROOT/'static/assets/js/v5-day-manager.js').read_text(encoding='utf-8')
    composer=(ROOT/'static/assets/js/v5-composer.js').read_text(encoding='utf-8')
    ccore=(ROOT/'static/assets/js/v5-composer-core.js').read_text(encoding='utf-8')
    today=(ROOT/'static/assets/js/v5-effective-pages.js').read_text(encoding='utf-8')
    manager_html=(ROOT/'docs/calendario/gestisci/index.html').read_text(encoding='utf-8')
    composer_html=(ROOT/'docs/calendario/componi/index.html').read_text(encoding='utf-8')
    assert 'matchesSearch' in ccore and 'ingredientNames' in ccore and 'ingredientAliases' in ccore
    assert 'composer.matchesSearch' in manager and 'pickerImpact' in manager and 'plannerStore.validateDays' in manager
    assert 'core.matchesSearch' in composer and 'pickerImpact' in composer and 'plannerStore.validateDays' in composer
    assert 'Contiene:' in manager and 'Contiene:' in composer
    assert all(f'data-manager-quick-offset="{n}"' in manager_html for n in [1,3,7,14])
    assert 'quick-plan-strip' in today and all(x in today for x in ["[1,'Domani']","[3,'+3 giorni']","[7,'+7 giorni']"])
    assert 'data-today-plan-date' in today and 'data-today-plan-go' in today
    assert 'data-add-portion value="1" readonly' in composer_html
    assert 'data-meal-portion' in composer and 'Porzione fissa' in composer
    assert 'is-v6-blocked' in manager and 'is-v6-blocked' in composer
    offline=load('docs/data/offline-assets.json')
    assert 'data/v6/phase-f-policy.json' in offline['assets'] and 'assets/js/v6-recipe-converter.js' in offline['assets']
    report={'status':'ok','phase':'V6-F','policy_version':policy['policy_version'],'checks':{
      'base_c2_byte_identity':True,'converter_on_all_recipe_pages':True,'read_only_converter':True,'ingredient_and_alias_search':True,
      'rolling_energy_picker_guard':True,'full_plan_commit_guard':True,'fixed_manual_serving':True,'future_shortcuts':True,'service_worker_assets':True}}
    out=ROOT/'qa/v6-phase-f/phase-f-release-report.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
