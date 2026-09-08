# TataDiet 6.0.0 — Release notes

TataDiet 6.0.0 is the V6 baseline release. It combines a manually curated 180-day plan with fixed-serving constraint-aware planning, ingredient substitution intelligence, improved meal replacement UX, future-date planning and a local-first diary.

## Curated diet baseline

The 180-day plan was reviewed explicitly rather than regenerated wholesale. The final baseline contains 180 days and 864 meals, with 556 recipe families / 797 fixed recipe versions and 131 ingredients.

Rolling seven-day V6 rules include the egg/egg-white ceiling, exactly three counted dairy portions with dairy-type variety, two avocado portions, plant-protein mains, pasta/rice presence, seasonality and anti-repetition controls. Purchase reuse is considered for relevant fresh/package-sensitive foods.

## Planner V6

Automatic planning uses fixed servings only. It supports targets from 800 to 2600 kcal, default ±5% tolerance, locked meals, optional snack omission at low targets and explicit `infeasible` results when a valid combination cannot be found. Automatic fallback paths do not silently scale recipes.

## Ingredient intelligence and recipe converter

Recipe pages include a read-only equal-energy ingredient converter. Suggested alternatives are ranked by food/culinary compatibility; free search can calculate any meaningful energy-equivalent comparison. The comparison shows equivalent grams and changes in protein, carbohydrate, fat and fibre.

## Meal replacement and future planning

Meal replacement searches recipe names and ingredients/aliases, displays ingredient summaries and gives immediate V6 constraint feedback. Automatic/manual recipe servings remain fixed at 1.0. Today and day-management pages include quick access to future dates.

## Diary

The new Diary stores what actually happened separately from the planned calendar. It provides meal/day traffic lights, rolling 7/30-day adherence summaries, notes, manual out-of-catalog meals and a frozen snapshot of the originally planned meals. Diary data is included in V6 backups.

## Storage and offline

IndexedDB/schema and backup schema are version 2. The legacy database identifier `tatadiet-v5` is intentionally retained to avoid an implicit local-data reset. The V6 interactive runtime, Diary and release policies are included in the offline/PWA package.

## Validation

The release gate rebuilds the app and runs C.2, D, E, F, G and H regressions, the 96-operation undo/redo stress scenario and complete static-site validation. Browser interaction tests are packaged for execution against a real deployment because the managed local Chromium blocks local navigation.
