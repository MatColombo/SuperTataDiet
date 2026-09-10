# TataDiet — memoria tecnica canonica

## Stato corrente

- Versione stabile: **6.0.2**
- Data release: **9 settembre 2026**
- Distribuzione: sito statico/PWA da `docs/`, compatibile con GitHub Pages project site
- Persistenza: IndexedDB `tatadiet-v5`
- DB version: 2
- Schema domain/backup: 2
- Dataset base: `tatadiet-base-v2`
- Fonte autorevole: `source_data/Piano_alimentare_revisionato_6_mesi_fibra_moderata.xlsx`

## Conteggi base

```text
6 cicli
36 varianti
180 giorni base
864 pasti/spuntini base
556 famiglie ricetta
797 versioni ricetta base
131 ingredienti base
```

I conteggi HTML/QA correnti sono prodotti da `./v5_2.sh`; la regressione generale è in `qa/v5.2/` e la patch mirata in `qa/v5.2.1/`.

## Principio architetturale

```text
BASE IMMUTABILE
+ DATI PERSONALI INDEXEDDB
+ CALENDARIO EFFETTIVO
+ VERSIONI RICETTA ASSEGNATE
+ PORZIONI DELLE OCCORRENZE
+ PREFERENZE ALIMENTARI
= PIANO EFFETTIVO
```

Il dataset base non viene modificato dal browser. `docs/` è output generato e non va modificato manualmente.

## Nomenclatura giornate V5.1

Internamente il dataset base conserva D1-D5 per compatibilità. La UI usa sempre:

| Interno | UI | Sigla | CSS | Profilo alimentare |
|---|---|---|---|---|
| D1 | Giornata | G | d1 / ocra | D1 |
| D2 | Notte | N | d2 / blu intenso | D2 |
| D3 | Smonto | SN | d3 / azzurro | D3 |
| D4 | Riposo 1 | R1 | d4 / verde | D4 |
| D5 | Riposo 2 | R2 | d5 / verde | D5 |
| M | Mattino | M | m / giallo tuorlo | D1 |
| P | Pomeriggio | P | p / rosso intenso | D1 |

Colori canonici:

```text
G  #a66a21
N  #173b83
SN #58a9d6
R1 #3e8a59
R2 #3e8a59
M  #e5a700
P  #b6242d
```

M e P sono nuovi tipi effettivi ammessi nel calendario personale. Non hanno orari fissi perché non sono stati forniti; `defaultShift(M/P)` mantiene `startTime/endTime = null`. Il Compositore mappa M/P al profilo D1 per slot, kcal di riferimento e proposta menu.

Il mapping UI autorevole è `static/assets/js/v5-day-types.js`; lato build è replicato da `SHIFT_INFO`/`DAY_UI` in `scripts/build_site.py`.

## Gestisci giornata

Percorso primario: `/calendario/gestisci/`.

È la UX consigliata per il lavoro quotidiano. Contiene:

1. calendario mensile navigabile;
2. selettore G/N/SN/R1/R2/M/P;
3. scelta menu `adapt / keep / personal`;
4. sostituzione dei singoli piatti in modalità personal;
5. aderenza;
6. FREE, postpone, insert, remove;
7. anteprima impatto;
8. una sola conferma finale.

Regola: quando cambia tipo di giornata, `menuMode` passa automaticamente a `adapt`.

Le modifiche restano in memoria finché l'utente non conferma. `v5-plan-store.commitState()` salva lo stato finale come **una singola operationRecord**, quindi undo/redo è atomico rispetto alla modifica composta.

La pagina `/calendario/modifica/` resta come **Gestione avanzata** per CUSTOM e operazioni di basso livello. `/calendario/componi/` resta il Compositore completo.

Bug V5.1 già corretto: entrando in Gestisci giornata su FREE/CUSTOM/OFF, la bozza conserva il tipo reale e non converte implicitamente a Giornata.

## Preferenze alimentari

Percorso: `/preferenze/`.
Setting IndexedDB: `foodPreferencesV1`, schemaVersion 1.

Famiglie iniziali:

```text
eggs        Uova
milkYogurt  Latte e yogurt
cheese      Formaggi
coldCuts    Affettati
fish        Pesce
legumes     Legumi
redMeat     Carne rossa
```

Livelli:

```text
more normal less rare never
```

