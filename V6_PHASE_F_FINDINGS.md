# TataDiet V6 — Fase F — Findings

## Esito

Fase F completata sul baseline C.2, senza modifiche ai file base di ingredienti, ricette o piano.

## Convertitore ingredienti

Il convertitore è pubblicato in tutte le **306 pagine ricetta statiche**. La versione ricetta runtime viene risolta dal titolo/slugg e le ingredient lines strutturate forniscono quantità e nutrienti.

Funzioni verificate:

- selezione ingrediente originale;
- suggerimenti greedy compatibili;
- ricerca libera per nome/alias;
- possibilità di vedere alternative `energy-only` solo tramite ricerca esplicita;
- quantità alternativa a parità di kcal;
- confronto READ di kcal, proteine, carboidrati, grassi e fibre;
- delta nutrizionale;
- nessuna scrittura a ricetta/piano.

Il calcolo equal-energy e i delta riusano direttamente il core D; il test F verifica inoltre l'esempio riso→pasta con tolleranza numerica coerente con l'arrotondamento della quantità alternativa.

## Cambio pasto

Compositore e Gestisci giornata ricercano ora anche `ingredientNames` e `ingredientAliases`, oltre ai campi ricetta già esistenti.

I risultati espongono tre ingredienti e una preview V6. Le sostituzioni localmente non conformi sono disabilitate. Il commit applica un secondo gate su tutto il piano tramite `plannerStore.validateDays()`.

Il badge positivo è volutamente `7gg OK`, non `OK V6`, perché il controllo immediato è locale; il controllo globale avviene al salvataggio.

## Porzioni

Eliminato l'ultimo punto UI che permetteva di digitare una porzione nel Compositore. La porzione è read-only e ogni sostituzione/aggiunta manuale persistita da questo flusso usa `portionMultiplier = 1`.

Questo allinea l'UX al contratto del motore E e impedisce revisioni di fatto ottenute per scaling.

## Navigazione futura

`Oggi` espone Domani, +3, +7 e picker data. `Gestisci giornata` espone +1/+3/+7/+14 rispetto alla data focalizzata. I link aprono direttamente il Compositore sulla giornata desiderata.

## Regressione

Risultati sul build F:

- C.2: PASS — 180 giorni, 864 pasti, max scostamento energia 4,77%;
- D Python/JS: PASS — baseline clean e Ingredient Intelligence invariata;
- E Python/JS: PASS — 800–2600 coperto per day-type compatibili, `infeasible` esplicito, serving fisso;
- F Python: PASS — policy, packaging, 306 converter pages, ingredient search, fixed serving, future shortcuts;
- F JS: PASS — ingredient/alias search, fixed serving, equal-energy delta;
- stress E: PASS — 96 operazioni + undo/redo, ~4,75 s nell'ultimo run;
- validazione sito: **592 HTML, 48.265 link/risorse/frammenti, 0 errori, 0 warning**.

Performance E nell'ultimo run di regressione:

- index ~12,5 ms;
- mediana matrice ~633 ms;
- P95/max ~981 ms.

## Baseline C.2 preservato

Hash invariati:

- ingredienti: `1765f980c824b1d11b44155ac813a5b285ce57e527c0a9ace088468f24e84a1b`;
- ricette: `535376cdea1d2508aa53a64c4bdf99a59cadbfd5644a5a3becd9f4fef87aa237`;
- piano: `9a155f1bf900f55e83ad5c569d3529eba96c021fa503f14fa9a0becf9210428d`.

## QA browser locale

È stato predisposto `scripts/test_v6_phase_f_browser.py` per verificare in un browser reale:

- converter greedy/free-search/confronto;
- shortcut futuri;
- picker ingredient-aware;
- porzioni read-only;
- quick date del manager.

Nell'ambiente di sviluppo corrente Chromium è installato ma una policy amministrativa blocca tutte le navigazioni HTTP locali con `net::ERR_BLOCKED_BY_ADMINISTRATOR`. Il test non è pertanto usato come gate locale. La limitazione è dell'ambiente browser, non un errore rilevato nell'applicazione. Il test resta disponibile da eseguire sul deploy in Fase H.

## Stato per Fase G

La Fase F chiude il blocco UX di pianificazione. La Fase G può concentrarsi sul Diario senza dover introdurre ulteriori scritture nel convertitore o modificare il planner. Il Diario dovrà privilegiare velocità d'uso, semafori, commenti e pasti manuali/fuori ricettario.
