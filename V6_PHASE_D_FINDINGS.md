# TataDiet V6 — Fase D findings

## Stato

Fase D completata sul baseline C.2 senza modificare ingredienti, ricette o piano dei 180 giorni. I tre file base hanno gli stessi SHA-256 della release C.2.

## Copertura semantica

- ingredienti base: 131/131 classificati;
- ingredienti `other` nel catalogo base: 0;
- versioni ricetta profilate: 797/797;
- codici ingredienti duplicati tra classi semantiche: 0.

La tassonomia separa almeno proteine animali, pesce magro/grasso, seafood, legumi, uova, latticini freschi/stagionati, latte-yogurt, pasta/riso/altri cereali, pane/patate, frutta, famiglie di verdura, grassi e condimenti.

## Convertitore READ-only

Il motore calcola la grammatura del candidato a pari kcal e restituisce il delta di:

- kcal;
- proteine;
- carboidrati;
- grassi;
- fibre.

Il ranking greedy esclude gli `energy-only`; la ricerca libera li mantiene disponibili per confronto.

Casi di regressione verificati:

- riso basmati 80 g → pasta: compatibile e kcal equivalenti;
- riso basmati 80 g → olio: `energy-only`, non greedy;
- pollo 140 g → tacchino: `very-compatible`;
- pollo 140 g → merluzzo: `compatible`;
- ricotta → altri formaggi: alternative multiple disponibili;
- candidato con 0 kcal: nessuna divisione/NaN, equivalenza dichiarata non calcolabile.

## Performance

Sul catalogo attuale da 131 ingredienti il benchmark del test D esegue 2.000 ranking completi in circa 1,1-1,4 secondi nell'ambiente di sviluppo, cioe circa 0,6-0,7 ms per ranking medio. Questo e adeguato alla ricerca interattiva prevista per F.

## Constraint parity

Il nuovo evaluator JavaScript applicato ai 180 giorni C.2 produce:

- 180 giorni;
- 174 finestre mobili;
- 0 violazioni hard;
- 0 warning soft;
- 0 ripetizioni ricetta entro 7 giorni;
- 0 warning di stagionalita.

Conferma anche:

- latticini conteggiati rolling min=max 3;
- avocado rolling min=max 2.

Sono stati aggiunti test negativi:

- una sostituzione che crea un secondo latticino nello stesso giorno viene rifiutata;
- una sostituzione che elimina una delle due quote avocado fa fallire il gate rolling;
- un `portionMultiplier != 1` genera hard violation `scaled_recipe_portion`.

## Packaging

Le policy V6 e i moduli runtime D sono pubblicati dalla build e inclusi nel service worker. L'estensione `v6_phase_d` e registrata nel manifest del dataset.

## Confine della fase

Non sono stati implementati in D:

- dialog/modal del convertitore nella pagina ricetta;
- pulsanti di sostituzione;
- salvataggio della sostituzione ingrediente;
- planner multi-slot V6.

Il convertitore resta deliberatamente READ-only e la UI e prevista in F. La Fase E puo ora costruire il planner direttamente sopra `TataDietV6Constraints` e i profili prodotti da `TataDietIngredientIntelligence`.
