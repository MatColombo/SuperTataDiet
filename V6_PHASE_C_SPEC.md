# TataDiet V6 - Fase C

## Scopo

La Fase C sostituisce il piano standard V5 con una curation esplicita di tutti i 180 giorni. Non viene rigenerato il semestre a runtime: ogni singolo pasto selezionato e' congelato in `spec/v6/phase-c-curation.json` e applicato deterministicamente da `scripts/apply_v6_phase_c_plan.py`.

La retrocompatibilita' del dataset V5 non e' un requisito. Il baseline passa a `tatadiet-base-v2`.

## Metodo editoriale

La revisione e' stata eseguita in ordine cronologico controllando contemporaneamente la finestra mobile di 7 giorni, il giorno corrente e la distribuzione globale del semestre.

Backbone settimanale usato come guardrail di curation:

- giorno modulo 7 = 1: portata vegetale con pasta;
- modulo 7 = 2: riso con proteina non vegetale;
- modulo 7 = 3: portata vegetale con riso;
- modulo 7 = 4: pasta con proteina non vegetale;
- modulo 7 = 5: portata vegetale con pasta;
- modulo 7 = 6: riso con proteina non vegetale;
- modulo 7 = 0: principale alternativo, usato per ampliare la varieta'.

Il backbone e' un vincolo di distribuzione, non una ricetta fissa. Le famiglie vengono ruotate per stagione e non possono ripetersi entro 7 giorni.

## Gate V6 applicati

Hard:

- uovo + albume <= 6 egg-equivalent in ogni finestra mobile di 7 giorni;
- <= 4 pasti con formaggi/latticini conteggiati in ogni finestra mobile di 7 giorni;
- <= 1 pasto con formaggi/latticini conteggiati nello stesso giorno;
- latte, yogurt e kefir esclusi dal limite formaggi;
- >= 3 portate principali con proteina vegetale in ogni finestra mobile di 7 giorni;
- >= 5 pasti con pasta o riso come carboidrato principale in ogni finestra mobile di 7 giorni.

Soft promossi a gate di curation:

- >= 2 pasti di pasta e >= 2 pasti di riso in ogni finestra mobile di 7 giorni;
- nessuna ripetizione della stessa famiglia ricetta entro 7 giorni;
- nessuna concentrazione proteica segnalata dall'audit;
- nessuna concentrazione ingrediente segnalata dall'audit;
- nessun ingrediente fresco fuori stagione secondo la policy V6-A;
- massimo 2 egg-equivalent nello stesso giorno;
- energia giornaliera entro +/-5% del riferimento del day-type durante la curation standard.

L'energia resta un controllo del piano standard; il planner V6 successivo dovra' usare il target e la tolleranza scelti dall'utente.

## Nuove ricette mirate emerse durante la curation

La Fase C aggiunge altre 15 famiglie a porzione fissa oltre alle 84 della Fase B. Sono principalmente brunch completi ad energia piu' alta, privi di uova e formaggi, necessari soprattutto per i giorni D3/Smonto, piu' una colazione rinforzata con yogurt escluso dal budget formaggi.

Nessuna nuova famiglia V6 usa serving scalabili: tutte le versioni hanno `servings = 1.0`.

## Artefatto autorevole

`spec/v6/phase-c-curation.json` contiene 180 record giorno e 864 assegnazioni pasto con:

- ricetta originale;
- ricetta selezionata;
- flag changed;
- ragioni della sostituzione;
- focus editoriale del giorno;
- indicatori nutrizionali e di conformita' della giornata.

Questo file e' il contratto riproducibile della curation. L'euristica usata durante il lavoro non e' necessaria per ricostruire il risultato.

## Applicazione e validazione

`./v6_phase_c.sh` ricostruisce il catalogo mirato, applica la curation, esegue audit e report, ricostruisce la PWA e lancia i test Phase C.

Output principali in `qa/v6-phase-c/`:

- `phase-c-summary.json`;
- `day-curation.csv`;
- `meal-curation.csv`;
- `window-audit.csv`;
- `monthly-balance.csv`;
- `recipe-usage.csv`;
- `plant-protein-distribution.csv`;
- `ingredient-frequency.csv`;
- `violations.json`.