Ogni gruppo supporta `maxPer7Days` opzionale. Una occasione è un **pasto** che contiene il gruppo. La finestra usa i 3 giorni precedenti e 3 successivi rispetto alla data target; durante la generazione di un menu il contatore viene aggiornato anche per i pasti appena selezionati nello stesso giorno.

Semantica:

- `more`: bonus ranking;
- `normal`: neutro;
- `less`: penalità crescente;
- `rare`: penalità maggiore;
- `never`: non eleggibile automaticamente;
- limite raggiunto: non eleggibile automaticamente;
- scelta manuale: sempre possibile, salvo futuri vincoli clinici separati.

Classificazione: `v5-preferences-core.js` usa prima gli ingredienti effettivi della `recipeVersion`; il titolo ricetta è solo fallback quando non esistono righe ingrediente. I nomi arrivano dal catalogo ingredienti caricato in `v5-composer-store.library()`.

Casi espliciti verificati: uovo/albume, yogurt/kefir/skyr, mozzarella/ricotta/grana/feta/fiocchi di latte/primosale; latte di cocco e bevande vegetali nominate come latte non vengono trattate automaticamente come latticini.

Le preferenze influenzano il Compositore completo e il menu adattato da Gestisci giornata.

## IndexedDB e versionamento

Store:

```text
meta
settings
ingredients
ingredientRevisions
recipes
recipeVersions
planInstances
calendarDays
operations
shoppingChecklists
```

Regole V5 invarianti:

- record base immutabili;
- ingredienti personali con revisioni immutabili;
- ricette personali con versioni immutabili;
- ogni pasto conserva `recipeVersionId` e `portionMultiplier`;
- lo storico non viene ricalcolato silenziosamente;
- una nuova modifica dopo undo elimina il ramo redo.

V5.1 mantiene DB/schema 1. `currentAppVersion` viene aggiornato a 5.1.0 senza riscrivere record personali.

## Piano effettivo

Tipi ammessi:

```text
D1 D2 D3 D4 D5 M P CUSTOM OFF FREE
```

Aderenza:

```text
planned followed partial not-followed not-applicable
```

`not-followed` non sposta la sequenza. FREE svuota il menu senza spostare il futuro. Insert/remove/postpone restano operazioni strutturali.

Home, Oggi, Preparazioni 48h, Spesa, Ricerca e ICS leggono il piano effettivo. La spesa deriva dalle righe ingrediente della versione ricetta effettiva scalate per porzione; i pasti oltre mezzanotte appartengono alla data civile di consumo.

ICS usa le sigle UI nei SUMMARY/CATEGORIES; M/P senza orario sono eventi all-day.

## Backup

Formati:

```text
full
recipes
calendar
settings
```

Nuovi backup: `appVersion = 5.2.1`. Backup V5.0/schema 1 e stesso dataset base restano importabili con warning. Le preferenze sono presenti in `settings`, quindi nei backup `full` e `settings`.

Import conserva checksum SHA-256, anteprima, controllo dataset, conflitti e rollback.

## PWA/offline

- service worker scope-safe per GitHub Pages;
- cache core atomica;
- query offline gestite con `ignoreSearch`;
- Gestisci giornata e Preferenze sono core offline;
- offline pack completo facoltativo;
- IndexedDB non viene cancellato dagli aggiornamenti SW;
- shortcut manifest del calendario apre Gestisci giornata.

## Build e QA

Build:

```bash
./build.sh
```

Gate corrente V5.2.1:

```bash
./v5_2.sh
# oppure ./qa.sh
```

QA browser corrente:

```bash
python3 scripts/qa_v5_2.py --base-url <root-pubblicata>
```

Controlli specifici V5.1 preservati:

- nessun D1-D5 visibile nelle 590 pagine HTML;
- 7 tipi UI e palette canonica;
- M/P validi nello schema e nel piano;
- M/P usano profilo alimentare Giornata;
- cambio tipo propone menu adattato;
- conferma unica via `commitState`;
- preferenze conteggiate per pasto;
- riconoscimento famiglie dagli ingredienti;
- `never`/limite escludono solo le proposte automatiche;
- backup include preferenze;
- Gestisci/Preferenze funzionano offline;
- nessun overflow mobile.

## Pubblicazione

GitHub Pages:

```text
branch main
folder /docs
```

## Limiti / backlog

