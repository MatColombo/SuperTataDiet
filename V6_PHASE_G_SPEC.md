# TataDiet V6 — Phase G specification

## Objective

Add a local-first **Diario** focused on fast daily logging and quick historical review. The diary records what actually happened without rewriting the effective plan.

## UX contract

The primary surface is `/diario/`.

It must provide:

- a month view with day traffic lights;
- a focused day detail with one-tap meal states;
- 7-day and 30-day cumulative summaries ending on the selected date;
- a fast `Segna tutti seguiti` action;
- per-planned-meal actual details for substitutions or meals outside the recipe catalog;
- extra/manual meals with optional kcal/macros/fibre;
- one free-text daily comment;
- direct access from `Oggi` and the main navigation.

Future dates are not loggable.

## Traffic-light semantics

### Meal

- `followed` — green — weight 1.0
- `partial` — yellow — weight 0.5
- `not-followed` — red — weight 0.0
- `unlogged` — gray — excluded from adherence score

### Day

- gray: no planned meal has been logged;
- yellow: the day is incomplete, or complete adherence is 50–84%;
- green: every planned meal is logged and adherence is at least 85%;
- red: every planned meal is logged and adherence is below 50%.

Manual/extra meals are shown in the diary but do not lower adherence by themselves.

## Data model

IndexedDB moves to database/schema version 2 and adds `diaryDays`.

Each `diaryDay` stores:

- `planInstanceId`;
- civil `date`;
- frozen planned-meal snapshots;
- per-meal status;
- optional actual/manual meal description and nutrition;
- manual extra meals;
- daily comment;
- timestamps.

The planned snapshot is frozen at the first diary write. A later plan edit therefore does not rewrite historical diary semantics.

## Backup

`diaryDays` is included in:

- full backup;
- calendar backup.

Backup schema moves to version 2. V6 does not require backward compatibility with V5 backup schema.

## Invariants

1. Diary writes never edit `calendarDays`, recipes, or the effective plan.
2. Base C.2 ingredient, recipe and 180-day plan files remain byte-identical.
3. Manual meals do not enter the adherence denominator.
4. The diary works offline once the normal PWA assets have been cached.
5. No future day is loggable from the diary UI.
