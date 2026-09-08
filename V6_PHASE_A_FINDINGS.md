# TataDiet V6 - Fase A: risultati baseline

## Stato

Fase A completata sulla baseline V5.2.1 senza modificare i 180 giorni. L'audit usa quantità e ingredient lines reali delle 547 versioni ricetta presenti nel piano.

## Baseline analizzata

- 180 giorni
- 864 pasti/spuntini
- 174 finestre mobili da 7 giorni
- 306 famiglie ricetta
- 547 versioni ricetta usate
- 130 ingredienti

## Hard constraint V6 contro il piano attuale

| Regola | Baseline attuale | Esito |
|---|---:|---:|
| Uova/albume <= 6 eq / 7 giorni | mediana 18.0; media 17.62; min 2.6; max 34.2 | 167/174 finestre KO |
| Formaggi/latticini <= 4 pasti / 7 giorni | mediana 15; media 14.75; min 7; max 23 | 174/174 finestre KO |
| Formaggi/latticini <= 1 pasto / giorno | massimo 5 pasti nello stesso giorno | 117/180 giorni KO |
| Pasta/riso primari >= 5 pasti / 7 giorni | mediana 5; media 5.47; min 2; max 10 | 49/174 finestre KO |
| Proteina vegetale principale >= 3 pasti / 7 giorni | mediana 0; media 0.12; max 1 | 174/174 finestre KO |

La baseline non e quindi correggibile con poche sostituzioni locali. La revisione dei 180 giorni deve essere strutturale.

## Uova e albume

Nel piano ci sono 198 pasti con uovo e/o albume.

- albume: 130 pasti, 102 giorni distinti, 13.620 g complessivi;
- uovo intero: 119 pasti, 90 giorni distinti, 9.240 g complessivi;
- massimo in una singola giornata: 9.6 egg-equivalent;
- 73 giornate superano il warning di distribuzione di 2 egg-equivalent nella stessa giornata.

Il problema principale non sono soltanto frittate e uova sode. L'albume compare come rinforzo proteico in primi, riso, patate e ricette con legumi. Nella revisione V6 questa pratica deve essere fortemente ridotta.

## Latticini/formaggi

379 dei 864 pasti contengono almeno un formaggio/latticino soggetto al limite. Latte, yogurt e kefir sono esclusi da questo conteggio.

Occorrenze per ingrediente:

| Ingrediente | Pasti |
|---|---:|
| Ricotta | 89 |
| Primosale | 80 |
| Grana/Parmigiano | 75 |
| Mozzarella | 46 |
| Feta | 38 |
| Robiola | 38 |
| Fiocchi di latte | 19 |

Distribuzione per slot:

- spuntino: 114;
- colazione: 81;
- pranzo: 60;
- cena: 42;
- spuntino notturno: 32;
- mini-pasto pre-sonno: 19;
- pasto preturno: 18;
- brunch: 13.

Questo indica che nella Fase B/C non bastera sostituire alcuni secondi: serviranno molte alternative per colazioni e soprattutto spuntini non basati su formaggio.

## Proteine vegetali

La classificazione semantica trova soltanto 3 pasti realmente qualificabili come portata con legumi come proteina principale nell'intero semestre, tutti a pranzo.

Le tre versioni sono:

- Pasta con crema di lenticchie e carote;
- Patate con crema di borlotti e finocchi;
- Riso con crema di cannellini e bietole.

Le altre ricette con ceci, lenticchie, borlotti, cannellini o piselli sono spesso dominate dall'albume. Esempi correnti includono 160 g di albume in ricette con 70-90 g di legumi.

Questa e la lacuna piu netta del ricettario V5 e richiedera un numero consistente di nuove ricette vere a base di legumi.

## Pasta e riso

Nel semestre risultano 138 pasti in cui pasta o riso sono realmente il carboidrato principale:

- riso: 122 pasti;
- pasta: 16 pasti.

Il requisito combinato di almeno 5/7 giorni fallisce in 49 finestre. Ma anche quando passa, il mix e sbilanciato: 154 delle 174 finestre hanno meno di 2 pasti con pasta primaria; soltanto 4 finestre hanno meno di 2 pasti con riso.

