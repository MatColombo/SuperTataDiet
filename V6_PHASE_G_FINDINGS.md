# TataDiet V6 — Phase G findings

## Implemented

Phase G adds a dedicated `/diario/` page and three runtime modules:

- `v6-diary-core.js` — traffic-light semantics, adherence/completion calculations, planned snapshots and rolling summaries;
- `v6-diary-store.js` — local persistence and CRUD over `diaryDays`;
- `v6-diary.js` — diary UX.

The main navigation now exposes **Diario**, and `Oggi` contains a direct button to open the diary on the date being viewed.

## Diary UX

The month view shows one signal per day. Selecting a day opens the planned meals and allows one-tap:

- Seguito;
- Modificato;
- Fuori piano.

Each planned meal can also store what was actually eaten, optional kcal/macros/fibre and a note. Extra meals outside the recipe catalog can be added manually. A daily free-text comment is independent from meal notes.

The header shows cumulative adherence for 7 and 30 days, number of logged meals and completed days.

## Historical integrity

On the first write for a date, all planned meals for that civil date are snapshotted into the diary record, including meals not yet logged. This deliberately freezes the meaning of “planned” for that historical day. If the effective plan is modified afterwards, diary history is not silently rewritten.

## Persistence / backup

IndexedDB is now database/schema version 2 and contains `diaryDays`. Full and calendar JSON backups include the diary. The backup schema is version 2.

## Validation

Phase G-specific tests cover:

- green/yellow/red/gray day semantics;
- completion vs adherence;
- exclusion of manual meals from the adherence denominator;
- snapshot freeze after the first diary write;
- planned status persistence;
- manual-meal add/delete;
- daily comments;
- `Segna tutti seguiti`;
- build/offline publication;
- IndexedDB/backup schema wiring;
- byte identity of the C.2 base ingredient/recipe/plan files.

Static site validation after adding the diary page:

- 593 HTML pages;
- 51,895 links/resources/fragments checked;
- 0 errors;
- 0 warnings.

The historical 96-operation structural stress test continues to pass.

## Browser environment limitation

The managed Chromium available in the current development environment blocks both HTTP and `file://` navigation with `ERR_BLOCKED_BY_ADMINISTRATOR`. A real browser E2E smoke of the diary therefore cannot be used as a local release gate here. The browser test should be performed against the deployment during Phase H, as already required for the Phase F interactions.
