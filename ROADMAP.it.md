# Roadmap

<p><a href="ROADMAP.md">English</a> · <strong>Italiano</strong></p>

Theme Studio segue tre principi: **sicuro, reversibile e semantico**.
Questa roadmap separa verifiche di rilascio e nuove funzioni. L’ordine seguente è
la sequenza consigliata, non un’autorizzazione a implementare o pubblicare tutto.

## Stato attuale — rilascio v0.5.0, 2026-11-10

- **Release:** v0.5.0 Preview, ZIP addon legacy, non Blender Extension. Lo ZIP
  conserva i byte di r2 verificati: corrispondenza dei 14 file sorgenti e otto
  controlli isolati superati su ciclo di vita/recupero su 5.2.1. I pacchetti v0.4.0
  restano invariati. Consulta le [note di rilascio](docs/releases/0.5.0.md).
- **Incluso:** fix smart-color accettati, Dettagli per categoria e
  contesto, workspace selezionabili, salvataggio/caricamento/esportazione nativi
  e Termina consapevole della provenienza. Gli ZIP v0.4.0 precedenti non includono tutte
  queste modifiche.
- **Workspace:** Ibrida predefinita; pannello N completo e Preferenze > Temi
  selezionabili nelle proprietà dell’addon. Condividono una sessione di modifica.
- **Evidenze:** l’ultima suite Python completa supera 430 test. Il probe nativo
  mirato di Termina già registrato supera 25 controlli su Blender 5.2.1 LTS
  `9e2066aef7ef`, inclusi salvataggi abbinati e ripristino esatto nel sandbox
  automatico. L’utente ha accettato le interazioni di Termina e riportato un
  riscontro complessivo positivo nella prova manuale.
- **Limiti:** l’utente ha confermato entrambi i salvataggi manuali e accettato
  complessivamente il candidato installato. Questo non equivale a copertura
  visiva strumentale di ogni modalità o a un crash test reale. Un precedente
  processo manuale è terminato senza un
  rapporto finale di ripristino: il ripristino esatto non è verificato. Restano
  gli avvisi iniziali di configurazione degli enum.
- **Compatibilità:** 5.2.1 LTS è la build di riferimento; 5.3.x è la famiglia di
  sviluppo. Le vecchie prove del candidato r4 sulla 5.3.0 Beta `ace25df17a10` non
  certificano sorgente corrente, ZIP pubblico o qualsiasi build 5.3. Il fallback
  del catalogo non dimostra compatibilità.
- **Picker:** accantonato dopo prove di usabilità negative; non registrato e non
  richiesto per la v0.5. Gli esperimenti precedenti sono solo evidenze storiche.

## A. Percorso di rilascio v0.5 e limiti delle evidenze

Ambito approvato (2026-11-09): distribuire il lavoro già implementato su colori,
workspace e salvataggio/sessione dopo verifiche circoscritte, correggendo i problemi
bloccanti senza aggiungere le funzioni della sezione B. Priorità a Blender 5.2.1 LTS
`9e2066aef7ef`; la 5.3 resta sperimentale, senza nuove dichiarazioni di compatibilità.
L’utente ha autorizzato la release pubblica v0.5.0 il 2026-11-10. Le verifiche
ancora aperte sotto non sono dichiarazioni di copertura universale.

### 1. Chiudere le verifiche di accettazione mancanti

- [x] Concordare l’ambito v0.5 e scegliere le build Blender esatte da supportare:
  funzioni esistenti, prima Blender 5.2.1 LTS `9e2066aef7ef`.
- [x] Confermare chiarezza dell’esito e chiusura della sessione per Salva come nuovo
  e Aggiorna tema esistente: accettati esplicitamente dall’utente. Non ripetere senza
  modifiche pertinenti.
- [ ] Registrare copertura visiva distinta di selettore/stato/layout/reattività in
  pannello N, Ibrida e Preferenze se emerge un problema concreto. L’accettazione
  complessiva del candidato installato è registrata; non è un nuovo blocco generico
  per il rilascio.
- [ ] Verificare che salvataggio, selezione e ricaricamento del tema nativo ne
  conservino l’aspetto; confermare creazione sicura di `themes`, consenso alla
  sostituzione e gestione delle collisioni. Riutilizzare le evidenze automatiche
  valide; non ricostruire funzioni già implementate.
- [ ] Valutare difetti osservati e avvisi degli enum. Correggere i problemi
  riproducibili che bloccano il rilascio; documentare i limiti innocui. Non
  trasformare questo passaggio in una riprogettazione senza confini.

Perché prima: capire cosa non funziona prima di investire nel pacchetto.

### 2. Preparare un candidato locale

- [ ] Allineare metadati di versione v0.5, note di rilascio, istruzioni e schermate
  inglesi/italiane al candidato effettivo.
- [x] Eseguire la suite Python completa dopo le ultime modifiche al sorgente e
  controlli nativi mirati ai comportamenti coinvolti sulle build scelte.
- [x] Creare uno ZIP legacy distinto, senza sovrascrivere altri pacchetti, e
  verificare la corrispondenza tra sorgente e pacchetto.

Perché dopo: provare ciò che verrà distribuito, non una cartella di sviluppo copiata.

### 3. Verificare il candidato installato

- [ ] Con impostazioni usa e getta, installare e attivare lo ZIP, modificare un
  tema, salvare/caricare, usare modifiche individuali e undo/redo, terminare/scartare
  sessioni e provare il recupero.