Per questo la Fase A introduce anche un warning soft di equilibrio: almeno 2 pasta e almeno 2 riso nella finestra, oltre al minimo hard combinato di 5.

## Fonti proteiche principali nei pasti principali

Classificazione attuale su pranzo/cena/brunch/pasto preturno:

| Famiglia | Pasti |
|---|---:|
| Pollame | 126 |
| Uova/albume | 78 |
| Pesce | 71 |
| Carne rossa/coniglio/maiale | 31 |
| Non classificata | 22 |
| Affettati | 18 |
| Formaggio | 11 |
| Legumi | 3 |

Il piano e quindi fortemente centrato su pollame + uova, con quasi nessun ruolo strutturale per i legumi.

## Ripetibilita

- 216 ripetizioni della stessa famiglia ricetta entro 7 giorni;
- 18 ripetizioni con gap <= 2 giorni.

Famiglie piu frequentemente coinvolte nei repeat warning:

- Latte e gallette di riso: 11;
- Primosale e gallette di riso: 10;
- Frutta e Grana: 10;
- Mini panino bianco con bresaola: 10;
- Frutta e nocciole: 9;
- Crackers e ricotta: 9;
- Piadina mini con ricotta: 8;
- Crackers e primosale: 8.

La ripetitivita e concentrata soprattutto negli spuntini/mini-pasti, che diventano quindi una priorita nella creazione di nuove ricette.

## Concentrazione ingredienti

L'audit genera warning quando un ingrediente non escluso compare in piu di 4 pasti della stessa finestra di 7 giorni e in almeno 3 giorni distinti.

Gli ingredienti che piu spesso generano finestre concentrate sono:

- pane bianco;
- albume;
- uovo;
- patata;
- latte;
- primosale;
- ricotta;
- grana;
- mela;
- pollo.

Questa metrica non e un divieto. Serve a evidenziare sequenze monotone durante la revisione editoriale.

## Stagionalita

Sono state trovate 39 occorrenze fuori stagione secondo la mappa italiana soft della Fase A.

I casi principali sono:

- cetriolo in ottobre-febbraio;
- pomodoro in novembre-febbraio;
- zucchina in novembre-febbraio;
- funghi in gennaio.

La stagionalita resta un warning: conserve, surgelati, importati o ingredienti esplicitamente year-round non sono trattati come errore hard.

## Implicazioni operative per le fasi successive

La Fase B dovra espandere il ricettario in modo mirato, non casuale. Le priorita evidenziate dalla baseline sono:

1. vere portate principali con ceci, lenticchie, fagioli, piselli e altri legumi senza albume di rinforzo;
2. piu primi di pasta, con forte aumento rispetto alle sole 16 occorrenze correnti;
3. spuntini e mini-pasti senza formaggi;
4. colazioni senza formaggi e senza dipendenza da uova;
5. piatti principali senza albume nascosto;
6. alternative stagionali autunno/inverno;
7. maggiore diversita delle fonti proteiche e dei carboidrati;
8. nuove famiglie ricetta, non semplici varianti di grammatura della stessa preparazione.

## Deliverable tecnici

La Fase A aggiunge:

- `spec/v6/phase-a-policy.json` - contratto machine-readable;
- `scripts/audit_v6_phase_a.py` - audit deterministico;
- `scripts/test_v6_phase_a.py` - test del contratto/classificatore;
- `v6_phase_a.sh` - gate della fase;
- `V6_PHASE_A_SPEC.md` - semantica delle regole;
- `qa/v6-phase-a/summary.json`;
- `qa/v6-phase-a/day-audit.csv`;
- `qa/v6-phase-a/window-audit.csv`;
- `qa/v6-phase-a/review-queue.csv`;
- `qa/v6-phase-a/recipe-classification.csv`;
- `qa/v6-phase-a/ingredient-frequency.csv`;
- `qa/v6-phase-a/seasonality-audit.csv`;
- `qa/v6-phase-a/violations.json`.

`./v6_phase_a.sh` termina con test e audit entrambi OK. Il fatto che il piano attuale abbia molte violazioni e il risultato atteso della baseline, non un fallimento del gate.
