# TataDiet 6.0.2

TataDiet è una PWA statica e local-first per gestire un piano alimentare su turni. **V6.0.2** mantiene i fix 6.0.1 e rende tutte le modifiche manuali libere: i controlli V6 diventano warning motivati, mentre i vincoli restano obbligatori soltanto per le proposte automatiche del planner. Corregge inoltre il clipping della card Oggi.

## V6.0.2

Correzioni principali:

- Diario: ordine dipendenze corretto, niente più blocco su “Caricamento diario…”;
- catalogo locale: sincronizzazione automatica dei record base V6 già installati, senza cancellare dati personali;
- pagine ricetta: build dal catalogo V6 completo, **556 famiglie / 797 versioni**;
- convertitore: selezione versione affidabile tramite recipe ID esatto, refresh visibile e alternative mostrate come grammi equivalenti + densità kcal/100 g;
- date future: calendario e scorciatoie aprono la vista di lettura della giornata; la modifica resta un'azione esplicita;
- grafica: palette pastello più ricca e nuovo logo TataDiet Supercharged;
- baseline alimentare C.2 invariato byte-per-byte.

Per il dettaglio vedere `V6_0_1_RELEASE_NOTES.md`.

## V6.0.0

Punti principali:

- 180 giorni / 864 pasti curati con regole rolling su uova, latticini, avocado, vegetali, pasta/riso, varietà e stagionalità;
- 556 famiglie ricetta e 797 versioni a porzione fissa;
- planner V6 800–2600 kcal con tolleranza e infeasibilità esplicita;
- convertitore ingredienti read-only con quantità equivalenti a pari kcal e delta nutrizionali;
- cambio pasto con ricerca per ingrediente e preview dei constraint;
- Diario con semafori, storico, commenti e pasti manuali;
- IndexedDB e backup schema 2;
- gate di release integrato A–H.

Per il dettaglio vedere `V6_RELEASE_NOTES.md` e `V6_PHASE_H_SPEC.md`.

---

## Archivio release precedenti

## TataDiet 5.2.1 (archivio)

TataDiet è una PWA statica e local-first per gestire un piano alimentare su turni. La release **5.2.1** è una patch compatibile con V5.2.0. Corregge il recupero del calendario personale nel riequilibrio e rende la pagina Oggi più compatta e coerente con le sigle G/N/SN/R1/R2/M/P.

## Patch 5.2.1

### Riequilibrio: recupero automatico del calendario personale

La pagina Preferenze non dipende più esclusivamente da `activePlanInstanceId`. Se la data iniziale è già configurata, TataDiet:

1. recupera un piano personale esistente anche se il riferimento attivo manca;
2. riattiva il piano corrispondente alla data iniziale;
3. se necessario materializza il piano effettivo dalla data già salvata;
4. apre normalmente il riequilibrio senza chiedere di configurare di nuovo il calendario.

La stessa logica di recupero è usata anche dalle viste del piano effettivo e dalla programmazione ricette.

### Oggi più compatto

La testata di `/oggi/` ora contiene soltanto:

```text
Versione V5.2.1 · piano alimentare di oggi
Oggi
```

La card del turno mostra in ordine:

- sigla UI colorata (`G`, `N`, `SN`, `R1`, `R2`, `M`, `P`);
- data descrittiva;
- nome completo del turno (`Turno giorno`, `Turno notte`, `Smonto`, ecc.);
- orario del turno, quando disponibile.

Il fallback statico usa le stesse sigle e non mostra D1/D2. Sono stati ridotti padding, titoli, distanze tra sezioni e spazio prima delle preparazioni 48h.

## Novità 5.2

### Riequilibra piano dalle Preferenze alimentari

Dopo aver impostato frequenze e limiti alimentari, la pagina `/preferenze/` può analizzare:

- prossima giornata;
- prossimi 7 giorni;
- prossimi 30 giorni;
- tutto il piano futuro.

Il motore considera il periodo nel suo insieme, i pasti bloccati, il tipo di turno, le preferenze alimentari e il profilo nutrizionale dei pasti. Prima di scrivere nel calendario mostra una preview completa; ogni sostituzione può essere selezionata o esclusa. Le modifiche confermate vengono salvate come **una singola operazione annullabile**.

### Programma una ricetta nel calendario