- nessuna sincronizzazione cloud/account;
- orari esatti di Mattino/Pomeriggio non definiti: usare CUSTOM quando servono;
- preferenze alimentari non equivalgono a allergie/intolleranze cliniche;
- possibile futuro: preset preferenze, statistiche di frequenza, import turni da calendario, dispensa e batch cooking.

Qualunque V5.3/V6 deve partire da questa memoria e preservare backup/IndexedDB o fornire una migrazione esplicita e testata.

## Gate finale V5.1.0

Release validata il 2 settembre 2026: 590 HTML, 41.327 link/risorse/frammenti, 0 errori e 0 warning; 645 risorse offline (16.664.804 byte). Audit accessibilita: 590 pagine, 1.183 immagini, 2.196 pulsanti, 19.497 link, 2.208 controlli form, 0 errori e 0 warning. Stress: 96 operazioni con undo/redo completo. QA Chromium: 20 controlli V5.1 superati, inclusi palette, M/P, cambio tipo con menu adattato, preferenze, backup, offline e mobile.


## Estensione V5.2.0

La V5.2 mantiene `DB_VERSION = 1` e `SCHEMA_VERSION = 1`; non aggiunge object store e non riscrive i record personali esistenti.

### Riequilibrio massivo

Percorso: `/preferenze/`. Il modulo `v5-planning-core.js` espone `buildRebalanceProposal()` e `applyProposals()`. Intervalli supportati: prossima giornata, 7 giorni, 30 giorni, resto del piano. Il motore valuta l'intero periodo, preserva i pasti `locked`, applica i limiti delle preferenze su finestre di 7 giorni e cerca sostituzioni nutrizionalmente vicine. L'utente seleziona le proposte da applicare; `planStore.commitState(..., 'rebalance-preferences')` salva l'insieme come una singola operazione undo/redo. Nessuna giornata passata viene modificata.

### Programmazione ricetta

Percorso: `/ricette/programma/`. Disponibile da ricette base e personali. Intervalli: 7 giorni, 30 giorni, resto del piano. `buildRecipeScheduleProposal()` cerca pasti compatibili, usa date distinte, adegua `portionMultiplier` per mantenere vicino il profilo nutrizionale e produce una preview con turno, pasto sostituito e distanza nutrizionale. Applicazione selettiva tramite una singola operation `schedule-recipe`.

### UX navigazione e pagine operative

- toolbar desktop/mobile: Oggi, Calendario, Ricette, Ingredienti/Alimenti, Spesa, Preferenze, Utilità; Piano rimosso dalla toolbar;
- Piano resta link secondario in fondo a `/calendario/`;
- `/oggi/`: tipo giornata → prossimo pasto → pasti data civile → nutrienti → 48h; rimossa card Calendario attivo;
- `/spesa/`: route primaria per date, default oggi, preset Oggi/Domani/48h/5gg/7gg;
- `/spesa/cicli/`: archivio liste ciclo/variante raggiungibile dal fondo di Spesa.

### Bug V5.2 corretti durante QA

- `v5-planning-core.js` deve essere caricato dopo `v5-composer-core.js`; l'ordine precedente rendeva indisponibile il riequilibrio in browser;
- radio della selezione periodo scheduler ridotti a 1px per evitare overflow documentale su mobile;
- `distance` viene conservato nei candidati dello scheduler per evitare `NaN%` nella descrizione dello scostamento nutrizionale.

## Gate finale V5.2.0

Release validata il 2 settembre 2026: 592 HTML, 44.713 link/risorse/frammenti, 0 errori e 0 warning; 650 risorse offline (17.113.344 byte). Audit accessibilita: 592 pagine, 1.187 immagini, 2.220 pulsanti, 21.033 link, 2.217 controlli form, 0 errori e 0 warning. Stress: 96 operazioni con undo/redo completo. QA Chromium: 23/23 controlli superati, inclusi riequilibrio con selezione parziale, programmazione ricetta con selezione parziale, spesa date/preset, ordine Oggi, offline e mobile senza overflow.

## Patch V5.2.1

Release del 2 settembre 2026. DB e schema restano invariati (`tatadiet-v5`, DB 1, schema 1).

### Recupero del piano attivo

`v5-plan-store.activeBundle()` non considera più `activePlanInstanceId` come unico riferimento autorevole. Se il setting manca o punta a un record non disponibile:

1. legge `planInstances`;
2. preferisce il piano con `startDate == planStartDate`;
3. in alternativa usa il record con `status=active`, poi il più recente;
4. riattiva il record se necessario;
5. ripristina `activePlanInstanceId`.

