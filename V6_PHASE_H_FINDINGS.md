# TataDiet V6 — Phase H findings

## Release result

Phase H closes the V6 development cycle and freezes **TataDiet 6.0.0**. The automated release gate passes after a clean rebuild.

The final build validates 593 HTML pages and 51,895 links/resources/fragments with 0 errors and 0 warnings. The historical 96-operation structural stress scenario passes with full undo and full redo in about 2.8 seconds in the final run.

## Baseline integrity

Phase H does not change the curated C.2 food content. The three authoritative base files retain the C.2 hashes:

- ingredients: `1765f980c824b1d11b44155ac813a5b285ce57e527c0a9ace088468f24e84a1b`;
- recipes: `535376cdea1d2508aa53a64c4bdf99a59cadbfd5644a5a3becd9f4fef87aa237`;
- 180-day plan: `9a155f1bf900f55e83ad5c569d3529eba96c021fa503f14fa9a0becf9210428d`.

Final baseline counts are 131 ingredients, 556 recipe families, 797 recipe versions, 180 days and 864 meals.

C.2 rolling rules remain fully satisfied: exactly 3 counted dairy portions / 7 rolling days with at least 2 dairy types, exactly 2 avocado portions / 7 days, no egg/egg-white breach, plant-protein and pasta/rice minima preserved, no recipe-family repeat inside 7 days and no seasonality warnings.

## Final application version

Application-facing versioning is now `6.0.0` in generated HTML, build metadata, PWA runtime, IndexedDB metadata and backup envelopes.

IndexedDB/schema and backup schema remain version 2. The database name `tatadiet-v5` is deliberately retained as a legacy technical identifier; renaming it in H would create an implicit empty database and therefore a destructive local-data reset without functional benefit.

## Offline/PWA packaging

The core service-worker bundle now explicitly contains the V6 interactive surfaces introduced after E:

- recipe converter;
- Diary page and Diary core/store/UI modules;
- F, G and H policies.

The web-app manifest exposes a Diary shortcut and the offline manifest contains 668 assets in the final build.

## Integrated regression

The final H runner executes C.2, D, E, F, G and H tests in sequence. It verifies the fixed-serving planner, 800–2600 kcal coverage matrix, explicit infeasibility, deterministic and range planning, ingredient equal-energy conversion/ranking, ingredient-aware recipe search, constraint-aware replacement, Diary semantics/store/snapshot persistence, release metadata, PWA/offline packaging and baseline byte identity.

The final E planner performance report shows index creation about 9.7 ms, matrix median 298 ms, P95/max 543 ms in the final H run.

## Browser validation boundary

The managed local Chromium blocks both HTTP and file navigation with `ERR_BLOCKED_BY_ADMINISTRATOR`. No browser-accessible deployment URL was provided during Phase H, so a visual/end-to-end smoke cannot be truthfully marked executed.

This does not block the automated/static release gate. Two executable deploy tests are retained (`test_v6_phase_f_browser.py` and `test_v6_phase_h_browser.py`) together with `qa/v6-phase-h/manual-review.csv`. They cover converter, meal picker, future-date UX, Diary persistence, PWA/offline and responsive visual checks.
