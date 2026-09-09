#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def load(path): return json.loads((ROOT / path).read_text(encoding='utf-8'))
def text(path): return (ROOT / path).read_text(encoding='utf-8')
def sha(path): return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()

def main():
    expected = {
        'ingredients.base.v1.json': '1765f980c824b1d11b44155ac813a5b285ce57e527c0a9ace088468f24e84a1b',
        'recipes.base.v1.json': '535376cdea1d2508aa53a64c4bdf99a59cadbfd5644a5a3becd9f4fef87aa237',
        'plan-template.base.v1.json': '9a155f1bf900f55e83ad5c569d3529eba96c021fa503f14fa9a0becf9210428d',
    }
    for name, digest in expected.items():
        assert sha('v5_data/base/' + name) == digest, name
        assert sha('docs/data/v5/' + name) == digest, 'published ' + name

    meta = load('docs/data/build-meta.json')
    assert meta['version'] == '6.0.1'
    assert meta['counts']['recipes'] == 556

    # 1. Diary: effective plan dependencies must be loaded before diary store/app.
    diary_page = text('docs/diario/index.html')
    order = [
        diary_page.index('assets/js/v5-effective-core.js'),
        diary_page.index('assets/js/v5-effective-store.js'),
        diary_page.index('assets/js/v6-diary-core.js'),
        diary_page.index('assets/js/v6-diary-store.js'),
        diary_page.index('assets/js/v6-diary.js'),
    ]
    assert order == sorted(order), order

    # 2. Converter: exact recipe identity, visible version refresh, density rather than repeated equal-energy kcal.
    converter = text('static/assets/js/v6-recipe-converter.js')
    assert 'host.dataset.recipeId' in converter
    assert 'sel.value=version.id' in converter
    assert 'renderVersion();renderLines();await renderAlternatives();' in converter
    assert 'equivalenti · ${esc(densityText(r.target))}' in converter
    assert 'kcal/100' in converter
    recipes = load('v5_data/base/recipes.base.v1.json')
    grouped = {}
    for version in recipes['recipe_versions']:
        grouped.setdefault(version['recipe_id'], []).append(version)
    multi = [rows for rows in grouped.values() if len(rows) > 1]
    assert multi
    assert any(len({json.dumps(v.get('ingredient_lines', []), sort_keys=True) for v in rows}) > 1 for rows in multi)

    # 3. Future dates are read views, while editing remains an explicit action.
    pages = text('static/assets/js/v5-effective-pages.js')
    calendar = text('static/assets/js/calendar.js')
    overlay = text('static/assets/js/v5-plan-calendar.js')
    assert "function dayViewUrl(date,start)" in pages
    assert 'aria-label="Consulta date future"' in pages
    assert 'location.href=dayViewUrl(planDate.value,start)' in pages
    assert 'const readDayHref = (date, start)' in calendar
    assert 'const url=state.stateUrl("oggi/index.html",planBundle.plan.startDate,{date:d.date})' in overlay
    assert 'data-day-view-title' in text('templates/today.html')

    # 4. Every V6 recipe and every curated plan reference resolves.
    families = {row['id']: row for row in recipes['recipe_families']}
    versions = {row['id']: row for row in recipes['recipe_versions']}
    plan = load('v5_data/base/plan-template.base.v1.json')
    missing_families = []
    missing_versions = []
    for day in plan['days']:
        for meal in day['meals']:
            if meal.get('recipe_id') not in families: missing_families.append(meal.get('recipe_id'))
            if meal.get('recipe_version_id') not in versions: missing_versions.append(meal.get('recipe_version_id'))
    assert not missing_families
    assert not missing_versions
    missing_pages = []
    for recipe_id, family in families.items():
        slug = family.get('slug') or recipe_id.replace('base:recipe:', '')
        page = ROOT / 'docs' / 'ricette' / slug / 'index.html'
        if not page.exists(): missing_pages.append(slug)
        else:
            body = page.read_text(encoding='utf-8')
            assert f'data-recipe-id="{recipe_id}"' in body
    assert not missing_pages
    assert len(families) == 556 and len(versions) == 797
    assert sum(len(day['meals']) for day in plan['days']) == 864

    # Existing local DBs get the authoritative base catalog without deleting personal records.
    db = text('static/assets/js/v5-db.js')
    assert 'BASE_CATALOG_SYNC_VERSION = 1' in db
    assert 'async function ensureBaseCatalogCurrent' in db
    assert 'const baseCatalogSync = await ensureBaseCatalogCurrent' in db
    assert 'tx.objectStore("recipes").put(row)' in db and 'tx.objectStore("recipeVersions").put(row)' in db

    # 5. Pastel refresh + supercharged brand assets.
    css = text('static/assets/css/styles.css')
    logo = text('static/assets/brand/brand-mark.svg')
    assert 'V6.0.1 - pastel supercharged visual refresh' in css
    assert '#a44778' in css.lower() and '--surface-butter' in css
    assert 'TataDiet Supercharged' in logo and 'bolt' in logo and '#FFD46B' in logo
    for icon in ['icon-192.png', 'icon-512.png', 'icon-maskable-512.png', 'apple-touch-icon.png']:
        assert (ROOT / 'docs/assets/icons' / icon).exists(), icon

    report = {
        'status': 'ok', 'release': '6.0.1',
        'checks': {
            'baseline_c2_byte_identity': True,
            'diary_dependency_order': True,
            'converter_version_refresh_contract': True,
            'converter_density_display': True,
            'future_day_read_navigation': True,
            'catalog_sync_for_existing_indexeddb': True,
            'recipe_references_resolve': True,
            'recipe_static_pages': len(families),
            'curated_meals_checked': 864,
            'pastel_supercharged_branding': True,
        }
    }
    out = ROOT / 'qa/v6-0-1/v6-0-1-release-report.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))

if __name__ == '__main__': main()