`v5-balance.js` e `v5-effective-store.js` possono inoltre materializzare un piano dalla `planStartDate`/data legacy già configurata caricando `plan-template.base.v1.json`. La programmazione ricette usa lo stesso fallback. Questo corregge il caso reale in cui il calendario era visibile/configurato ma il riequilibrio mostrava “Configura prima il calendario personale”.

### Oggi V5.2.1

La pagina `/oggi/` ha header compatto: `Versione V5.2.1 · piano alimentare di oggi` + `Oggi`, senza testo descrittivo. La card turno usa sempre `dayTypes.short()` e mostra sigla colorata, data, nome completo del turno e orario. Il fallback di `calendar.js` usa anch'esso le sigle UI, quindi D1/D2 non ricompaiono se il piano effettivo tarda a caricarsi. Spazi verticali, titoli sezione e card sono stati ridotti.

### Gate V5.2.1

- 592 HTML;
- 44.713 link/risorse/frammenti;
- 0 errori / 0 warning;
- 650 risorse offline;
- 17.120.878 byte offline;
- stress 96 operazioni con undo/redo completo;
- regressione Chromium V5.2: 23/23;
- test patch: recupero active plan, materializzazione da data configurata, sigla N colorata, nome `Turno notte`, nessun D2 nel contenuto, nessun overflow mobile.


## Sviluppo V6 - decisioni consolidate (8 settembre 2026)

La V6 e una revisione sostanziale del piano e **non richiede retrocompatibilita con V5**. La precedente nota che imponeva di preservare backup/IndexedDB V5 non si applica alla V6: modello dati e baseline possono essere ripuliti o sostituiti quando serve.

### Fase A

Contratto V6 e audit dei 180 giorni completati senza modificare il calendario. Regole principali: max 6 egg-equivalent/7 giorni mobili; max 4 pasti con formaggi/7 giorni e max 1/giorno, escludendo latte/yogurt/kefir; almeno 3 vere portate proteiche vegetali/7 giorni; almeno 5 pasti pasta/riso/7 giorni; warning di concentrazione, ripetizione e stagionalita. La revisione dei 180 giorni dovra essere curata intenzionalmente, uno per uno, mantenendo il contesto delle finestre mobili.

### Fase B

Catalogo esteso senza toccare il piano: 84 nuove famiglie/84 versioni, tutte a porzione fissa e non ottenute per scaling. Di queste, 40 sono nuove portate con legumi come proteina principale, 36 pasta-primary, 12 rice-primary, 68 portate principali completamente senza uova/albume e formaggi, 16 colazioni/spuntini senza uova/formaggi. Il catalogo passa da 306/547 a 390/631 famiglie/versioni. La Fase C usera questo bacino per la revisione one-shot dei 180 giorni; ulteriori ricette potranno essere create se emergono gap durante la curation.

### Fase C

Curation one-shot dei 180 giorni completata e congelata in `spec/v6/phase-c-curation.json`. Il dataset base passa a `tatadiet-base-v2`; la retrocompatibilita V5 non e richiesta. Sono stati revisionati 180/180 giorni e 864 pasti: 179 giorni modificati, 709 pasti sostituiti, 155 conservati.

Durante la curation sono state aggiunte altre 15 famiglie a porzione fissa (`v6c-`), soprattutto brunch completi ad energia piu alta senza uova/formaggi per i giorni D3/Smonto e una colazione rinforzata con yogurt escluso dal budget formaggi. Catalogo finale: 405 famiglie / 646 versioni.

Gate finale su 174 finestre mobili: 0 violazioni uova/albume, 0 latticini, 0 pasta/riso, 0 proteine vegetali principali; 0 giornate con oltre un latticino conteggiato; 0 warning di concentrazione proteica o ingredienti; 0 ripetizioni della stessa famiglia entro 7 giorni; 0 ingredienti fuori stagione. Massimo uova/albume 4.6 egg-equivalent/7d; latticini max 4/7d; pasta/riso min 5/7d e media 6.2; proteine vegetali principali min 3/7d. Energia della curation: nessun giorno oltre +/-5% dal riferimento del day-type, massimo 4.78%, mediana 0.42%.

