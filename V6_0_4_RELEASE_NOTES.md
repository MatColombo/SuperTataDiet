# TataDiet 6.0.4 — Savestate restore

## Obiettivo

Correggere il ripristino dei backup completi su dispositivi vergini o con cache/localStorage vuoti. Un backup completo deve comportarsi come un vero savestate: dopo il restore il calendario, il piano attivo e le modifiche devono essere immediatamente disponibili e modificabili.

## Root cause

Il backup 6.0.2 fornito per la regressione contiene correttamente `planStartDate`, `activePlanInstanceId`, 2 piani da 180 giorni, 360 `calendarDays` e 20 operazioni. Il piano più recente contiene 11 giornate personalizzate.

Il restore 6.0.3 scriveva questi dati in IndexedDB, ma il frontend continuava a risolvere la data iniziale tramite la chiave localStorage `diet-plan:start-date:v2`. Su un browser vergine quella chiave non esisteva: il piano era presente nel database ma molte pagine restavano nello stato "non configurato".

Il backup di regressione contiene inoltre due `planInstance` marcati `active`; le impostazioni indicano correttamente quale dei due è il piano effettivo.

## Correzioni

- Il restore sincronizza `planStartDate` anche nel bridge localStorage usato dall'interfaccia.
- `db.initialize()` autoripara il bridge localStorage a partire dalle impostazioni IndexedDB.
- I backup nuovi includono una sezione `savestate` esplicita con `activePlanInstanceId`, `planStartDate` e le chiavi browser TataDiet (`diet-plan*`).
- I backup schema 2 creati da 6.0.2/6.0.3 restano compatibili anche senza la sezione `savestate`.
- In fase di import, se più piani sono marcati `active`, viene mantenuto attivo solo il piano indicato dal savestate/impostazioni; gli altri vengono archiviati.
- `activeBundle()` riconcilia automaticamente eventuali stati `active` duplicati già presenti nel database.
- `ensureActive()` sceglie il piano più recente quando esistono più piani con la stessa data di partenza.
- Il preview del backup valida i riferimenti piano↔giornate e mostra quale savestate verrà ripristinato.
- Le spunte browser `diet-plan-shopping*` entrano nei nuovi savestate e vengono ripristinate insieme agli altri dati.

## Regressione sul backup reale

Il file `tatadiet-backup-full-2026-09-22.json` è stato usato direttamente come fixture esterna di regressione, senza includerlo nella release.

Risultato:

- backup 6.0.2 accettato;
- piano attivo corretto ripristinato;
- 180/180 giornate disponibili;
- 11 giornate personalizzate presenti;
- un solo piano marcato `active`;
- `planStartDate` visibile immediatamente alla UI;
- una modifica post-import al calendario viene persistita correttamente.

## Compatibilità

Lo schema backup resta `2`; la modifica è retrocompatibile con i backup full 6.0.2 e 6.0.3.
