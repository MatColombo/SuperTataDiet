# TataDiet V6 — Fase F

## Scopo

La Fase F espone in UI i servizi introdotti nelle Fasi D/E senza cambiare il baseline alimentare C.2. Gli obiettivi sono:

1. convertitore ingredienti nella pagina ricetta, a parità di kcal e in sola lettura;
2. ricerca ricette anche per ingrediente/alias nei flussi di cambio pasto;
3. preview immediata dell'impatto V6 e blocco del commit non conforme;
4. serving manuale coerente con V6: ricette sempre a porzione fissa 1.0;
5. accesso rapido alla pianificazione di date future.

Il Diario resta in Fase G. La Fase F non crea revisioni ricetta, non modifica ingredienti/ricette/piano base e non introduce migrazioni dati.

## Convertitore ingredienti — contratto UX

Il convertitore compare nelle pagine dettaglio ricetta e usa la versione strutturata corrispondente nel catalogo runtime.

Per ogni riga ingrediente:

- usa la quantità base della ricetta;
- calcola le kcal dell'ingrediente originale;
- calcola i grammi/quantità dell'alternativa necessari per fornire le stesse kcal;
- mostra proteine, carboidrati, grassi e fibre originali/alternativa;
- mostra il delta assoluto di ciascun valore;
- distingue compatibilità culinaria/nutrizionale da mera equivalenza energetica;
- non salva, non crea revisioni e non altera il piano.

### Modalità greedy

A campo ricerca vuoto vengono mostrate fino a 12 alternative ordinate dall'Ingredient Intelligence della Fase D. Le alternative `energy-only` non sono suggerite automaticamente.

Classi visuali:

- `Molto compatibile`;
- `Compatibile`;
- `Con differenze`;
- `Solo equivalenza energetica`.

### Ricerca libera

Digitando un nome o alias ingrediente vengono mostrate anche alternative `energy-only`, purché l'equivalenza calorica sia calcolabile. Questo consente di rispondere a domande esplicite come "quanto olio equivale caloricamente a questi grammi di riso?" senza far apparire l'olio tra i suggerimenti normali del riso.

La UI ricorda esplicitamente che stesse kcal non implicano equivalenza nutrizionale o culinaria.

## Cambio pasto — ricerca ingrediente

Il testo indicizzato di ogni candidato include:

- titolo ricetta;
- cucina;
- meal type;
- tag;
- nomi ingredienti;
- alias ingredienti.

Il picker mostra i primi tre ingredienti principali in forma sintetica (`Contiene: ...`) per rendere comprensibile il match.

## Preview constraint-aware

Nel picker di Compositore e Gestisci giornata ogni candidato viene simulato senza persistenza.

La preview immediata controlla:

- le finestre mobili di 7 giorni coinvolte;
- hard constraint V6;
- soft warning V6;
- energia giornaliera rispetto al target con tolleranza ±5%.

Esiti visuali:

- `7gg OK`;
- `Fuori kcal`;
- `Vincolo hard`;
- `Warning V6`.

Le card non conformi sono disabilitate.

`7gg OK` descrive volutamente solo il controllo immediato locale. Prima del commit viene eseguita `validateDays()` sull'intero piano per includere anche varietà globale, cap C.1 e riuso acquisti.

## Serving fisso

La Fase F elimina l'ambiguità residua della vecchia UI manuale:

- il campo porzione nel Compositore è read-only;
- ogni aggiunta/sostituzione scrive `portionMultiplier = 1`;
- l'utente non può creare implicitamente una revisione scalata variando la porzione;
- il convertitore ingredienti resta informativo e non viene usato per aggirare questo vincolo.

## Navigazione a date future

### Oggi

Sono disponibili accessi diretti:

- Domani;
- +3 giorni;
- +7 giorni;
- selezione libera della data.

La destinazione è `calendario/componi` focalizzata sulla data richiesta.

### Gestisci giornata

Sono disponibili:

- Domani;
- +3;
- +7;
- +14 giorni.

Gli offset vengono calcolati dalla giornata correntemente focalizzata e limitati all'intervallo del piano.

## Runtime e file principali

Nuovo runtime:

- `static/assets/js/v6-recipe-converter.js`.

Runtime modificati:

- `static/assets/js/v5-composer-core.js`;
- `static/assets/js/v5-composer.js`;
- `static/assets/js/v5-day-manager.js`;
- `static/assets/js/v5-effective-pages.js`.

Template/UI modificati:

- `templates/recipe.html`;
- `templates/day_composer.html`;
- `templates/day_manager.html`;
- `templates/base.html`;
- `static/assets/css/styles.css`.

Policy:

- `spec/v6/phase-f-policy.json`.

## Dati

La Fase F deve mantenere byte-identici i tre asset base C.2:

- ingredienti;
- ricette;
- piano 180 giorni.

Il manifest passa a `6.0.0-phase-f.1` aggiungendo soltanto l'estensione F e la policy/runtime relativi.

## Gate

Gate riproducibile:

```bash
./v6_phase_f.sh
```

Comprende build, regressioni C.2/D/E/F, stress strutturale E e validazione statica dell'intero sito.

Il browser smoke F è disponibile come test separato contro un deploy/ambiente che consenta la navigazione HTTP del browser:

```bash
python3 scripts/test_v6_phase_f_browser.py --base-url https://HOST/TataDiet
```

Non è parte del gate locale perché il Chromium gestito nell'ambiente di sviluppo corrente blocca la navigazione HTTP con policy amministrativa.