Varieta globale: alcune ricette semplici da snack ricorrono 16-20 volte nel semestre ma con distanza minima di 8 giorni. Non e stato imposto artificialmente un tetto globale <=15 per non introdurre nuovi conflitti su ingredienti/energia. Le frequenze restano tracciate in `qa/v6-phase-c/recipe-usage.csv` e possono guidare un'ulteriore espansione snack.

Il gate riproducibile e `./v6_phase_c.sh`: ricostruzione catalogo C, applicazione curation, audit, report, build PWA, test Phase C e stress test 96 operazioni. La copia pubblicata `docs/data/v5/` e byte-identica ai file base V2, anche se i nomi file mantengono temporaneamente il suffisso `.v1.json` per evitare un cambio di path non necessario in questa fase.

### Fase C.1 — varietà reale e riutilizzabilità acquisti

Completata l'8 settembre 2026. Obiettivo: ampliare la varietà effettiva del semestre senza creare ingredienti one-shot o sprechi. Esclusi esplicitamente tofu, tempeh e seitan. Aggiunte 95 famiglie/95 versioni `v6c1-`, tutte a porzione fissa e costruite usando ingredienti già presenti nel master; catalogo 500 famiglie / 741 versioni.

Linee guida in `V6_PHASE_C1_GUIDELINES.md`: riuso severo per formaggi/confezioni deperibili, preferenza di cluster entro 4 giorni per ingredienti da batch, flessibilità per dispensa/surgelabili, almeno 90 g di componente animale nelle nuove portate principali. Nessun formaggio package-sensitive può restare come piccolo uso isolato.

Curation congelata in `spec/v6/phase-c1-curation.json`: 180/180 giorni e 864 pasti rivalutati; 131 giorni e 254 pasti modificati rispetto alla Fase C, 610 conservati, 221 occorrenze di ricette C.1. Famiglie realmente usate: 253 (Fase C: 198); massimo stessa famiglia 12 occorrenze (Fase C: 20). Slot: colazione 41 famiglie, spuntino 58, mini-pasto pre-sonno 21, pranzo 81, cena 78.

Riduzioni principali: banana 87→55, carota 78→52, spinaci 74→51, zucca 53→42, hummus 50→24, salmone 40→26, bresaola 31→16, tacchino affettato 33→16, burro di arachidi 46→32, tacchino fresco 54→45. Il tonno sale 12→32 ma ha tetto esplicito 32; lupini 23→30 con tetto 30 per evitare monoculture sostitutive.

Attivati realmente (>=6 occorrenze): barbabietola 11, castagna 16, cavoletti 14, cicoria 7, cozze 6, fave 6, gnocchi 16, indivia 26, mais 15, patata dolce 22, polpo 6, rape 6, sardine 12, semi di zucca 31, tortilla 22, trota 7. Ceci+hummus = 28,66% delle occasioni legumi; top3 frutta 46,82%; top3 verdure 30,85%.

Riuso latticini: mozzarella/primosale/feta/fiocchi/grana 0; ricotta 12 e robiola 5, entrambe con 0 occorrenze isolate entro ±4 giorni. Tutti i target batch C.1 passano la quota minima di riuso ravvicinato. Gate nutrizionale/editoriale: 0 hard, 0 soft, 0 repeat <=7g, 0 fuori stagione, 0 giorni oltre ±5% energia; max delta 4,95%.

Gate riproducibile: `./v6_phase_c1.sh`. Output QA in `qa/v6-phase-c1/`. Build/stress V5 restano verdi (96 operazioni con full undo/redo). Branding/UI applicazione resta temporaneamente 5.2.1: C.1 è una fase dati/curation, non ancora motore/UX V6.

### Fase C.2 — quota latticini e avocado

Completata l'8 settembre 2026. La policy C.2 sostituisce per il baseline standard V6 il precedente solo-limite latticini con una quota esatta: **3 porzioni di formaggi/latticini conteggiati in ogni finestra mobile di 7 giorni**, massimo 1 al giorno e almeno 2 tipologie diverse per finestra. Latte, yogurt e kefir restano esclusi da questo conteggio. Avocado: **2 porzioni da 75 g in ogni finestra mobile di 7 giorni**.

Anti-spreco: i formaggi freschi sono pianificati a coppie entro 4 giorni con grammature che chiudono confezioni plausibili (ricotta 125+125 g, robiola 50+50 g, mozzarella 62,5+62,5 g, feta 75+75 g, fiocchi di latte 100+100 g, primosale 80+80 g). Il Grana è conservabile e non richiede pairing. L'avocado e pianificato in coppie da 75+75 g entro 4 giorni. Tofu, tempeh e seitan restano esclusi.

