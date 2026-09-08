# TataDiet V6 — Fase C.1: risultati

## Esito

La Fase C.1 è stata applicata al baseline V6 e passa il gate completo.

### Catalogo e rotazione

| Metrica | Fase C | Fase C.1 |
|---|---:|---:|
| Famiglie catalogo | 405 | **500** |
| Versioni catalogo | 646 | **741** |
| Famiglie realmente usate | 198 | **253** |
| Max occorrenze stessa famiglia | 20 | **12** |
| Famiglie diverse a colazione | 32 | **41** |
| Famiglie diverse negli spuntini | 32 | **58** |
| Famiglie diverse nel mini-pasto pre-sonno | 14 | **21** |
| Famiglie diverse a pranzo | 72 | **81** |
| Famiglie diverse a cena | 61 | **78** |

La C.1 aggiunge 95 famiglie fisse; 221 pasti del semestre usano effettivamente una ricetta C.1.

## Riduzione degli ingredienti dominanti

| Ingrediente | Fase C | C.1 |
|---|---:|---:|
| Banana | 87 | **55** |
| Carota | 78 | **52** |
| Spinaci | 74 | **51** |
| Zucca | 53 | **42** |
| Hummus | 50 | **24** |
| Salmone | 40 | **26** |
| Bresaola | 31 | **16** |
| Tacchino affettato | 33 | **16** |
| Burro di arachidi | 46 | **32** |
| Tacchino fresco | 54 | **45** |

Il tonno al naturale sale da 12 a 32 occasioni, ma è esplicitamente **cappato a 32** per non trasformarlo nel nuovo default. I lupini salgono da 23 a 30 e sono anch'essi cappati.

## Nuove rotazioni effettive

Ingredienti prima assenti dal semestre e ora realmente presenti:

- barbabietola 11;
- castagne 16;
- cavoletti di Bruxelles 14;
- cicoria 7;
- cozze 6;
- gnocchi 16;
- indivia 26;
- mais 15;
- patata dolce 22;
- polpo 6;
- rape 6;
- sardine 12;
- semi di zucca 31;
- tortilla 22.

Inoltre fave 6, trota 7, sgombro 11, maiale 27 e coniglio 14 migliorano la rotazione di legumi e proteine animali.

## Distribuzione legumi

La dipendenza da ceci/hummus è stata ridotta:

- hummus 24;
- ceci 21;
- lenticchie 19;
- cannellini 32;
- borlotti 14;
- piselli 11;
- fave 6;
- lupini 30.

Cece + hummus rappresentano **28,66%** delle occasioni legumi, sotto il limite C.1 del 40%.

## Frutta e verdura

Le prime tre frutte rappresentano il **46,82%** delle occasioni frutta, sotto il limite del 48%. Le prime tre verdure rappresentano il **30,85%**, sotto il limite del 36%.

La rotazione invernale contiene ora in modo sostanziale radicchio, cavolfiore, finocchio, broccoli, indivia, carciofi, bietole, cavoletti, barbabietola, cicoria e rape, oltre agli ingredienti già presenti.

## Anti-spreco

Nel baseline finale:

- mozzarella: 0 usi;
- primosale: 0;
- feta: 0;
- fiocchi di latte: 0;
- grana: 0;
- ricotta: 12 usi, **0 isolati**;
- robiola: 5 usi, **0 isolati**.

Ogni ricotta/robiola residua ha un altro utilizzo dello stesso ingrediente entro 4 giorni.

Gli ingredienti batch-preferred superano tutti il target minimo di riuso ravvicinato del 55%. Gli alimenti da dispensa/surgelabili non vengono artificialmente ripetuti solo per soddisfare il riuso.

Le 95 nuove ricette sono tutte a porzione fissa. Nessuna nuova portata principale animale usa una porzione simbolica inferiore a 90 g. Nessun tofu, tempeh o seitan è presente.

## Gate nutrizionale/editoriale finale

- hard violations: **0**;
- soft warnings: **0**;
- ripetizioni stessa famiglia entro 7 giorni: **0**;
- ingredienti fuori stagione: **0**;
- giornate fuori ±5% energia: **0**;
- massimo scostamento energetico: **4,95%**;
- max stessa famiglia in 180 giorni: **12**;
- fallimenti tetti globali: **0**;
- fallimenti ingredienti da attivare: **0**;
- latticini package-sensitive isolati: **0**.

## Regressione applicazione

Il gate `./v6_phase_c1.sh` passa:

1. rebuild catalogo C.1;
2. applicazione curation congelata;
3. audit Phase A/C + audit C.1;
4. report prima/dopo;
5. build PWA;
6. test contratto C.1;
7. stress test V5 con 96 operazioni, undo completo e redo completo.

La UI/build continua temporaneamente a riportare `5.2.1`: questa fase modifica dataset e curation, non ancora branding o motore V6.