Da una ricetta base o personale è disponibile **Programma nel calendario**.

Percorso:

```text
/ricette/programma/
```

Si può scegliere quante volte inserire la ricetta e il periodo:

- prossimi 7 giorni;
- prossimi 30 giorni;
- resto del piano.

TataDiet propone date distinte e pasti compatibili, indica giorno/turno, pasto sostituito, nuova ricetta, porzione e scostamento nutrizionale. Prima della conferma si possono accettare tutte le proposte o solo alcune date. L'applicazione finale è atomica e supporta undo/redo.

### Navigazione semplificata

La navigazione principale non contiene più `Piano`.

Sono invece sempre disponibili:

```text
Oggi
Calendario
Ricette
Ingredienti / Alimenti
Spesa
Preferenze
Utilità
```

La sezione Piano resta raggiungibile dal fondo della pagina Calendario come archivio del programma base.

### Oggi riordinato

La pagina `/oggi/` segue ora questa gerarchia:

1. tipo di giornata;
2. prossimo pasto;
3. pasti nella data civile;
4. valori nutrizionali;
5. preparazioni nelle prossime 48 ore.

La precedente card “Calendario attivo” è stata rimossa.

### Spesa per date come vista principale

`/spesa/` apre direttamente la spesa per intervallo civile. Alla prima apertura calcola automaticamente **la spesa di oggi**.

Preset immediati:

- Oggi;
- Domani;
- Prossime 48 ore;
- Prossimi 5 giorni;
- Prossimi 7 giorni.

I preset compilano il date picker e aggiornano la lista nella stessa pagina. La card “Intervallo selezionato” viene mostrata sotto il selettore delle date. Le vecchie liste per ciclo/variante restano disponibili come collegamento secondario in fondo pagina.

## Funzioni V5.1 mantenute

### Tipi giornata

| Codice interno | Nome UI | Sigla | Colore |
|---|---|---|---|
| D1 | Giornata | G | ocra |
| D2 | Notte | N | blu intenso |
| D3 | Smonto | SN | azzurro |
| D4 | Riposo 1 | R1 | verde |
| D5 | Riposo 2 | R2 | verde |
| M | Mattino | M | giallo tuorlo |
| P | Pomeriggio | P | rosso intenso |

D1-D5 restano codici interni per compatibilità. `M` e `P` usano il profilo dietistico di Giornata; non introducono orari di turno inventati.

### Gestisci giornata

`/calendario/gestisci/` resta il flusso consigliato per modifiche rapide: tipo giorno, menu adattato/mantenuto/personalizzato, aderenza, giornata libera, inserimento/rimozione/posticipo e conferma finale unica.

### Preferenze alimentari

Supportate:

- Uova;
- Latte e yogurt;
- Formaggi;
- Affettati;
- Pesce;
- Legumi;
- Carne rossa.

Livelli:

```text
Più spesso
Normale
Meno spesso
Raramente
Mai
```

Ogni famiglia può avere anche un massimo di occasioni ogni 7 giorni. Una occasione corrisponde a un pasto. Queste preferenze influenzano le proposte automatiche ma non impediscono la scelta manuale di una ricetta.

## Architettura

```text
Dataset base immutabile
+ IndexedDB personale
+ calendario effettivo
+ ricette/versioni assegnate
+ porzioni
+ preferenze alimentari
+ riequilibrio / programmazione ricette
= piano effettivo
```

Database e schema restano compatibili:

```text
tatadiet-v5
DB_VERSION = 1
SCHEMA_VERSION = 1
```

La V5.2 non richiede una migrazione distruttiva della V5.0/V5.1.

## Percorsi principali

```text
/oggi/
/diario/
/calendario/
/calendario/gestisci/
/calendario/modifica/
/calendario/componi/
/preferenze/
/preparazioni/
/ingredienti/
/ricette/
/ricette/studio/
/ricette/programma/
/spesa/
/spesa/cicli/
/cerca/
/strumenti/
```

## Build e QA

Non modificare manualmente `docs/`.

```bash
./build.sh
./v5_2.sh
```

`./qa.sh` richiama il gate V5.2.

QA browser contro un deploy:

```bash
python3 scripts/qa_v5_2.py --base-url https://MatColombo.github.io/TataDiet
```

## Gate finale 5.2.1

