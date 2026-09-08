#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]; QA=ROOT/'qa'/'v6-phase-h';QA.mkdir(parents=True,exist_ok=True)
p=argparse.ArgumentParser();p.add_argument('--base-url',required=True);p.add_argument('--executable-path',default='/usr/bin/chromium');a=p.parse_args();base=a.base_url.rstrip('/')
checks=[];errors=[]
def ok(name,value=True,detail=None):
    if not value: raise AssertionError(name if detail is None else f'{name}: {detail}')
    checks.append({'name':name,'status':'ok','detail':detail})
with sync_playwright() as pw:
    launch={'headless':True,'args':['--no-sandbox','--disable-dev-shm-usage']}
    if a.executable_path: launch['executable_path']=a.executable_path
    browser=pw.chromium.launch(**launch);ctx=browser.new_context(viewport={'width':1280,'height':900},locale='it-IT',timezone_id='Europe/Rome',service_workers='allow')
    page=ctx.new_page();page.on('pageerror',lambda exc: errors.append(f'pageerror: {exc}'))
    page.goto(f'{base}/diario/?start=2026-09-01&date=2026-09-08',wait_until='networkidle');page.wait_for_selector('[data-diary-app]:not([hidden])',timeout=30000)
    ok('diary visible',page.locator('[data-diary-calendar]').count()==1)
    page.locator('[data-diary-mark-all]').click();page.wait_for_timeout(300)
    score=page.locator('[data-diary-day-score]').inner_text();ok('mark all gives 100 percent','100%' in score,score)
    form=page.locator('[data-diary-manual-form]');form.locator('[name="title"]').fill('Smoke test H');form.locator('[name="energyKcal"]').fill('500');form.locator('button[type="submit"]').click();page.wait_for_timeout(300)
    ok('manual meal visible','Smoke test H' in page.locator('[data-diary-meals]').inner_text())
    page.locator('[data-diary-comment]').fill('Persistenza smoke H');page.locator('[data-diary-save-comment]').click();page.wait_for_timeout(300);page.reload(wait_until='networkidle');page.wait_for_selector('[data-diary-app]:not([hidden])')
    ok('comment persists',page.locator('[data-diary-comment]').input_value()=='Persistenza smoke H')
    ok('manual meal persists','Smoke test H' in page.locator('[data-diary-meals]').inner_text())
    page.screenshot(path=str(QA/'diary-deploy-smoke.png'),full_page=True)
    ctx.close();browser.close()
report={'status':'ok' if not errors else 'failed','phase':'V6-H-browser','checks':checks,'browser_errors':errors}
(QA/'phase-h-browser-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(report,ensure_ascii=False,indent=2))
if errors: raise SystemExit(1)
