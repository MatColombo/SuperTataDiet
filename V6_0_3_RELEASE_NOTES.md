# TataDiet 6.0.3 — release notes

## Scopo

Release correttiva focalizzata su due bug emersi nel test manuale della 6.0.2:

1. coerenza dei pasti del turno notte che ricadono nel giorno civile successivo;
2. backup/ripristino poco chiaro e import non affidabile dal punto di vista UX.

Il baseline nutrizionale C.2 non viene modificato.

## 1. Turno notte: coda +1 giorno coerente

La sorgente autorevole dei pasti notturni resta la giornata di tipo `D2`. I pasti delle 03:30 e 08:20 sono memorizzati con `dayOffset = 1` e vengono visualizzati nel giorno civile successivo tramite l'effective plan.

La 6.0.3 centralizza questa semantica in `v5-plan-core.js`:

- inserendo una nuova giornata `D2`, viene materializzato un menu notte coerente, inclusi i pasti `+1`;
- trasformando una giornata non-notte in `D2`, vengono aggiunti gli slot/pasti di coda mancanti senza duplicarli;
- trasformando una `D2` in un tipo non-notte, i pasti con `dayOffset > 0` vengono rimossi;
- eliminando una `D2`, la sua coda scompare con la giornata sorgente;
- inserimenti/rimozioni prima di una `D2` spostano insieme data sorgente e coda civile, preservando l'allineamento.

La logica è nel core e vale quindi sia per **Gestisci giornata** sia per la modifica avanzata.

## 2. Backup: un solo flusso comprensibile

La sezione **Preferenze legacy V4** è stata rimossa. I vecchi JSON di preferenze del browser non sono più esposti né importabili dalla UI.

La pagina Utilità presenta ora un solo flusso:

1. **Scarica backup completo**;
2. **Seleziona backup TataDiet**;
3. verifica automatica di formato, checksum e dataset base;
4. anteprima del contenuto;
5. **Ripristina tutto dal backup**.

Il ripristino sostituisce:

- calendario e modifiche del piano;
- Diario;
- ricette e ingredienti personali;
- impostazioni;
- spunte della spesa.

Il catalogo base V6 resta intatto. Prima di scrivere viene creato automaticamente un checkpoint, annullabile con **Annulla l'ultimo ripristino**.

La UI non espone più `Unisci`, `Solo ricette`, `Solo calendario` o `Solo impostazioni`: erano modalità tecniche corrette ma poco adatte a un normale flusso di backup/ripristino.

## QA

- insert D2 con coda +1: PASS
- delete D2 con rimozione coda: PASS
- cambio tipo D1→D2→D1: PASS
- spostamenti strutturali prima di D2: PASS
- backup completo + restore round-trip: PASS
- Diario e spunte incluse nel restore: PASS
- catalogo base preservato: PASS
- checkpoint pre-ripristino: PASS
- nessun controllo legacy visibile: PASS
- regressioni C.2/D/E/F/G/H: PASS
- stress 96 operazioni + undo/redo: PASS
- validazione statica: 843 pagine, 72.393 riferimenti, 0 errori, 0 warning
