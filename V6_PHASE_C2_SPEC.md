# TataDiet V6 - Fase C.2: specifica

## Scope

Baseline: `tatadiet-base-v2`, derivato dalla C.1 approvata.
Policy: `6.0.0-phase-c2.1`.

La C.2 aggiunge un ingrediente (`avocado`) e una tranche mirata di ricette a porzione fissa per rendere verificabili i nuovi requisiti senza modificare serving a runtime.

## Contratto latticini

I codici conteggiati sono `ricotta`, `robiola`, `mozzarella`, `feta`, `fiocchi_latte`, `primosale`, `grana`.

In ogni finestra mobile di 7 giorni:

- porzioni = 3 esatte;
- tipologie distinte >= 2;
- massimo 1 porzione per giorno.

Le porzioni fresche sono organizzate in coppie riutilizzabili entro 4 giorni. Il Grana e storage-flexible.

## Contratto avocado

- ingrediente: `avocado`;
- porzione fissa: 75 g;
- porzioni per finestra mobile di 7 giorni: 2 esatte;
- ogni occorrenza deve avere un'altra occorrenza entro 4 giorni;
- coppia di acquisto: 150 g.

I valori nutrizionali del nuovo ingrediente provengono dalla tabella CREA "Avocado, fresco" e sono salvati nella provenance dell'ingrediente.

## Catalogo

La tranche finale C.2 contiene 56 famiglie realmente utilizzate nel baseline. Le varianti tecniche non utilizzate durante la curation sono state eliminate prima del freeze per evitare rumore nella ricerca ricette.

Tutte le ricette C.2 hanno `servings = 1.0`.

## Curation

La curation e congelata in `spec/v6/phase-c2-curation.json`.

Rispetto alla C.1:

- 180 giorni rivalutati;
- 864 pasti rivalutati;
- 133 giorni modificati;
- 138 pasti modificati;
- 129 occorrenze di ricette C.2 nel piano finale.

## Gate

Il gate `./v6_phase_c2.sh` deve ottenere zero errori per:

- audit hard/soft della Fase A;
- contratto rolling latticini/avocado;
- riuso formaggi freschi;
- riuso avocado;
- energia +/-5%;
- family cap;
- global caps C.1;
- activation minima C.1;
- batch reuse C.1;
- stagionalita;
- recipe repeat <=7 giorni;
- contratto porzioni fisse C.2;
- build PWA e smoke stress C.2 con undo/redo completo.

Il precedente stress V5 da 96 operazioni resta un controllo esteso separato: sul catalogo C.2 non completa entro 240 s nell ambiente di sviluppo e viene tracciato come backlog di performance per la fase motore, non come gate dati C.2.
