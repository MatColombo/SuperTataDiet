# TataDiet V6 - Fase B: risultati

## Esito

**PASS**

La Fase B ha trasformato il catalogo da 306 a **390 famiglie** e da 547 a **631 versioni**, mantenendo completamente invariato il piano dei 180 giorni.

## Gap prima della Fase B

| Indicatore | Prima |
|---|---:|
| Famiglie ricetta | 306 |
| Versioni ricetta | 547 |
| Vere proteine vegetali principali | 3 famiglie |
| Pasta come carboidrato principale | 16 famiglie |
| Riso come carboidrato principale | 86 famiglie |
| Versioni senza uova/albume e senza formaggi | 206 |

Il problema principale non era quindi il numero assoluto di ricette, ma la distribuzione semantica del catalogo. In particolare, i legumi erano quasi assenti come vera portata proteica e la pasta era molto meno rappresentata del riso.

## Estensione introdotta

Sono state aggiunte **84 nuove famiglie**, tutte con una singola versione a porzione fissa.

| Indicatore | Aggiunto | Dopo |
|---|---:|---:|
| Famiglie ricetta | +84 | 390 |
| Versioni ricetta | +84 | 631 |
| Proteine vegetali principali | +40 | 43 famiglie |
| Pasta-primary | +36 | 52 famiglie |
| Riso-primary | +12 | 98 famiglie |
| Versioni senza uova/formaggi | +84 | 290 |

La tranche comprende:

- 16 piatti di pasta con legumi come proteina principale;
- 12 piatti di riso con legumi come proteina principale;
- 12 portate vegetali principali con altri carboidrati;
- 20 piatti di pasta con proteina animale ma senza uova/formaggi;
- 8 altri principali senza uova/formaggi;
- 16 colazioni/spuntini alternativi.

## Diversità introdotta

La nuova tranche non contiene titoli duplicati né composizioni ingredienti duplicate.

Esempi del nuovo bacino:

- Pasta e ceci con zucca;
- Pasta e lenticchie con cavolo nero;
- Pasta e cannellini con carciofi;
- Pasta integrale con lupini e zucca;
- Riso basmati con ceci e carote;
- Riso integrale con lenticchie e zucca;
- Riso jasmine con lupini e carote;
- Couscous con ceci e zucca;
- Farro con cannellini e cavolo nero;
- Orzo con lenticchie e finocchi;
- Polenta con borlotti e funghi;
- Patate con lupini e carciofi;
- Gnocchi con ragu delicato di lenticchie;
- nuovi primi con tonno, sgombro, sardine, merluzzo, salmone, trota, gamberi, cozze, calamaro, pollo, tacchino e manzo;
- nuovi spuntini e colazioni con yogurt/kefir, avena, frutta, pane, hummus, frutta secca e burro di arachidi senza ricorrere a formaggi o uova.

## Nutrizione delle nuove portate principali

Le 68 nuove portate principali occupano un intervallo abbastanza ampio per essere utili nella futura composizione dei giorni:

- 332.4 kcal minimo;
- 435.0 kcal mediana;
- 502.6 kcal massimo;
- 11.9 g fibra massima.

Il limite sulla fibra è stato introdotto appositamente perché il progetto corrente usa un profilo a fibra moderata. Evita che la correzione del problema legumi ne introduca un altro.

## Copertura stagionale

Anche il mese meno coperto, settembre, dispone ora di:

- 35 nuovi principali;
- 21 nuovi principali vegetali;
- 18 nuovi piatti di pasta;
- 6 nuovi piatti di riso;
- 15 nuove colazioni/spuntini.

Da ottobre a febbraio la copertura cresce ulteriormente fino a 60-65 nuovi principali per mese.

Questo non significa che ogni ricetta debba essere usata. Significa che la Fase C avrà abbastanza candidati stagionalmente coerenti per mantenere bassa la ripetibilità.

## Calendario: volutamente invariato

Il checksum del piano resta:

`89793df84b3b5153bba3eb3ee8333942a286b2d076289193e8fc53f9d69fb439`

I 180 giorni e gli 864 pasti non sono stati toccati.

Di conseguenza le violazioni rilevate dalla Fase A restano, come previsto:

- 167/174 finestre fuori limite uova/albume;
- 174/174 finestre fuori limite formaggi;
- 49/174 finestre insufficienti per pasta/riso;
- 174/174 finestre insufficienti per proteine vegetali principali.

La Fase B non tenta di mascherare questi numeri: ha creato gli strumenti alimentari necessari per correggerli in Fase C.

## Regressione tecnica

Sono passati:

- audit Fase B;
- test di determinismo del catalogo;
- validazione JSON Schema di tutte le nuove famiglie/versioni;
- test contrattuale dataset V5 aggiornato;
- regressione Fase A;
- build PWA;
- stress test V5.2.1 con 96 operazioni e undo/redo completo;
- validazione degli schemi V5.

Il catalogo materializzato ha checksum:

`02346fbbed6fab9b67fb6e1a255f1f26b86207ed6f78422f2ac5f8b802c891aa`

## Implicazione per la Fase C

La Fase C può ora concentrarsi sul lavoro realmente costoso: **rivedere i 180 giorni uno per uno**.

Non sarà necessario inventare ricette mentre si corregge ogni singolo giorno, salvo gap specifici che emergeranno durante la curation. Se questi emergono, verranno aggiunte ulteriori ricette mirate e poi si continuerà la revisione.

L'ordine suggerito per la curation è:

1. eliminare le violazioni uova/albume e formaggi;
2. inserire la quota di proteine vegetali principali;
3. portare ogni finestra a sufficiente pasta/riso mantenendo equilibrio fra le due fonti;
4. distribuire fonti proteiche e ingredienti dominanti;
5. eliminare ripetizioni ravvicinate;
6. verificare stagionalità;
7. fare una seconda passata editoriale sull'intero semestre;
8. chiudere solo quando tutti gli hard constraint sono a zero violazioni.
