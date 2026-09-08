#!/usr/bin/env python3
from __future__ import annotations
import argparse
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
QA=ROOT/'qa'/'v6-phase-f'; QA.mkdir(parents=True,exist_ok=True)
parser=argparse.ArgumentParser(description='Browser smoke V6 Phase F')
parser.add_argument('--base-url', default='http://127.0.0.1:8765')
parser.add_argument('--executable-path', default='/usr/bin/chromium')
args=parser.parse_args()
BASE=args.base_url.rstrip('/')
errors=[]; checks=[]

def wire(page):
    page.on('pageerror', lambda exc: errors.append(f'pageerror: {exc}'))
    page.on('console', lambda msg: errors.append(f'console {msg.type}: {msg.text}') if msg.type=='error' else None)

def ok(name, value=True, detail=None):
    if not value: raise AssertionError(name if detail is None else f'{name}: {detail}')
    checks.append({'name':name,'status':'ok','detail':detail})

with sync_playwright() as p:
    launch={'headless':True,'args':['--no-sandbox','--disable-dev-shm-usage']}
    if args.executable_path: launch['executable_path']=args.executable_path
    browser=p.chromium.launch(**launch)
    ctx=browser.new_context(viewport={'width':1280,'height':900}, locale='it-IT', timezone_id='Europe/Rome', service_workers='block')
    page=ctx.new_page(); wire(page)

    # Recipe converter: greedy + free search + nutrition comparison.
    page.goto(f'{BASE}/ricette/banana-e-latte/', wait_until='networkidle')
    page.wait_for_selector('[data-converter-app]:not([hidden])', timeout=30000)
    ok('converter visible', page.locator('[data-v6-recipe-converter]').count()==1)
    ok('source ingredients available', page.locator('[data-converter-line]').count()>=2)
    page.wait_for_selector('[data-converter-result]')
    ok('greedy suggestions available', page.locator('[data-converter-result]').count()>=1)
    mode=page.locator('[data-converter-mode-note]').inner_text()
    ok('greedy mode labeled', 'Suggeriti greedy' in mode, mode)
    search=page.locator('[data-converter-search]')
    search.fill('olio')
    page.wait_for_timeout(250)
    page.wait_for_selector('[data-converter-result]')
    results=page.locator('[data-converter-results]').inner_text()
    ok('free search finds oil', 'olio' in results.lower(), results[:300])
    ok('free search mode labeled', 'Ricerca libera' in page.locator('[data-converter-mode-note]').inner_text())
    page.locator('[data-converter-result]').first.click()
    page.wait_for_selector('[data-converter-comparison]:not([hidden])')
    comp=page.locator('[data-converter-comparison]').inner_text()
    for label in ['Proteine','Carboidrati','Grassi','Fibre']:
        ok(f'comparison shows {label}', label in comp)
    ok('comparison read-only wording', 'Questo strumento non modifica la ricetta' in comp)
    page.screenshot(path=str(QA/'converter-desktop.png'), full_page=True)

    # Today: future shortcuts + free date picker.
    page.goto(f'{BASE}/oggi/?start=2026-09-07&date=2026-09-08', wait_until='networkidle')
    page.wait_for_selector('.quick-plan-strip')
    quick=page.locator('.quick-plan-strip').inner_text()
    ok('today tomorrow shortcut', 'Domani' in quick)
    ok('today +3 shortcut', '+3' in quick)
    ok('today +7 shortcut', '+7' in quick)
    ok('today date picker', page.locator('[data-today-plan-date]').count()==1)
    page.screenshot(path=str(QA/'today-quick-plan-desktop.png'), full_page=True)

    # Composer: fixed portion and ingredient-aware picker.
    page.goto(f'{BASE}/calendario/componi/?start=2026-09-07&focus=2026-09-08', wait_until='networkidle')
    page.wait_for_selector('[data-composer-app]:not([hidden])', timeout=30000)
    ok('composer fixed portion inputs', page.locator('[data-meal-portion][readonly]').count()>=1)
    replace=page.locator('[data-meal-replace]').first
    replace.click()
    page.wait_for_selector('[data-recipe-picker][open]')
    search=page.locator('[data-picker-search]')
    search.fill('lenticchie')
    page.wait_for_timeout(300)
    cards=page.locator('[data-picker-version]')
    ok('ingredient search returns recipes', cards.count()>=1, f'count={cards.count()}')
    picker_text=page.locator('[data-picker-results]').inner_text()
    ok('picker exposes ingredients', 'Contiene:' in picker_text, picker_text[:500])
    ok('picker exposes V6 window status', ('7gg OK' in picker_text) or ('Vincolo hard' in picker_text) or ('Warning V6' in picker_text) or ('Fuori kcal' in picker_text))
    page.screenshot(path=str(QA/'composer-picker-desktop.png'), full_page=True)
    page.locator('[data-picker-close]').click()

    # Day manager: quick future navigation and ingredient-aware picker placeholder.
    page.goto(f'{BASE}/calendario/gestisci/?start=2026-09-07&focus=2026-09-08', wait_until='networkidle')
    page.wait_for_selector('[data-day-manager-app]:not([hidden])', timeout=30000)
    for offset in ['1','3','7','14']:
        ok(f'manager quick offset {offset}', page.locator(f'[data-manager-quick-offset="{offset}"]').count()==1)
    ok('manager picker placeholder mentions ingredient', 'ingrediente' in (page.locator('[data-picker-search]').get_attribute('placeholder') or '').lower())
    page.screenshot(path=str(QA/'manager-quick-dates-desktop.png'), full_page=True)

    ctx.close(); browser.close()

report={'status':'ok' if not errors else 'failed','checks':checks,'browser_errors':errors}
(QA/'phase-f-browser-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
if errors: raise SystemExit(1)
