# TataDiet V6 — Fase E Findings

## Esito

**PASS.** Il planner V6 è operativo e il baseline C.2 rimane byte-identico.

## Copertura energetica

La matrice di test dimostra copertura dell'intervallo richiesto con serving fissi e tolleranza ±5%:

| Target kcal | Day type usato | Risultato kcal | Esito |
|---:|---|---:|---|
| 800 | D3 | 798,13 | OK |
| 1000 | D1 | 1047,70 | OK |
| 1200 | D3 | 1199,36 | OK |
| 1400 | D1 | 1405,33 | OK |
| 1600 | D1 | 1567,46 | OK |
| 1800 | D4 | 1748,56 | OK |
| 2000 | D1 | 2001,00 | OK |
| 2200 | D4 | 2116,74 | OK |
| 2400 | D4 | 2285,46 | OK |
| 2600 | D4 | 2475,69 | OK |

Il test non richiede che ogni singolo day-type possa fisicamente coprire ogni target. Un D1 a 800 kcal, per esempio, non trova una combinazione valida con gli slot strutturali disponibili: il planner restituisce correttamente `infeasible`; nell'ultima esecuzione il best effort era 909,3 kcal ed esponeva `energy_target` come violazione.

## Serving

- 0 proposte automatiche con `portionMultiplier != 1`;
- un pasto bloccato a serving 1 viene preservato;
- un pasto bloccato già scalato viene rifiutato con `locked_scaled_portion`, non normalizzato in silenzio;
- anche i generatori automatici V5 ancora presenti come fallback non usano più scaling energetico.

## Constraint

Il baseline: 180 giorni, 864 pasti, 174 finestre, 0 hard e 0 soft.

La pianificazione sequenziale di tre giorni a 1400/1600/1200 kcal produce un piano completo ancora a **0 hard / 0 soft**, dimostrando che il planner non valida soltanto il giorno isolato ma preserva il contratto rolling.

Sono inclusi gate per varietà globale C.1, anti-spreco C.1/C.2, ripetizioni, stagionalità e preferenze utente.

## Prestazioni planner

Ultimo gate Node sulla matrice 800–2600:

- costruzione indice: circa 30–40 ms;
- mediana proposta nell’ultimo gate: circa **0,94 s**;
- P95 nell’ultima esecuzione: circa **2,14 s**;
- massimo nell’ultima esecuzione: circa **2,14 s**.

La prima configurazione di ricerca era circa 2–3 volte più lenta. La riduzione a 3 stati/bucket, beam 1200 e 220 finalisti mantiene la copertura 800–2600 e riduce sensibilmente il costo.

## Stress strutturale

Il timeout C.2 non dipendeva dal catalogo ampliato. Era una regressione del calcolo `affectedDays` nel vecchio `v5-plan-core`: `sortDays(daysInput)` veniva rieseguito dentro il confronto di ogni giornata.

Dopo la correzione:

- 96 operazioni consecutive;
- date continue e ID unici;
- modifiche strutturali;
- full undo;
- full redo;
- esecuzione nell'ordine di pochi secondi (circa 5–6 s nel gate corrente).

## Integrazione browser

È stato anche corretto l'ordine degli script: `v6-planner-core.js` viene caricato dopo `v5-plan-core.js`/`v5-composer-core.js`, e `v6-planner-store.js` dopo gli store da cui dipende. `Componi giornata` e `Gestisci giornata` usano il planner V6 nei percorsi automatici.

Il riequilibrio preferenze e lo scheduler ricetta possono ancora generare preview con la vecchia UX, ma prima del commit il loro stato viene validato contro V6; una selezione non conforme viene bloccata.

## Baseline invariato

SHA-256 invariati rispetto a C.2:

- ingredienti: `1765f980...e84a1b`
- ricette: `535376cd...aa237`
- piano 180 giorni: `9a155f1b...0428d`

La Fase F può quindi lavorare sulla UX senza dover ricostruire il motore: convertitore ingredienti, ricerca per ingrediente, picker constraint-aware e navigazione rapida alle date future possono usare i servizi D/E già disponibili.