```text
592 pagine HTML
44.713 link/risorse/frammenti
0 errori
0 warning
650 risorse offline
17.120.878 byte offline
```

Accessibilità statica:

```text
592 pagine
1.187 immagini
2.220 pulsanti
21.033 link
2.217 controlli form
0 errori
0 warning
```

Stress del calendario: 96 operazioni consecutive con undo e redo completi.

QA Chromium end-to-end: **23/23 controlli V5.2 superati**. La patch aggiunge inoltre un test dedicato al recupero del calendario con `activePlanInstanceId` mancante e alla resa compatta/colorata della card Oggi.

## Pubblicazione GitHub Pages

```text
Settings → Pages
Deploy from a branch
Branch: main
Folder: /docs
```

## Persistenza e privacy

TataDiet non richiede account o backend. Ingredienti, ricette, preferenze, calendario, cronologia e modifiche restano nel browser. Per trasferire i dati usare **Utilità → Backup JSON**.

## Limiti

- La sincronizzazione fra dispositivi resta manuale tramite export/import JSON.
- Il riequilibrio è un supporto di pianificazione e non sostituisce indicazioni cliniche o prescrizioni nutrizionali.
- La programmazione casuale è deterministica rispetto al seed interno della proposta e privilegia compatibilità e vicinanza nutrizionale; l'utente conferma sempre le sostituzioni.
- La prova standalone su hardware iOS/Android reale resta raccomandata dopo il deploy.

## Baseline dati V6 in sviluppo

Il baseline dati corrente resta quello della Fase C.2: 3 porzioni di formaggi conteggiati per ogni finestra mobile di 7 giorni (latte/yogurt/kefir esclusi), almeno 2 tipologie diverse e massimo 1 al giorno; 2 porzioni di avocado da 75 g per ogni finestra mobile. Specifica e risultati: `V6_PHASE_C2_SPEC.md`, `V6_PHASE_C2_GUIDELINES.md`, `V6_PHASE_C2_FINDINGS.md`.

La Fase D aggiunge il layer runtime `Ingredient Intelligence` senza cambiare il baseline: conversione ingrediente READ-only a pari kcal, delta nutrizionale, ranking greedy compatibile, ricerca esplicita e evaluator condiviso dei constraint V6. Vedi `V6_PHASE_D_SPEC.md`, `V6_PHASE_D_FINDINGS.md` e gate `./v6_phase_d.sh`.

La Fase E aggiunge il planner V6 constraint-aware: target 800–2600 kcal, default ±5%, serving automatico fisso 1.0, `infeasible` esplicito, preservazione dei gate C.2 e pianificazione su intervallo. `Componi giornata` e `Gestisci giornata` usano il nuovo planner. È stata inoltre corretta la regressione prestazionale del vecchio stress strutturale, che torna a superare 96 operazioni con undo/redo completo. Vedi `V6_PHASE_E_SPEC.md`, `V6_PHASE_E_FINDINGS.md` e gate `./v6_phase_e.sh`.

### V6 Fase F — UX pianificazione

La Fase F rende visibili i servizi D/E senza cambiare il baseline C.2:

- convertitore ingredienti READ-only nelle pagine ricetta, con equivalenza kcal, delta nutrizionale, suggerimenti greedy e ricerca libera;
- cambio pasto ricercabile anche per ingrediente/alias, con preview rolling/energia e gate V6 completo prima del salvataggio;
- porzioni manuali fisse a 1.0 nel Compositore;
- accessi rapidi da Oggi e Gestisci giornata alle date future.

Documentazione: `V6_PHASE_F_SPEC.md`, `V6_PHASE_F_FINDINGS.md`. Gate: `./v6_phase_f.sh`.


### V6 Fase G — Diario

La Fase G aggiunge `/diario/`: calendario mensile con semafori, riepilogo 7/30 giorni, registrazione rapida dei pasti pianificati, dettagli di sostituzioni/pasti effettivi, pasti manuali fuori ricettario e commento giornaliero. Il Diario e separato dal piano effettivo e congela lo snapshot della giornata al primo salvataggio.

IndexedDB e backup passano allo schema 2 con `diaryDays`. Il baseline alimentare C.2 non cambia. Documentazione: `V6_PHASE_G_SPEC.md`, `V6_PHASE_G_FINDINGS.md`. Gate: `./v6_phase_g.sh`.
