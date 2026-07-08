# Specifica di progetto — "Tracker raccomandazioni YouTube"

> **Documento per Claude Code.** L'utente non è un programmatore: questo file è la specifica completa del progetto. Claude Code scrive ed esegue il codice, spiega ogni passaggio in italiano semplice e chiede conferma prima delle azioni importanti. L'utente crea gli account esterni e fornisce le chiavi quando richiesto.

## 1. Obiettivo

Sistema automatico che: monitora un elenco di canali YouTube di finanza; rileva i nuovi video; ne recupera la trascrizione; estrae in modo selettivo le raccomandazioni su asset finanziari (buy/sell/hold) identificandoli con ticker e, dove esiste, ISIN; registra data e prezzo di chiusura alla data della raccomandazione; ogni giorno a orario fisso aggiorna i prezzi e verifica l'esito delle raccomandazioni rispetto al mercato; costruisce una classifica di affidabilità dei canali; pubblica i risultati su una dashboard web protetta, invia una email quotidiana di sintesi e offre un export Excel scaricabile. Gira in cloud 365 giorni l'anno con costi di infrastruttura ~0.

## 2. Regole di collaborazione con l'utente

1. Spiegare in italiano semplice cosa si sta per fare e perché, prima di farlo.
2. Chiedere conferma esplicita prima di: installare dipendenze nuove, creare risorse su servizi esterni, fare deploy, cancellare dati.
3. Le chiavi API vanno **solo** in un file `.env` locale (in `.gitignore`) e nei Secrets di GitHub Actions. Mai nel codice, mai nei commit. Guidare l'utente passo passo quando deve crearle o incollarle.
4. Chiudere ogni sessione con un riepilogo: cosa funziona ora, come l'utente può provarlo, cosa resta da fare.
5. Se una libreria o un servizio indicato in questo documento risulta cambiato o non funzionante, verificarlo e proporre un'alternativa spiegando il perché.

## 3. Requisiti funzionali

