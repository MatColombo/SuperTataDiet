# TataDiet V6 - Fase B

## Scopo

La Fase B amplia in modo mirato il ricettario prima della revisione one-shot dei 180 giorni prevista in Fase C.

Il calendario di 180 giorni **non viene modificato** in questa fase. L'obiettivo è creare abbastanza alternative reali da poter correggere giorno per giorno il piano senza ricorrere a porzioni scalate, senza abusare di albume/formaggi e senza perdere varietà o stagionalità.

La baseline normativa e di audit resta quella congelata in `V6_PHASE_A_SPEC.md` e `spec/v6/phase-a-policy.json`.

## Principi vincolanti

1. Le nuove ricette sono nuove famiglie, non revisioni ottenute scalando porzioni esistenti.
2. Ogni nuova famiglia ha una sola versione iniziale con `servings = 1.0` e porzione fissa.
3. Le nuove portate principali introdotte in Fase B non contengono uovo, albume o formaggi.
4. Latte, yogurt e kefir possono comparire nelle colazioni/spuntini perché sono esplicitamente esclusi dal limite formaggi della Fase A.
5. I nutrienti sono calcolati esclusivamente usando gli ingredienti già presenti nel catalogo V5; la Fase B non inventa valori nutrizionali sintetici.
6. Ogni ricetta dichiara i mesi stagionali ammessi e la dichiarazione viene verificata rispetto alla stagionalità degli ingredienti.
7. Le nuove portate principali devono rimanere compatibili con l'impostazione a fibra moderata del progetto; il gate impone un massimo di 12 g di fibra per porzione.
8. Il piano `plan-template.base.v1.json` deve rimanere byte-per-byte identico alla baseline Fase A.

## Perché il catalogo corrente non è sufficiente

L'audit pre-estensione misura 306 famiglie e 547 versioni. In particolare:

- solo 3 famiglie soddisfano il criterio V6 di proteina vegetale principale;
- solo 16 famiglie hanno pasta come carboidrato principale;
- le 16 ricette di pasta correnti risultano tutte poco adatte alla nuova policy perché coinvolgono formaggi e, in diversi casi, anche albume;
- il catalogo offre molte più opzioni di riso che di pasta;
- le vere portate a base di legumi sono insufficienti per garantire 3 pasti vegetali principali in ogni finestra mobile di 7 giorni;
- il calendario attuale dipende in modo eccessivo da ricette contenenti uova/albume e formaggi.

La Fase B quindi non cerca di aumentare indiscriminatamente il numero di ricette: colma i buchi che renderebbero impossibile o monotona la revisione dei 180 giorni.

## Nuove ricette

La Fase B aggiunge **84 nuove famiglie**, ciascuna con una sola versione a porzione fissa.

| Ruolo | Nuove famiglie |
|---|---:|
| Pasta con proteina vegetale principale | 16 |
| Riso con proteina vegetale principale | 12 |
| Altre portate vegetali principali | 12 |
| Pasta con pesce/carne/pollame, senza uova/formaggi | 20 |
| Altre portate principali, senza uova/formaggi | 8 |
| Colazioni e spuntini alternativi | 16 |
| **Totale** | **84** |

Ne derivano:

- **40** nuove portate con legumi come proteina principale;
- **36** nuove portate con pasta come carboidrato principale;
- **12** nuove portate con riso come carboidrato principale;
- **68** nuove portate principali completamente libere da uova/albume e formaggi;
- **16** nuove colazioni/spuntini liberi da uova/albume e formaggi.

Le famiglie vegetali usano in modo distribuito ceci, lenticchie, cannellini, borlotti e lupini, abbinate a pasta, riso, couscous, farro, orzo, polenta, patate e verdure stagionali.

Le famiglie non vegetali aggiungono soprattutto alternative a base di tonno, sgombro, sardine, salmone, trota, merluzzo, nasello, branzino, gamberi, cozze, calamaro, pollo, tacchino e manzo, senza usare formaggio/albume come rinforzo proteico.

## Energia e fibra

Per le 68 nuove portate principali:

- minimo: 332.4 kcal;
- mediana: 435.0 kcal;
- massimo: 502.6 kcal;
- fibra massima: 11.9 g.

Le colazioni/spuntini sono validate nell'intervallo energetico definito dalla specifica di Fase B e restano a porzione fissa.

Questi intervalli non sostituiscono il futuro lavoro sulle fasce caloriche 800-2600 kcal del piano giornaliero: servono a costruire un catalogo più modulare per la successiva curation.

