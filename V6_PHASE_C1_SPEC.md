# TataDiet V6 — Fase C.1: specifica varietà e riuso acquisti

## Scopo

La Fase C.1 parte dal baseline approvato della Fase C e ne aumenta la varietà reale senza indebolire i vincoli nutrizionali/editoriali già validati. Il focus è doppio:

1. ridurre la ripetizione nascosta di ingredienti/archetipi, soprattutto in colazioni e spuntini;
2. evitare varietà “costosa” in termini di spreco, cioè ingredienti deperibili acquistati appositamente per un singolo uso minimo.

La retrocompatibilità V5 non è un requisito. Il dataset resta identificato come `tatadiet-base-v2`; la fase applicata è `6.0.0-phase-c1.1`.

## Esclusioni

Non introdurre tofu, tempeh o seitan.

## Catalogo

La C.1 aggiunge **95 nuove famiglie / 95 versioni**, tutte con `servings = 1.0` e senza revisioni scalate. Il catalogo passa da 405/646 a **500 famiglie / 741 versioni**.

Le nuove ricette usano esclusivamente ingredienti già presenti nel master ingredienti. La C.1 non crea ingredienti esotici o “one-shot”: attiva meglio materie prime semplici già disponibili.

## Regole di varietà globale

Tetti su 180 giorni:

- stessa famiglia ricetta: max 12 occorrenze;
- banana max 55;
- carota max 55;
- spinaci max 55;
- zucca max 45;
- hummus max 25;
- salmone max 28;
- bresaola max 16;
- tacchino affettato max 16;
- burro di arachidi max 32;
- tonno al naturale max 32;
- tacchino fresco max 45;
- lupini max 30.

Ulteriori gate di concentrazione:

- quota delle prime 3 frutte <= 48% delle occorrenze frutta;
- quota delle prime 3 verdure <= 36% delle occorrenze verdura;
- ceci + hummus <= 40% delle occasioni legumi.

## Attivazione reale degli ingredienti sottoutilizzati

Almeno 6 occorrenze nel semestre per:

barbabietola, castagna, cavoletti, cicoria, cozze, fave, gnocchi, indivia, mais, patata dolce, polpo, rapa, sardine, semi di zucca, tortilla e trota.

Un ingrediente non viene considerato “aggiunto alla rotazione” se compare soltanto una o due volte.

## Riuso acquisti

### Formaggi / confezioni deperibili

Per mozzarella, ricotta, robiola, primosale, feta, fiocchi di latte e grana: **zero utilizzi isolati**. Ogni occorrenza deve avere almeno un altro uso dello stesso ingrediente entro ±4 giorni, oppure essere rimossa dalla curation.

### Ingredienti da batch

Per barbabietola, cavoletti, cicoria, indivia, rape, gnocchi, tortilla e mais, almeno il 55% delle occorrenze deve avere un altro utilizzo entro 4 giorni. È un controllo di praticità, non una prescrizione di ripetizione continua.

### Dispensa / freezer

Legumi, alimenti secchi, pesci conservabili/surgelabili e altri prodotti stoccabili non sono obbligati a un cluster ravvicinato. La conservabilità evita di creare monotonia solo per “finire la confezione”.

### Porzioni proteiche

Nelle nuove portate principali animali la componente carne/pesce è almeno circa 90 g. Non vengono create portate con 40–50 g di carne speciale solo per nominale varietà.

## Curation dei 180 giorni

La C.1 viene congelata in `spec/v6/phase-c1-curation.json`.

Rispetto alla Fase C:

- 180 giorni rivalutati;
- 864 pasti rivalutati;
- **131 giorni modificati**;
- **254 pasti modificati**;
- 610 pasti conservati;
- 221 utilizzi effettivi di ricette C.1.

La curation finale usa 253 famiglie ricetta distinte, contro 198 della Fase C.

## Gate preservati dalla Fase C

Devono restare contemporaneamente:

- 0 violazioni hard nelle 174 finestre mobili;
- max 6 egg-equivalent/7 giorni;
- max 4 formaggi/7 giorni e max 1/giorno;
- almeno 3 portate vegetali principali/7 giorni;
- almeno 5 pasti pasta/riso/7 giorni;
- equilibrio pasta/riso;
- 0 warning di concentrazione proteica o ingredienti;
- 0 ripetizioni stessa famiglia entro 7 giorni;
- 0 ingredienti fuori stagione;
- ogni giornata entro ±5% dal riferimento energetico del day-type.

## Artefatti e gate

- policy: `spec/v6/phase-c1-policy.json`;
- ricette: `spec/v6/phase-c1-recipes.json`;
- curation: `spec/v6/phase-c1-curation.json`;
- linee guida: `V6_PHASE_C1_GUIDELINES.md`;
- audit: `qa/v6-phase-c1/`;
- gate: `./v6_phase_c1.sh`.
