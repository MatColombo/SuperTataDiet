# TataDiet V6 - Fase A: contratto e audit dei 180 giorni

## Obiettivo

La Fase A non corregge ancora il piano. Congela un contratto verificabile e produce una fotografia deterministica dei 180 giorni che useremo come guida per la curation one-shot della Fase C.

Fonte autorevole dell'audit:

1. `docs/data/v5/plan-template.base.v1.json` per le 180 giornate e le 864 occorrenze;
2. `docs/data/v5/recipes.base.v1.json` per versioni ricetta e ingredient lines;
3. `docs/data/v5/ingredients.base.v1.json` per nutrienti e categorie;
4. `spec/v6/phase-a-policy.json` per le regole V6.

Titolo della ricetta e ricerca testuale non vengono usati per classificare un pasto quando esistono ingredient lines.

## Vincoli hard V6 congelati in Fase A

### Uova e albume

- massimo `6.0` egg-equivalent in ogni finestra mobile di 7 giorni;
- 1 uovo intero = 50 g = 1 egg-equivalent;
- 50 g di albume = 1 egg-equivalent;
- l'equivalenza è una regola di pianificazione TataDiet, non una conversione clinica.

### Latticini/formaggi

Sono conteggiati: feta, fiocchi di latte, grana/parmigiano, mozzarella, primosale, ricotta e robiola.

Sono esclusi dal limite: latte, yogurt e kefir.

Vincoli:

- massimo 4 pasti contenenti formaggio/latticino in ogni finestra mobile di 7 giorni;
- massimo 1 pasto contenente formaggio/latticino nella stessa giornata.

Una ricetta con due formaggi conta come una sola occorrenza, ma resta visibile nell'audit ingredienti.

### Pasta e riso

- almeno 5 pasti in ogni finestra mobile di 7 giorni;
- il pasto conta solo quando pasta o riso semplice sono la fonte glucidica primaria classificata;
- gallette di riso e noodles di riso non soddisfano il requisito.

### Proteina vegetale principale

Per il profilo standard V6 fissiamo una soglia iniziale di almeno 3 pasti principali a base di legumi in ogni finestra mobile di 7 giorni.

Sono pasti principali: pranzo, cena, brunch e pasto preturno.

Un pasto viene classificato `legumes` come proteina principale solo se contemporaneamente:

- contiene almeno 70 g di legumi/hummus nella porzione;
- i legumi forniscono almeno 6 g di proteine;
- forniscono almeno il 50% delle proteine provenienti da fonti proteiche riconosciute nella ricetta.

Questa definizione impedisce di conteggiare come "proteina vegetale principale" ricette in cui i legumi sono una piccola aggiunta e la proteina dominante è albume, carne, pesce o formaggio.

## Soft constraint

### Ripetizione ricetta

Ogni ripetizione della stessa famiglia ricetta entro i 7 giorni precedenti è un warning. Se il gap è 2 giorni o meno il warning ha priorità alta.

Non è un hard constraint: durante la revisione dei 180 giorni l'obiettivo è ridurlo fortemente senza creare sostituzioni artificiali.

### Distribuzione uova/albume

Il limite settimanale resta hard. Una singola giornata sopra 2 egg-equivalent genera però un warning di distribuzione: serve a evitare di concentrare quasi tutta la quota settimanale in uno o due pasti.

### Concentrazione fonte proteica

Una famiglia proteica primaria che supera il 40% dei pasti principali della finestra, con almeno 3 occorrenze, genera un warning di concentrazione.

### Bilanciamento pasta/riso

Il requisito hard resta almeno 5 pasti complessivi pasta/riso per finestra. Come obiettivo di varietà la finestra genera un warning se contiene meno di 2 pasti con pasta primaria o meno di 2 con riso primario. In questo modo non possiamo soddisfare il requisito quasi esclusivamente con il riso, come accade spesso nel dataset corrente.

### Concentrazione ingrediente

Un ingrediente non di dispensa/base che compare in più di 4 pasti nella stessa finestra e in almeno 3 giorni distinti genera un warning.

Pasta e riso semplici sono esclusi da questo warning perché la V6 richiede intenzionalmente una loro presenza frequente; la varietà verrà valutata a livello di ricetta, condimento e fonte proteica.

### Stagionalità

La stagionalità è un warning, non un hard failure. Si applica agli ingredienti freschi esplicitamente mappati nel profilo italiano. Surgelati, conserve, prodotti importati o ingredienti considerati disponibili tutto l'anno sono esclusi.

Il periodo del piano base è settembre-febbraio e usa il campo `month` già presente nelle 180 giornate.

## Energia

La Fase A registra il delta rispetto ai riferimenti V5 per tipo giornata ma non congela una tolleranza hard.

Motivo: la V6 dovrà essere testata manualmente su target circa 800-2600 kcal e il target/tolleranza effettivi devono provenire dalla configurazione dell'utente. L'audit dei 180 giorni non deve confondere il riferimento storico con il futuro contratto del planner.

## Output dell'audit

`python3 scripts/audit_v6_phase_a.py`

scrive in `qa/v6-phase-a/`:

- `summary.json`: fotografia globale e conteggi violazioni;
- `window-audit.csv`: tutte le 174 finestre mobili da 7 giorni;
- `day-audit.csv`: metriche e problemi di ogni giornata;
- `review-queue.csv`: giornate ordinate per priorità di revisione;
- `recipe-classification.csv`: classificazione semantica di ogni versione ricetta usata;
- `ingredient-frequency.csv`: frequenza ingredienti nell'intero piano;
- `seasonality-audit.csv`: singole occorrenze fuori stagione;
- `violations.json`: violazioni hard e warning soft con riferimenti puntuali.

## Regola per la Fase C

L'unità editoriale resta il singolo giorno, ma ogni correzione deve essere valutata nel contesto della finestra mobile. La review queue è un ordine di lavoro, non autorizza a correggere una giornata ignorando i sei giorni prima e dopo.
