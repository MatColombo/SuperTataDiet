# TataDiet V6 — Fase E

## Scopo

La Fase E introduce il planner V6 constraint-aware sul baseline alimentare congelato in C.2. Il planner non deve migliorare il piano standard modificandolo: deve usare C.2 come golden baseline e produrre nuove proposte che non degradino i suoi vincoli hard/soft, la varietà o le regole di riuso acquisti.

La UI definitiva del planner e del convertitore ingredienti resta in F. Questa fase consegna il motore, lo store runtime, l'integrazione minima nei flussi automatici esistenti e il gate prestazionale.

## Contratto energetico

- target ammesso: **800–2600 kcal/giorno**;
- tolleranza default: **±5%**;
- tolleranza massima configurabile dal core: ±20%;
- l'energia è un hard constraint: una proposta è applicabile solo se rientra nei limiti;
- se nessuna combinazione valida esiste, il risultato è `infeasible` con diagnostica e migliore tentativo; nessuno sforamento viene accettato silenziosamente;
- le ricette automatiche hanno sempre `portionMultiplier = 1.0`.

Gli snack sono gli unici slot opzionali eliminabili per raggiungere target bassi. Colazione, brunch, pranzo, cena e pasto preturno non vengono omessi automaticamente. Un pasto bloccato non viene mai eliminato o sostituito.

## Contratto di qualità preservato

Il planner riusa i profili e l'evaluator della Fase D e preserva:

- uova/albume entro il limite rolling;
- esattamente 3 porzioni di latticini conteggiati ogni 7 giorni mobili, max 1/giorno e varietà tipologica;
- esattamente 2 porzioni di avocado ogni 7 giorni mobili;
- quote minime pasta/riso e proteine vegetali principali;
- stagionalità;
- nessuna ripetizione della stessa famiglia entro 7 giorni;
- warning di concentrazione ingredienti/proteine non superiori al baseline;
- cap globali C.1 e attivazioni minime;
- riuso dei formaggi freschi e dell'avocado;
- preferenze utente `never` e `maxPer7Days`.

Quando il giorno di partenza è già conforme, il planner conserva la sua firma giornaliera per latticini e avocado. Questo impedisce che una ripianificazione locale rompa indirettamente le finestre C.2 adiacenti.

## Ricerca

Il planner esegue una ricerca deterministica a stati bucketizzati:

1. genera candidati compatibili per slot;
2. elimina a monte candidati fuori stagione, ricette troppo vicine, cap globali già saturi e incompatibilità di preferenza;
3. costruisce combinazioni a serving fisso;
4. pota per energia e firma giornaliera;
5. valuta i finalisti contro vincoli rolling, ripetizioni, varietà globale e anti-spreco;
6. accetta solo soluzioni pulite.

Parametri Phase E:

- max 52 candidati/slot;
- max 3 stati per bucket;
- beam max 1200 stati;
- max 220 finalisti;
- bin energetico 20 kcal.

## API runtime

### `v6-planner-core.js`

Espone:

- `createIndex()`
- `targetBounds()`
- `defaultTarget()`
- `daySignature()`
- `globalMetrics()`
- `globalVarietyViolations()`
- `purchaseReuseViolations()`
- `preferenceViolations()`
- `planDay()`
- `planRange()`

`planDay()` restituisce sempre `accepted/status`, target e tolleranza, menu proposto/best effort, diagnostica delle violazioni e tempo di esecuzione.

### `v6-planner-store.js`

Espone preview/applicazione giorno, preview intervallo, impostazioni energetiche e `validateDays()` per impedire che flussi automatici legacy applichino stati incompatibili con V6.

## Integrazione minima Phase E

- `Componi giornata` usa il planner V6 per le proposte automatiche e applica esattamente la preview validata;
- `Gestisci giornata` usa il planner V6 quando il menu è in modalità Adatta/Personalizza;
- riequilibrio preferenze e programmazione ricetta restano con la loro UX esistente, ma le sostituzioni automatiche sono a serving fisso e l'applicazione viene bloccata se lo stato finale viola V6;
- la UI completa di ricerca ingrediente/cambio pasto e del convertitore resta in F.

## Prestazioni

È stata corretta una regressione preesistente in `v5-plan-core.applyAction()`: il calcolo dell'impatto riordinava e clonava l'intero piano dentro il confronto di ciascuno dei 180 giorni. Il piano originale viene ora ordinato una sola volta per operazione.

Il vecchio stress da 96 operazioni, full undo e full redo torna quindi ad essere un gate reale della release.

## Dati

La Fase E non modifica ingredienti, ricette o i 180 giorni C.2. Gli hash dei tre file base restano invariati. Cambiano solo policy, runtime e manifest di fase.