Catalogo C.2: aggiunto ingrediente `avocado` con valori CREA e 56 famiglie/56 versioni `v6c2-` effettivamente utilizzate; catalogo finale 556 famiglie / 797 versioni. Curation congelata in `spec/v6/phase-c2-curation.json`: 133 giorni e 138 pasti modificati rispetto alla C.1.

Risultato su 174 finestre mobili: latticini rolling min=max 3; minimo 2 tipologie distinte; avocado rolling min=max 2. Distribuzione semestre: Grana 25, ricotta 10, primosale 10, robiola 8, mozzarella 8, feta 8, fiocchi di latte 8 (77 porzioni totali); avocado 52 porzioni da 75 g. Zero latticini freschi isolati oltre 4 giorni.

Tutti i gate nutrizionali/editoriali C.1 restano chiusi: 0 hard/soft violations, 0 repeat famiglia <=7 giorni, 0 fuori stagione, 0 giorni oltre +/-5% energia (max 4,77%), family cap 12, global caps/activation/batch reuse tutti OK. Top-3 frutta 46,64%, top-3 verdure 29,96%, ceci+hummus 25%.

Gate specifico: `scripts/test_v6_phase_c2.py` e `scripts/audit_v6_phase_c2.py` passano. Il vecchio stress test V5 da 96 operazioni e diventato troppo lento sul baseline ampliato e non completa entro 240 s nell'ambiente di sviluppo; una riduzione a 8 operazioni passa con undo/redo completo. Trattare questo come backlog di performance della futura fase motore, non come violazione del dataset C.2.

### Fase D — Ingredient Intelligence + constraint evaluator

Completata l'8 settembre 2026 sul baseline C.2 senza modificare i tre file base ingredienti/ricette/piano. Introdotti `v6-ingredient-intelligence-core.js`, `v6-constraint-core.js`, `v6-intelligence-store.js` e `spec/v6/phase-d-policy.json`.

Il convertitore V6 e definito READ-only: usa la `baseQuantity` della riga ricetta, calcola la quantita alternativa a pari kcal e mostra il delta di proteine/carboidrati/grassi/fibre. L'equivalenza energetica non implica equivalenza nutrizionale. Il greedy suggerisce solo alternative con stesso ruolo/famiglia compatibile e grammatura plausibile; la ricerca esplicita puo mostrare anche `energy-only` (es. riso→olio) senza suggerirli automaticamente. Ricette automatiche V6: serving fisso 1.0; `portionMultiplier != 1` e hard violation nel nuovo evaluator.

Tassonomia: 131/131 ingredienti base classificati, 0 `other`, 0 codici duplicati tra classi; 797/797 versioni ricetta profilate. Il nuovo evaluator JS riproduce sul baseline C.2: 180 giorni, 174 finestre, 0 hard, 0 soft, 0 repeat <=7g, 0 stagionalita; latticini rolling min=max 3 e avocado rolling min=max 2. `evaluateReplacement()` valuta giornata + sole finestre coinvolte e non persiste nulla.

Performance convertitore sul catalogo da 131 ingredienti: circa 0,6-0,7 ms per ranking completo nel test Node. Policy e moduli D vengono pubblicati nella PWA e inclusi offline. Gate riproducibile: `./v6_phase_d.sh` (build, regressione C.2, core D, packaging e stress smoke undo/redo). La UI del convertitore resta in F; il planner V6 usera gli stessi profili/evaluator in E.

### Fase E — planner V6 + performance

Completata l'8 settembre 2026 sul baseline C.2, senza modificare ingredienti, catalogo ricette o i 180 giorni. Introdotti `v6-planner-core.js`, `v6-planner-store.js` e `spec/v6/phase-e-policy.json`.

Contratto: target 800-2600 kcal, default +/-5%, serving automatico sempre 1.0, infeasibility esplicita. Solo gli slot della famiglia snack possono essere omessi automaticamente ai target bassi; pasti principali e locked non vengono saltati. Il planner riusa evaluator/profili D e preserva vincoli A, cap/diversita C1, quote latticini/avocado C2, stagionalita, repeat <=7d, riuso acquisti e preferenze never/maxPer7Days. Quando l'input e conforme, conserva la firma giornaliera latticini/avocado per non rompere le finestre mobili adiacenti.

