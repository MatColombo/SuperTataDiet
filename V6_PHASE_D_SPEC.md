# TataDiet V6 — Fase D

## Scopo

La Fase D introduce il livello condiviso di **Ingredient Intelligence** che sara usato sia dal planner V6 sia dal convertitore ingredienti della futura UX. Non modifica il baseline C.2 dei 180 giorni e non crea revisioni ricetta.

Principi vincolanti:

- una sostituzione a pari kcal e un calcolo quantitativo, non una dichiarazione di equivalenza nutrizionale;
- il convertitore e **READ-only**: non salva o modifica automaticamente la ricetta;
- le ricette automatiche V6 restano a porzione fissa `1.0`;
- il ranking greedy mostra solo alternative semanticamente compatibili e con grammatura plausibile;
- la ricerca esplicita puo mostrare anche candidati `energy-only`, chiaramente distinti e mai suggeriti automaticamente;
- planner e convertitore devono usare la stessa semantica ingredienti e lo stesso evaluator dei vincoli.

## Componenti

### `v6-ingredient-intelligence-core.js`

Responsabilita:

1. normalizzazione ingrediente/revisione base o personale;
2. classificazione strutturata (`classId`, `primaryRole`, traits);
3. calcolo nutrizionale per quantita;
4. calcolo della quantita alternativa a pari kcal;
5. delta READ di kcal, proteine, carboidrati, grassi e fibre;
6. compatibility score 0-100;
7. classi di risultato: `very-compatible`, `compatible`, `with-differences`, `energy-only`;
8. ranking greedy e ricerca testuale rapida;
9. classificazione semantica delle versioni ricetta per i vincoli V6.

Formula base:

```text
kcal_originali = quantita_originale / basis_originale * kcal_originale_per_basis
quantita_alternativa = kcal_originali / kcal_alternativa_per_basis * basis_alternativa
```

La quantita usa la `baseQuantity` della riga ricetta e restituisce la `basis.unit` dell'ingrediente candidato (`g` o `ml`).

### `v6-constraint-core.js`

Evaluator riutilizzabile dal futuro planner. Valuta senza correggere automaticamente:

- egg-equivalent;
- quota e varieta latticini C.2;
- massimo un latticino conteggiato/giorno;
- pasta/riso;
- proteine vegetali principali;
- avocado C.2;
- porzione ricetta fissa;
- equilibrio pasta/riso;
- concentrazione proteica;
- concentrazione ingredienti;
- ripetizioni ricetta;
- stagionalita.

Espone anche `evaluateReplacement()`: simula una sostituzione e valuta solo la giornata e le finestre mobili interessate. Il risultato contiene `accepted`, hard/soft prima e dopo e la preview, ma non persiste nulla.

### `v6-intelligence-store.js`

Adapter runtime READ-only:

- carica ingredienti, revisioni, ricette e versioni da IndexedDB;
- carica le policy V6 pubblicate;
- costruisce catalogo ingredienti e profili ricetta;
- espone suggerimenti/search del convertitore;
- espone evaluator piano/sostituzione.

Non contiene metodi di scrittura.

## Semantica di compatibilita

Il ranking considera, in ordine:

- stessa famiglia funzionale;
- famiglie culinarie vicine esplicitamente consentite;
- stesso ruolo principale nel pasto;
- profilo macro a pari kcal;
- plausibilita della grammatura equivalente;
- categoria e stato di preparazione.

Esempi attesi:

- pollo → tacchino: `very-compatible`;
- pollo → merluzzo: `compatible`;
- riso → pasta: `compatible`;
- riso → olio: `energy-only`, calcolabile solo tramite ricerca esplicita;
- ingredienti a 0 kcal: equivalenza non calcolabile.

## Policy

`spec/v6/phase-d-policy.json` contiene:

- tassonomia delle 131 materie prime base;
- ruoli e famiglie di sostituzione;
- vicinanze compatibili;
- range di grammatura plausibile;
- soglie score;
- contratto planner READ-only/fixed serving.

La policy evita doppie assegnazioni dello stesso codice a classi semantiche diverse.

## Pubblicazione PWA

La build copia in `docs/data/v6/`:

- `phase-a-policy.json`
- `phase-c1-policy.json`
- `phase-c2-policy.json`
- `phase-d-policy.json`

I tre moduli D vengono inclusi negli asset PWA/offline. Nessuna UI del convertitore viene introdotta in D: la visualizzazione resta prevista per la Fase F.

## Gate

Gate riproducibile:

```bash
./v6_phase_d.sh
```

Sequenza:

1. build PWA;
2. regressione baseline C.2;
3. test core D;
4. verifica packaging/pubblicazione;
5. smoke stress calendario con undo/redo.