## Stagionalità

Ogni nuova ricetta dichiara i mesi in cui è utilizzabile. Il gate verifica che la dichiarazione non contraddica la stagionalità degli ingredienti.

Copertura minima disponibile per la futura revisione dei 180 giorni:

| Mese | Nuovi principali | Di cui vegetali | Pasta | Riso | Colazioni/spuntini |
|---|---:|---:|---:|---:|---:|
| Settembre | 35 | 21 | 18 | 6 | 15 |
| Ottobre | 62 | 36 | 32 | 11 | 15 |
| Novembre | 65 | 40 | 33 | 12 | 16 |
| Dicembre | 60 | 37 | 31 | 12 | 16 |
| Gennaio | 60 | 37 | 31 | 12 | 16 |
| Febbraio | 60 | 37 | 31 | 12 | 16 |

Settembre è volutamente il mese con la copertura più stretta ed è usato come caso limite del gate.

## Contratto dati

Le definizioni curate delle nuove ricette sono in:

`spec/v6/phase-b-recipes.json`

Lo script:

`scripts/apply_v6_phase_b_catalog.py`

le materializza in modo deterministico nel catalogo base.

Gli ID generati usano il namespace:

- `base:recipe:v6-<slug>`
- `base:recipe-version:v6-<slug>:<hash>`

Le nuove versioni hanno:

- `servings = 1.0`;
- `servings_source = explicit` per compatibilità con lo schema esistente;
- ingredient lines strutturate;
- istruzioni disponibili;
- nessuna `source_occurrence`, perché non sono ancora inserite nel piano dei 180 giorni.

## Dataset e passaggio a V2

Durante la Fase B il manifest mantiene transitoriamente `dataset_version = tatadiet-base-v1`, perché il piano dei 180 giorni è ancora quello originale e la Fase B è un'estensione catalog-only.

Non è una scelta di retrocompatibilità. La retrocompatibilità V5 non è un requisito V6.

Il passaggio al nuovo dataset V6/V2 va fatto quando la Fase C sostituirà realmente i pasti del calendario. In quel momento catalogo e piano costituiranno insieme il nuovo baseline V6.

## Audit e gate

Il comando principale è:

```bash
./v6_phase_b.sh
```

Esegue:

1. materializzazione deterministica del catalogo Fase B;
2. test specifici Fase B;
3. build della PWA;
4. regressione Fase A;
5. audit Fase A sul calendario ancora invariato;
6. audit Fase B del catalogo;
7. test contrattuale del dataset V5 aggiornato.

Output principali:

- `qa/v6-phase-b/summary.json`
- `qa/v6-phase-b/catalog-gap-matrix.csv`
- `qa/v6-phase-b/new-recipes.csv`
- `qa/v6-phase-b/seasonal-coverage.csv`
- `qa/v6-phase-b/nutrition-by-role.csv`

## Gate di accettazione

La Fase B passa soltanto se:

- vengono aggiunte esattamente 84 nuove famiglie e 84 nuove versioni;
- esiste una sola versione fissa per nuova famiglia;
- almeno 40 nuove famiglie sono vere proteine vegetali principali;
- almeno 36 sono pasta-primary;
- almeno 12 sono rice-primary;
- tutte le 68 nuove portate principali sono senza uovo/albume e senza formaggi;
- le 16 colazioni/spuntini sono senza uovo/albume e senza formaggi;
- energia e fibra rispettano i range della specifica;
- non esistono titoli duplicati o composizioni duplicate nella nuova tranche;
- la stagionalità dichiarata è valida;
- ogni mese del periodo settembre-febbraio ha almeno 35 nuovi principali e almeno 18 nuovi principali vegetali;
- il piano dei 180 giorni è identico alla baseline Fase A;
- manifest e checksum sono coerenti;
- gli schemi e i test di regressione continuano a passare.

## Confine con la Fase C

La Fase B **non decide quali ricette sostituire nei 180 giorni**.

La Fase C userà contemporaneamente:

- `qa/v6-phase-a/review-queue.csv`, che individua i giorni problematici;
- `qa/v6-phase-b/new-recipes.csv`, che descrive il nuovo bacino di sostituzione;
- i vincoli hard e soft della Fase A;
- la stagionalità della singola data;
- il contesto dei giorni precedenti e successivi.

La revisione resterà intenzionale e giorno-per-giorno, non una rigenerazione automatica del semestre.