Copertura testata a 800,1000,1200,1400,1600,1800,2000,2200,2400,2600 kcal usando day-type compatibili: tutte le soluzioni accettate entro +/-5%, porzioni fisse, 0 hard/soft. Un target impossibile per un determinato day-type restituisce `infeasible` con `energy_target`, non uno sforamento silenzioso. `planRange()` su piu giorni conserva il contratto rolling completo.

Integrazione minima: Componi giornata e Gestisci giornata usano il planner V6 nei flussi automatici; riequilibrio preferenze e programmazione ricetta non scalano piu automaticamente le porzioni e validano lo stato finale V6 prima del commit. La validazione UX delle singole sostituzioni manuali resta in F.

Performance: policy ricerca 52 candidati/slot, 3 stati/bucket, beam 1200, 220 finalisti. Nel gate Node: indice ~25-40 ms, mediana proposta circa 0,7-1,0 s; il P95 varia circa 1,1-2,2 s a seconda del run. Corretto inoltre `v5-plan-core.applyAction()`: il vecchio calcolo `affectedDays` riordinava/clonava il piano 180 volte per operazione. Il test storico da 96 operazioni con full undo/redo passa nuovamente in circa 5-6 s. La precedente attribuzione del timeout C2 al catalogo ampliato era quindi errata: il collo di bottiglia era nel calcolo dell'impatto strutturale.

Gate: `./v6_phase_e.sh`. QA in `qa/v6-phase-e/`. UI completa del convertitore e picker/search ingredienti resta in F.

### Fase F — UX convertitore, cambio pasto e date future

Completata l'8 settembre 2026 sul baseline C.2 senza modificare ingredienti, ricette o i 180 giorni. La Fase F espone in UI i servizi D/E e aggiunge `spec/v6/phase-f-policy.json` e `v6-recipe-converter.js`.

Le 306 pagine ricetta statiche includono ora un convertitore READ-only: si seleziona una ingredient line, si vedono fino a 12 alternative greedy compatibili e si puo cercare liberamente per nome/alias anche candidati `energy-only`. Il confronto calcola la quantita alternativa a pari kcal e mostra kcal, proteine, carboidrati, grassi, fibre e delta. Il convertitore non persiste nulla e non crea revisioni.

Compositore e Gestisci giornata cercano ricette anche per nomi/alias degli ingredienti. Il picker mostra i primi tre ingredienti e valuta localmente finestra rolling 7d + energia; gli esiti sono `7gg OK`, `Fuori kcal`, `Vincolo hard`, `Warning V6`. Prima del commit viene sempre rieseguita la validazione globale V6 tramite `plannerStore.validateDays()`.

Il vecchio campo porzione manuale del Compositore e ora read-only: aggiunte e sostituzioni persistono sempre `portionMultiplier=1`. Questo chiude l'ultimo percorso UI che poteva creare scaling incompatibile con V6.

Navigazione futura: Oggi espone Domani/+3/+7 + picker data verso Componi giornata; Gestisci giornata espone +1/+3/+7/+14 dalla data focalizzata.

Gate locale: regressioni C.2/D/E/F, stress E da 96 operazioni con full undo/redo e validazione statica. Ultima validazione: 592 HTML, 48.265 link/risorse/frammenti, 0 errori, 0 warning. Il browser smoke F e predisposto ma il Chromium gestito dell'ambiente corrente blocca navigazioni HTTP con `ERR_BLOCKED_BY_ADMINISTRATOR`; va eseguito sul deploy/ambiente browser non gestito, idealmente in Fase H.

Gate riproducibile: `./v6_phase_f.sh`. La Fase G resta dedicata al Diario e alla sua UX.


### Fase G — Diario

Completata l'8 settembre 2026. Aggiunta la pagina `/diario/` con UX orientata alla compilazione rapida: semafori pasto/giorno, riepiloghi rolling 7/30 giorni, `Segna tutti seguiti`, dettagli del pasto effettivo, pasti manuali fuori ricettario e commento giornaliero. La pagina e raggiungibile dalla navigazione principale e direttamente da Oggi sulla data visualizzata.

Semantica: pasto `followed`=verde/peso 1, `partial`=giallo/peso 0.5, `not-followed`=rosso/peso 0, `unlogged`=grigio/escluso dal punteggio. Il giorno e verde solo se tutti i pasti pianificati sono registrati e l'aderenza e >=85%; resta giallo se incompleto; e rosso se completo ma <50%. I pasti manuali/extra non abbassano da soli l'aderenza al piano.

