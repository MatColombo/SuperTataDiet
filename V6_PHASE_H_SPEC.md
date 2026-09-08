# TataDiet V6 — Phase H specification

## Objective

Freeze and validate the final **TataDiet 6.0.0** release after Phases A–G. Phase H does not alter the curated C.2 food baseline; it aligns release metadata, runs the complete regression chain, validates offline/backup packaging, and produces the final manual/deploy smoke checklist.

## Release contract

- Application version: `6.0.0`.
- Dataset: `tatadiet-base-v2`.
- Curated content remains byte-identical to C.2: 131 ingredients, 556 recipe families, 797 recipe versions, 180 days, 864 meals.
- Automatic recipe servings remain fixed at `1.0`.
- Planner range remains 800–2600 kcal with explicit infeasibility outside a feasible combination.
- D/F ingredient conversion remains read-only and equal-energy.
- G diary remains separate from the effective plan and uses IndexedDB/schema version 2.
- The historical IndexedDB database name `tatadiet-v5` is intentionally retained as a technical identifier to avoid an implicit local-data reset; it is not the application version.

## Release gates

1. Rebuild the static site from source.
2. Run C.2 curated-baseline regression.
3. Run D ingredient intelligence and V6 constraint regression.
4. Run E planner matrix, deterministic planning and multi-day planning regression.
5. Run F recipe converter/search/replacement regression.
6. Run G diary core/store/persistence regression.
7. Run H release-coherence regression.
8. Run the historical 96-operation undo/redo stress test.
9. Validate the complete generated static site and offline manifest.
10. If a browser-accessible deployment URL is supplied, run F/G interactive browser smoke tests.

## Browser/deploy smoke

The local Chromium environment is controlled by administrator policy and blocks local HTTP/file navigation. Browser smoke is therefore an explicit deploy gate rather than a local code gate. The release bundle includes executable browser tests and a human review matrix for:

- recipe ingredient converter;
- ingredient-aware meal replacement;
- future-date navigation;
- diary meal status/persistence/manual meals/comments;
- PWA install/update/offline behavior.
