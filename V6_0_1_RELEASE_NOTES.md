# TataDiet 6.0.1 — release notes

Patch correttiva della V6.0.0 basata sul collaudo reale del 9 settembre 2026. Il baseline alimentare C.2 non viene modificato.

## Correzioni

1. **Diario** — corretta la sequenza degli script: il Diario viene inizializzato dopo il piano effettivo e non resta più bloccato su “Caricamento diario…”.
2. **Convertitore ingredienti** — il cambio versione usa l'ID ricetta esatto, aggiorna versione, ingredienti e risultati; l'elenco mostra grammi equivalenti e densità kcal/100 g, mentre il confronto conserva correttamente le kcal totali uguali per definizione.
3. **Consultazione date future** — calendario, overview e scorciatoie da Oggi aprono la vista read-only `/oggi/?date=...`; modifica e gestione restano azioni esplicite.
4. **Ricette non disponibili** — il build statico usa il catalogo V6 autorevole e genera 556 pagine ricetta. IndexedDB riallinea automaticamente il catalogo base quando proviene da una build intermedia, senza cancellare dati personali.
5. **Visual refresh** — palette pastello più ricca, maggiore differenziazione delle card e nuovo logo “TataDiet Supercharged”, applicato anche a favicon e icone PWA.

## Integrità dati

Restano invariati gli hash C.2 di ingredienti, ricette e piano. Il piano continua a contenere 180 giorni / 864 pasti; catalogo: 131 ingredienti, 556 famiglie, 797 versioni.

## QA

Il test dedicato `scripts/test_v6_0_1.py` verifica i cinque fix, tutti i riferimenti del piano e tutte le pagine ricetta. Le regressioni C.2, D, E, F, G e H e lo stress undo/redo restano verdi. Il validatore statico controlla 843 pagine HTML e 72.395 riferimenti con 0 errori / 0 warning.