Persistenza: IndexedDB passa a DB/schema 2 con store `diaryDays`; backup JSON passa a schema 2 e include il diario nei backup full e calendar. Al primo write di una data viene congelato lo snapshot di tutti i pasti pianificati della giornata: modifiche successive al piano non riscrivono retroattivamente lo storico del Diario. Base C.2 ingredienti/ricette/piano resta byte-identico.

Gate G: core semafori/rolling, store in-memory (snapshot freeze, status, manual meal CRUD, commento, mark-all), regressioni C.2/D/E/F, stress 96 operazioni e validazione statica. Validazione sito: 593 HTML, 51.895 link/risorse/frammenti, 0 errori/0 warning. Chromium gestito continua a bloccare navigazioni locali con `ERR_BLOCKED_BY_ADMINISTRATOR`; smoke browser F/G resta da eseguire sul deploy in H. Gate: `./v6_phase_g.sh`.

### Fase H — release TataDiet 6.0.0

Completata l'8 settembre 2026. La V6 è congelata come release `6.0.0`; il baseline alimentare C.2 non cambia (131 ingredienti, 556 famiglie/797 versioni, 180 giorni/864 pasti e hash base invariati). Branding/versione applicativa, build meta, PWA, DB metadata e backup envelope sono allineati a 6.0.0. IndexedDB/schema e backup schema restano v2; il nome tecnico DB `tatadiet-v5` viene mantenuto intenzionalmente per evitare un reset implicito dei dati locali.

Gate finale `./v6_phase_h.sh`: rebuild + regressioni C.2/D/E/F/G/H + stress 96 operazioni full undo/redo + validazione sito. Ultimo run: 593 HTML, 51.895 riferimenti, 0 errori/0 warning; stress ~2,8 s. Service worker/offline includono convertitore, Diario e policy F/G/H; manifest PWA espone shortcut Diario.

Il browser Chromium gestito nell'ambiente blocca HTTP/file con `ERR_BLOCKED_BY_ADMINISTRATOR`; senza un URL di deploy non è stato possibile eseguire un vero smoke visuale/E2E. Gli script deploy F/H e `qa/v6-phase-h/manual-review.csv` sono inclusi come verifica post-deploy esplicita. La release automatizzata/statica è PASS.


### Patch V6.0.1 — correzioni post-release (9 settembre 2026)

V6.0.1 mantiene byte-identico il baseline alimentare C.2 e corregge cinque problemi osservati nel collaudo reale. Il Diario caricava i moduli prima di `v5-effective-core/store`; l'ordine script è ora corretto. `v5-db.initialize()` esegue `ensureBaseCatalogCurrent()` per riallineare un IndexedDB proveniente dalle build intermedie C/C1/C2 al catalogo base autorevole senza cancellare record personali.

La build delle pagine ricetta usa ora `v5_data/base/recipes.base.v1.json` e genera tutte le 556 famiglie V6; tutti gli 864 pasti del piano risolvono sia `recipe_id` sia `recipe_version_id`. Il convertitore usa `data-recipe-id` come identificatore primario, aggiorna esplicitamente versione/ingredienti/alternative al cambio versione e mostra nelle card la densità energetica invece delle kcal totali, che a parità energetica sono intenzionalmente uguali.

Calendario e scorciatoie future aprono `/oggi/?date=...` come vista read-only; `Gestisci`/`Modifica i pasti` restano azioni esplicite. Refresh visuale V6.0.1: palette pastello più ricca, card cromatiche e nuovo marchio `TataDiet Supercharged` con cuore/fulmine; favicon e icone PWA rigenerate.


### Patch V6.0.2 — libertà delle modifiche manuali (9 settembre 2026)

Le azioni manuali dell'utente non sono più bloccate dai constraint V6. Gestisci giornata, sostituzione/aggiunta pasto, riequilibrio selezionato e pianificazione manuale di ricette salvano sempre se lo stato dati è strutturalmente valido; l'evaluator V6 viene usato solo per warning motivati. Le proposte automatiche del planner continuano invece a richiedere piena conformità V6 e porzioni fisse. La card Oggi usa una griglia esplicita badge/copia/azioni per evitare clipping del testo del tipo giornata.