- [x] Verificare disattivazione/rimozione e ripristino esatto dove richiesto su ogni
  build dichiarata compatibile. I probe di salvataggio preferenze richiedono
  configurazione usa e getta e autorizzazione esplicita; mai preferenze personali.
- [x] Ottenere l’accettazione dell’utente sul candidato installato. La sola prova
  del sorgente non dimostra installabilità dello ZIP o accettazione del rilascio.

Perché dopo: intercettare file mancanti, problemi del ciclo di vita e regressioni
di installazione.

### 4. Pubblicare solo dopo accettazione e autorizzazione

- [x] Registrare candidato verificato, checksum, build supportate e limiti noti.
- [x] Eseguire commit/push del checkpoint privato finale, poi esaminare l’export
  pubblico limitato ai file consentiti tramite il flusso di pubblicazione separato.
- [x] Pubblicare, creare tag e release solo con autorizzazione esplicita. Non
  trasferire mai la cronologia privata nel repository pubblico.

Il rapporto mancante della finestra manuale chiusa resta un limite storico delle
evidenze, non un motivo per riaprirla e dichiarare un ripristino retroattivo.

## B. Nuove funzioni — elenco separato e ordinato

Queste voci restano disponibili per le decisioni sull’ambito. Non viene assegnata
una versione: sceglierne una richiede progettazione e verifica dedicate, non
un’inclusione implicita nel rilascio.

1. **Chiarire controlli collegati e aree coinvolte.** Spiegare “Segue le modifiche
   comuni”, “Modifica separatamente” e il rapporto con il gruppo capostipite.
   Partire da etichette e spiegazioni chiare; aggiungere indicazioni visive curate
   solo dove risolvono confusione osservata. Conservare i Dettagli accettati per
   categoria e contesto.
2. **Verificare i consumer nativi dei colori ancora irrisolti.** Dare priorità a
   difetti reali di rendering, contesti condivisi/trasparenti e Image
   `face_mode_select`. Il catalogo da solo non dimostra il comportamento visivo.
   Rivalutare il grigio nei menu solo con un problema concreto: gli smart-color
   accettati non promettono nero puro o testi identici tra stati. Il contorno
   della ruota HSV ignora l’alpha.
3. **Aggiungere controlli coordinati degli effetti non cromatici.** Progettare
   controlli espliciti per ombre dei testi, ombre di menu/popup, rilievi e gradienti.
   I campi esistenti restano nei Dettagli; le nuove copie attualmente disattivano
   solo le ombre dei testi, in modo reversibile.
4. **Studiare una raccolta sfogliabile nell’Asset Browser.** Prima verificare API
   native e rappresentazione: file XML in una libreria non diventano automaticamente
   asset e un file `.blend` non sostituisce XML nativo o dati del progetto
   modificabile. Implementare solo dopo l’approvazione del flusso di lavoro.

Ulteriore lavoro UI futuro richiesto dall’utente: piccoli pulsanti persistenti
per impostazioni, supporto/donazioni e GitHub. Prima dell’implementazione definire
posizione, icone native, accessibilità e destinazioni approvate dei collegamenti.
Non sono scelti provider o URL per le donazioni; non sono impliciti pagamenti
o tracciamento incorporato. Non amplia l’ambito corrente del rilascio v0.5.

Questo ordine migliora la comprensione prima di ampliare i controlli e lascia
l’integrazione più incerta a dopo la stabilizzazione del salvataggio esistente.

## C. Lavoro accantonato — nessuna ripresa automatica

- Picker sperimentale, destinazioni precise per regione e fix della selezione
  contestuale. Riprendere solo con una nuova decisione esplicita. Non sostituire
  la selezione del bersaglio con il campionamento colore e non ripristinare la
  riorganizzazione dei Dettagli per elementi già rifiutata.

## Traguardi successivi

### v0.6.0 — Pacchetto Blender Extension

Dopo la v0.5 e gli eventuali cambiamenti UX importanti selezionati, senza rendere
il formato Extension un prerequisito della v0.5:

- [ ] Creare `blender_manifest.toml` e adattare pacchetto e registrazione.
- [ ] Verificare installazione isolata, uso e ripristino su build 5.2.1/5.3 scelte.
- [ ] Aggiornare le guide di installazione inglesi/italiane e valutare requisiti
  e metadati prima di considerare la pubblicazione su `extensions.blender.org`.

### v0.7.0 — Workspace Palette

- [ ] Progettare una pagina Palette accanto a Theme, 3D View e Details.
- [ ] Offrire palette semantiche curate, applicabili in modo reversibile.
- [ ] Generare palette complementari, analoghe e triadiche con Python `colorsys`,
  non con generazione AI.
- [ ] Salvare/caricare palette personali e applicarle solo ai gruppi scelti,
  integrandole con i profili dove opportuno.

### v1.0 — Stabilità e chiarezza

- [ ] Rifinire la UX dall’uso osservato; rivedere casi limite, messaggi e coerenza.
- [ ] Privilegiare la robustezza rispetto al numero di funzioni; completare guide,
  schermate o una demo.

## Idee da valutare — non sono impegni

- Popover Modifica rapida per i gruppi più usati.
- Campi recenti e navigazione più semplice tra i campi.
- Indicazioni informative sul contrasto, mai correzioni forzate dei colori.

La v1.0 non richiede ogni voce dell’elenco. Verificare esplicitamente la
compatibilità; non dedurla dal fallback o da prove storiche non pertinenti.