1. Monitorare i canali della tabella §10 (elenco configurabile) e rilevare i nuovi video pubblicati.
2. Recuperare la trascrizione di ogni nuovo video.
3. Estrarre **solo** affermazioni operative dell'autore su asset finanziari — azioni, ETF, indici, materie prime — ignorando chiacchiere generiche, notizie riportate e opinioni di terzi citate.
4. Per ogni raccomandazione salvare: nome asset, ticker, ISIN (se esiste), tipo asset, azione (buy/sell/hold), eventuale prezzo target, orizzonte temporale dichiarato, motivazione sintetica, citazione testuale (1–2 frasi), timestamp nel video, data del video, prezzo di chiusura dell'asset a quella data.
5. Salvare tutto in un database; l'Excel è un **export** generato dal database, mai la fonte di verità.
6. Ogni giorno, a orario fisso dopo la chiusura di Wall Street, aggiornare i prezzi e valutare ogni raccomandazione agli orizzonti di +7, +30 e +90 giorni di calendario (usando l'ultima chiusura disponibile ≤ data target).
7. Valutazione relativa al mercato: rendimento dell'asset confrontato con il benchmark del suo mercato (excess return), non solo rendimento assoluto.
8. Rating per canale con correzione per campioni piccoli; mostrare sempre il numero di raccomandazioni accanto al punteggio.
9. Backfill: al primo avvio elaborare lo storico dei video di ogni canale (ultimi 12 mesi, configurabile) così i rating sono attendibili da subito.
10. Report: dashboard web con password + email quotidiana di sintesi + download Excel dalla dashboard.
11. Robustezza: un errore su un singolo video non deve bloccare il resto; log di ogni esecuzione; alert email se il job giornaliero fallisce.

## 4. Stack tecnico (deciso — cambiare solo motivando)

- **Linguaggio:** Python 3.11+. Repository GitHub privato.
- **Database:** Postgres su Supabase (piano gratuito).
- **Rilevamento nuovi video:** feed RSS ufficiale `https://www.youtube.com/feeds/videos.xml?channel_id=...` (dal link o handle del canale si ricava il `channel_id` una sola volta). Per il **backfill storico**: YouTube Data API v3, playlist "uploads" del canale (l'RSS mostra solo gli ultimi ~15 video).
- **Trascrizioni:** prima scelta i sottotitoli esistenti via `youtube-transcript-api`. Fallback: download audio con `yt-dlp` + trascrizione con `faster-whisper`. Il fallback va proposto all'utente prima di attivarlo, avvisandolo che il download dell'audio è contrario ai Termini di servizio di YouTube; i sottotitoli sono la via preferita. Nota operativa: YouTube a volte blocca le richieste di sottotitoli dagli IP dei datacenter — gestire l'errore con retry e, se persistente, segnalarlo nel report invece di far fallire il job.
- **Estrazione:** Claude API con il modello Haiku più recente (es. `claude-haiku-4-5`; verificare il nome corrente su docs.claude.com), output JSON con schema validato (tool use). Linee guida del prompt in §6.
- **Ticker/ISIN:** API OpenFIGI (gratuita) per mappare nome ↔ ticker ↔ ISIN. Ciò che non si risolve finisce nella tabella `quarantine`, non tra i dati buoni.
- **Prezzi:** `yfinance`, incapsulato in un modulo `prices.py` sostituibile (se yfinance diventa inaffidabile, alternative: Twelve Data, EODHD). Convenzioni ticker Yahoo: USA semplici (`AAPL`); Milano `.MI` (`ENI.MI`); Xetra `.DE`; Parigi `.PA`; Amsterdam `.AS`; Londra `.L`; indici `^GSPC`, `FTSEMIB.MI`, `^STOXX`; materie prime futures `GC=F`, `SI=F`, `CL=F`.
- **Benchmark per mercato:** titoli USA → S&P 500 (`^GSPC`); Italia → FTSE MIB (`FTSEMIB.MI`); altra Europa → STOXX Europe 600 (`^STOXX`); ETF/indici/materie prime → S&P 500 come default (configurabile per asset).
- **Scheduler/hosting:** GitHub Actions, cron `30 21 * * *` UTC tutti i giorni (≈ 22:30–23:30 ora italiana, sempre dopo la chiusura USA) + un workflow "keep-alive" settimanale, perché GitHub sospende i cron sui repository inattivi da 60 giorni. Opzionale: una seconda esecuzione di sola ingestione a metà giornata per catturare prima i nuovi video.
- **Dashboard:** Streamlit Community Cloud (gratuito), protetta da password semplice (via `st.secrets`), con pulsante "Scarica Excel".
- **Email:** Brevo (piano gratuito) oppure SMTP di Gmail con password per app — far scegliere l'utente e guidarlo nella configurazione.

## 5. Schema dati (minimo)

- `channels(id, name, url, channel_id, language, market_default, active)`
- `videos(id, channel_id, video_id, title, url, published_at, transcript_source [subs|whisper|none], processed_at, status)`
- `recommendations(id, video_id, asset_name, ticker, isin, asset_type [stock|etf|index|commodity], action [buy|sell|hold], target_price, horizon_text, rationale, quote, video_timestamp, reco_date, price_at_reco, benchmark_ticker, conditional, status [open|evaluated|quarantined])`
- `prices(ticker, date, close)` — chiave primaria (ticker, date)
- `evaluations(id, recommendation_id, horizon_days [7|30|90], asset_return_pct, benchmark_return_pct, excess_return_pct, hit, evaluated_at)`
- `ratings(channel_id, horizon_days, n_recos, hit_rate, wilson_lb, avg_excess_return, score, updated_at)`
- `quarantine(id, video_id, raw_extraction_json, reason, created_at)`
- `job_runs(id, started_at, finished_at, status, notes)` — per il monitoraggio

## 6. Prompt di estrazione — linee guida

Input: trascrizione completa + titolo + data + lingua del canale. Output: array JSON con i campi di §5. Regole da includere nel prompt:

1. Estrarre solo affermazioni operative dell'autore (compro / vendo / comprerei / eviterei / il mio target è X), non notizie riportate né raccomandazioni di terzi che l'autore sta solo citando.
2. Normalizzare i numeri secondo la lingua del video: in tedesco e italiano "6.500" è seimilacinquecento e "4,36" è quattro virgola trentasei. (Nel file di esempio dell'utente questo errore ha prodotto un target S&P 500 di "6.50".)
3. Se il nome dell'asset sembra storpiato dalla trascrizione automatica (es. "RWE ACZEN" per "RWE Aktien"), proporre l'interpretazione più plausibile e marcare `low_confidence: true`; se OpenFIGI non conferma, la riga va in quarantena.
4. Riportare la citazione testuale (massimo 1–2 frasi) e il timestamp approssimativo nel video.
5. Marcare con `conditional: true` le raccomandazioni condizionali ("se rompe i 200$ allora…").
6. Distinguere le raccomandazioni buy/sell/hold dai **forecast quantitativi** (target numerici su prezzi/ricavi): i secondi appartengono al modulo opzionale §11 e per ora vanno ignorati o salvati a parte senza valutarli.

## 7. Metodologia di valutazione e rating

- `price_at_reco` = chiusura del giorno del video (se festivo o weekend, ultima chiusura precedente).
- Orizzonti: 7 / 30 / 90 giorni di calendario → si usa l'ultima chiusura disponibile ≤ data target.
- `excess_return` = rendimento dell'asset − rendimento del benchmark sullo stesso intervallo.
- `hit`: buy → excess > 0; sell → excess < 0. Le "hold" non entrano nel conteggio hit ma restano tracciate. Soglia di rilevanza opzionale ±1% (configurabile) per non premiare il rumore.
- **Punteggio del canale** = Wilson lower bound al 95% del hit rate a 30 giorni (così 3 su 3 non batte 45 su 60); a parità, ordinare per excess return medio. Mostrare sempre N accanto al punteggio, con nota in dashboard: il rating misura l'accuratezza storica, non predice quella futura.

## 8. Dashboard — pagine

1. **Classifica canali:** punteggio, N raccomandazioni, hit rate a 7/30/90, excess medio.
2. **Raccomandazioni aperte:** asset, azione, canale, giorni trascorsi, performance corrente vs benchmark.
3. **Dettaglio canale:** storico raccomandazioni ed esiti.
4. **Download Excel:** un file con fogli Recommendations, Evaluations, Ratings (stessa logica del file di esempio dell'utente, esteso con ISIN, prezzo alla data ed esiti).

## 9. Email quotidiana — contenuto

Nuove raccomandazioni del giorno (canale, asset, azione); esiti maturati oggi (hit/miss per orizzonte); variazioni rilevanti in classifica; eventuali errori del job. Testo semplice + link alla dashboard.

## 10. Canali da monitorare

| # | Nome canale | URL | Lingua | Mercato / focus prevalente | Pilota |
|---|---|---|---|---|---|
| 1 | Joseph Carlson After Hours | https://www.youtube.com/@JosephCarlsonAfterHours | EN | USA — azioni, portafoglio reale | ✔ |
| 2 | Jerry Romine Stocks | https://www.youtube.com/@JerryRomineStocks | EN | USA — tech/AI, ETF | ✔ |
| 3 | Finanzbär | https://www.youtube.com/@Finanzbaer | DE | Germania/Europa — azioni, ETF | ✔ |
| 4 | Ticker Symbol: YOU | https://www.youtube.com/@TickerSymbolYOU | EN | USA — AI, semiconduttori, tech | |
| 5 | Millionaires Investment Secrets | https://www.youtube.com/channel/UCESh5daDcPqvG0QhbSdzIzw | EN | USA — stock picks | |
| 6 | Honeystocks Active Investing | https://www.youtube.com/channel/UCmNwLkHnslfzEtO2S16vmcQ | EN | USA — indici, ETF settoriali, materie prime (analisi tecnica) | |
| 7 | Clive Thompson | https://www.youtube.com/@clivethompson-jc9my | EN | Globale — azioni, oro/argento, minerari | |
| 8 | BWB – Business With Brian | https://www.youtube.com/@BusinessWithBrian | EN | USA — AI, quantum computing | |

Note operative:
- **Fase pilota** (Sessioni 1–3): usare solo i tre canali marcati ✔ — due in inglese con call esplicite frequenti e uno in tedesco per collaudare subito la parte multilingue e la normalizzazione dei numeri (virgola/punto). Gli altri cinque si aggiungono dopo il collaudo cambiando solo la configurazione.
- Il canale 6 (Honeystocks) produce molte call su **indici, ETF e materie prime** e il canale 7 (Clive Thompson) su **oro/argento e minerari**: per questi asset l'ISIN spesso non esiste (usare solo il ticker con `asset_type` corretto) e il benchmark va configurato con criterio (es. i minerari auriferi contro l'oro `GC=F` o l'ETF GDX, non solo contro l'S&P 500).
- Il canale 3 (Finanzbär) tratta anche P2P e immobili: contenuti da ignorare in estrazione (fuori perimetro: solo asset quotati con ticker).

## 11. Modulo opzionale (fase successiva): forecast quantitativi

Verifica dei target numerici (foglio "Forecasts" del file di esempio): tabella separata `forecasts` con `target_value` e scadenza; esito = raggiunto / non raggiunto entro la scadenza. **Non implementare** finché il modulo principale non è collaudato, salvo richiesta esplicita dell'utente.

## 12. Piano di lavoro in sessioni — con criteri di completamento

- **Sessione 1 — Fondamenta:** repository, struttura del progetto, connessione a Supabase, creazione tabelle, watcher RSS sui canali pilota. ✔ Completata quando: lanciando lo script, i nuovi video dei canali pilota compaiono nel database.
- **Sessione 2 — Trascrizione ed estrazione:** sottotitoli, prompt Claude, validazione OpenFIGI, quarantena. ✔ Completata quando: 5 video di prova producono raccomandazioni corrette, verificate a mano dall'utente confrontandole col video.
- **Sessione 3 — Prezzi e valutazione:** prezzo alla data, tracker a 7/30/90 giorni, benchmark, backfill 12 mesi sui canali pilota. ✔ Completata quando: le valutazioni dei video storici risultano plausibili a un controllo a campione.
- **Sessione 4 — Rating e dashboard:** punteggi, Streamlit con password e download Excel. ✔ Completata quando: l'utente naviga la dashboard dal proprio browser.
- **Sessione 5 — Automazione:** email quotidiana, GitHub Actions (cron + keep-alive + alert su fallimento), deploy della dashboard. ✔ Completata quando: per 3 giorni consecutivi il job gira da solo e l'email arriva.
- **Collaudo:** 1–2 settimane di esercizio sui canali pilota; poi aggiunta di tutti i canali e, se desiderato, del modulo §11.

## 13. Account e chiavi a carico dell'utente (guidarlo passo passo)

| Servizio | A cosa serve | Costo |
|---|---|---|
| GitHub | codice + esecuzione automatica quotidiana | gratis |
| Supabase | database | gratis |
| Anthropic Console | chiave API per l'estrazione | a consumo (pochi €/mese) |
| Google Cloud | solo la chiave YouTube Data API per il backfill | gratis |
| Streamlit Community Cloud | hosting della dashboard | gratis |
| Brevo (o Gmail con password per app) | invio email quotidiana | gratis |

Tutte le chiavi vanno nel file `.env` locale e nei Secrets del repository GitHub. Claude Code deve mostrare all'utente esattamente dove cliccare per crearle e dove incollarle.
