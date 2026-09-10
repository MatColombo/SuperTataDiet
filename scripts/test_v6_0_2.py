#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def text(p): return (ROOT/p).read_text(encoding='utf-8')
def load(p): return json.loads(text(p))
def sha(p): return hashlib.sha256((ROOT/p).read_bytes()).hexdigest()

def main():
    expected={
      'ingredients.base.v1.json':'1765f980c824b1d11b44155ac813a5b285ce57e527c0a9ace088468f24e84a1b',
      'recipes.base.v1.json':'535376cdea1d2508aa53a64c4bdf99a59cadbfd5644a5a3becd9f4fef87aa237',
      'plan-template.base.v1.json':'9a155f1bf900f55e83ad5c569d3529eba96c021fa503f14fa9a0becf9210428d',
    }
    for n,d in expected.items():
        assert sha('v5_data/base/'+n)==d,n
        assert sha('docs/data/v5/'+n)==d,'published '+n
    meta=load('docs/data/build-meta.json'); assert meta['version']=='6.0.2'
    manager=text('static/assets/js/v5-day-manager.js')
    composer=text('static/assets/js/v5-composer.js')
    balance=text('static/assets/js/v5-balance.js')
    scheduler=text('static/assets/js/v5-recipe-scheduler.js')
    pstore=text('static/assets/js/v6-planner-store.js')
    mtpl=text('templates/day_manager.html'); ctpl=text('templates/day_composer.html')
    css=text('static/assets/css/styles.css')

    # Manual flows: validation is informative only.
    assert 'Modifica bloccata: il piano finale non rispetta V6' not in manager
    assert 'Sostituzione bloccata:' not in composer
    assert "data-manager-pick=\"${esc(e.version.id)}\"" in manager and 'aria-disabled="true"' not in manager
    assert "data-pick-version=\"${esc(e.version.id)}\"" in composer and 'aria-disabled="true"' not in composer
    assert 'manualWarningsForPreview' in manager and 'manualWarnings(afterValidation,beforeValidation' in composer
    assert 'v6PlannerStore.manualWarnings(validation,beforeValidation)' in balance
    assert 'v6PlannerStore.manualWarnings(validation,beforeValidation)' in scheduler
    assert 'I controlli V6 sono informativi' in mtpl
    assert 'Le sostituzioni manuali sono sempre consentite' in ctpl
    assert 'describeIssue' in pstore and 'manualWarnings' in pstore

    # Automatic planner remains strict.
    assert "if(!result.accepted)throw new Error(`Planner V6: nessuna soluzione valida" in pstore
    assert 'data-suggest-apply' in composer and 'suggestionDraft?.accepted' in composer

    # Oggi card: explicit non-overlapping grid.
    assert 'grid-template-columns:max-content minmax(0,1fr) max-content' in css
    assert '.today-shift-actions{grid-column:3' in css
    assert 'overflow-wrap:anywhere' in css

    report={'status':'ok','release':'6.0.2','checks':{
      'baseline_c2_byte_identity':True,
      'day_manager_manual_save_warning_only':True,
      'meal_replacement_warning_only':True,
      'batch_manual_tools_warning_only':True,
      'automatic_planner_still_strict':True,
      'warning_reasons_human_readable':True,
      'today_shift_card_no_clipping_contract':True,
    }}
    out=ROOT/'qa/v6-0-2/v6-0-2-release-report.json'; out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__': main()
