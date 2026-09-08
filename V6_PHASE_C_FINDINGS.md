# TataDiet V6 - Fase C - Risultati

## Esito della revisione

- 180/180 giorni revisionati.
- 864 pasti valutati.
- 179 giorni modificati.
- 709 pasti sostituiti; 155 conservati.
- dataset promosso a `tatadiet-base-v2`.
- catalogo finale: 405 famiglie / 646 versioni.
- 15 nuove famiglie mirate create durante la curation, oltre alle 84 introdotte in Fase B.

L'ampiezza delle modifiche e' conseguenza della baseline V5: i vincoli su latticini, uova e proteine vegetali erano violati quasi sistematicamente, quindi non era realistico correggere il semestre con poche sostituzioni locali.

## Conformita' delle 174 finestre mobili

Risultato finale:

- uova/albume: 0 violazioni; massimo 4.6 egg-equivalent / 7 giorni;
- latticini/formaggi conteggiati: 0 violazioni; massimo 4 pasti / 7 giorni e massimo 1 nello stesso giorno;
- pasta/riso: 0 violazioni; minimo 5 pasti / 7 giorni, media 6.2;
- portate vegetali principali: 0 violazioni; esattamente almeno 3 / 7 giorni;
- equilibrio pasta/riso: nessun warning;
- concentrazione proteica: nessun warning;
- concentrazione ingredienti: nessun warning;
- stessa famiglia ricetta entro 7 giorni: 0 occorrenze;
- ingredienti fuori stagione: 0 occorrenze.

## Energia

Come gate editoriale della curation e' stato usato il profilo energetico dei day-type V5 con tolleranza +/-5%.

- massimo scostamento assoluto: 4.78%;
- mediana dello scostamento assoluto: 0.42%;
- giornate oltre il 5%: 0.

Il valore non sostituisce il futuro target calorico configurabile del planner V6.

## Distribuzione mensile

Ogni mese contiene 13 portate vegetali principali. Pasta e riso sono distribuiti in modo regolare, con 25-28 pasti complessivi al mese in cui uno dei due e' la fonte glucidica principale.

Egg-equivalent mensili: 4.0-9.2. Pasti con formaggi/latticini conteggiati: 10-12 al mese.

## Proteine vegetali

Le 78 portate principali vegetali usano piu' fonti: ceci, lenticchie, cannellini, piselli, borlotti, lupini e fave. I ceci sono la fonte piu' frequente, ma non sono l'unica base del pattern.

## Ripetitivita' globale

Il gate forte e' la distanza temporale: nessuna famiglia ricetta ricompare entro 7 giorni.

Guardando invece l'intero semestre, alcuni snack semplici ricorrono 16-20 volte. Il massimo e' 20 occorrenze, con distanza minima di 8 giorni. Un tentativo di imporre un tetto globale di 15 senza ampliare ulteriormente il catalogo snack creava conflitti con concentrazione ingredienti o energia; per questo non e' stato forzato artificialmente in Fase C.

Questo punto resta visibile in `qa/v6-phase-c/recipe-usage.csv` e puo' guidare una successiva espansione mirata del catalogo snack, se si vuole una varieta' globale ancora maggiore.

## Differenza rispetto alla Fase A

Baseline Fase A:

- 167 finestre con eccesso uova;
- 174 finestre con eccesso latticini;
- 117 giornate con piu' di un latticino conteggiato;
- 49 finestre insufficienti per pasta/riso;
- 174 finestre insufficienti per proteine vegetali principali;
- 216 ripetizioni ricetta entro 7 giorni;
- 39 occorrenze fuori stagione.

Fase C: tutti questi contatori sono a zero.
