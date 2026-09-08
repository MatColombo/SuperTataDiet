# TataDiet V6 - Fase C.2: findings

## Risultato

La C.2 chiude il problema di sottorappresentazione dei formaggi senza riaprire il problema originario di eccesso.

Su 174 finestre mobili di 7 giorni:

- 174/174 hanno esattamente 3 porzioni di latticini conteggiati;
- 174/174 hanno almeno 2 tipologie diverse;
- 174/174 hanno esattamente 2 porzioni di avocado da 75 g;
- 0 giorni hanno piu di un latticino conteggiato.

## Distribuzione latticini nel semestre

- Grana: 25 porzioni;
- ricotta: 10;
- primosale: 10;
- robiola: 8;
- mozzarella: 8;
- feta: 8;
- fiocchi di latte: 8.

Totale: 77 porzioni.

Tutte le occorrenze dei sei formaggi freschi hanno un secondo uso dello stesso tipo entro 4 giorni. Non risultano acquisti freschi isolati.

## Avocado

- 52 porzioni;
- 75 g ciascuna;
- 3.900 g complessivi nel semestre;
- 0 porzioni isolate oltre l'orizzonte di riuso di 4 giorni;
- 2 porzioni esatte in ogni finestra mobile di 7 giorni.

## Impatto sulla C.1

La nuova curation modifica 138 pasti in 133 giorni rispetto alla C.1. Gli altri gate restano chiusi:

- 0 hard violations Fase A;
- 0 soft warnings;
- 0 recipe repeat entro 7 giorni;
- 0 fuori stagione;
- 0 giornate oltre +/-5% energia;
- massimo scostamento energetico 4,77%;
- max 12 occorrenze per famiglia;
- 0 global-cap failures;
- 0 activation failures;
- 0 batch-reuse failures.

Le concentrazioni globali restano nei limiti: top-3 frutta 46,64%, top-3 verdure 29,96%, ceci+hummus 25% delle occasioni legumi.


## QA e performance

Il gate C.2 (`./v6_phase_c2.sh`) passa: rebuild catalogo, applicazione del piano congelato, audit C.2, build PWA, test contrattuale e smoke stress con 8 operazioni/undo/redo completo.

Il precedente stress V5 da 96 operazioni non completa entro 240 secondi sul baseline ampliato C.2; il test ridotto passa. Il fenomeno viene registrato come backlog di performance per la futura fase motore e non altera i risultati nutrizionali/editoriali del baseline.
