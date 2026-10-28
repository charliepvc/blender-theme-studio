# Roadmap

<p><a href="ROADMAP.md">English</a> · <strong>Italiano</strong></p>

Questa roadmap descrive uno sviluppo realistico, per fasi, guidato da tre
principi: **sicuro, reversibile e semantico**. Le priorità possono cambiare in
base ai riscontri degli utenti e alle verifiche tecniche.

## Stato attuale

- **v0.4.0 Preview** — Pubblicata come ZIP legacy installabile localmente, non
  come Blender Extension. **Blender 5.2.1 LTS** è la build di riferimento; lo
  sviluppo riguarda la famiglia **5.3.x**, ma il fallback del catalogo basato
  sulla versione non dimostra la compatibilità. Le funzioni attuali includono
  modifica live, controlli RGBA, undo/redo accorpati e recupero tramite journal.
  Il salvataggio di tutte le preferenze di Blender richiede un’azione esplicita.

## Pianificazione

### v0.5.0 — Focus contestuale e navigazione *(priorità massima)*

Rendere **Details** più comprensibile e facile da esplorare per chi usa l’addon
per la prima volta, sfruttando i gruppi semantici e il filtraggio dei campi già
esistenti.

- [ ] **Scegliere la posizione dell’interfaccia: Themes o N-panel** — Aggiungere
  una preferenza dell’addon per posizionare Theme Studio in Preferenze di Blender
  > Themes oppure nel pannello N della Vista 3D (posizione attuale). Entrambe le
  modalità devono condividere sessione, modifica live, cronologia e ripristino.
- [ ] **Aprire direttamente Details** — Dai gruppi principali Theme o 3D View,
  aprire Details con categoria e contesto già filtrati.
- [ ] **Percorso contestuale** — Mostrare la provenienza, per esempio
  `Details › Text › Controls`, per orientarsi nella selezione attuale.
- [ ] **Indicazione “Modificando: …”** — Identificare il gruppo da cui si è
  arrivati alla vista Details.
- [ ] **Mostrare le aree dell’interfaccia interessate** — Aggiungere una
  spiegazione visiva statica, basata sui gruppi, delle regioni di Blender
  influenzate da un gruppo di colori semantico. Usa associazioni curate; non è un
  selettore per elementi UI arbitrari.
- [ ] **Chiarire i controlli collegati** — Spiegare “Segue le modifiche comuni”
  rispetto a “Modifica separatamente” e mostrare il legame tra i campi e il gruppo.
- [ ] **Rivedere i pattern dei colori semantici** — Raccogliere esempi concreti di
  risultato atteso e ottenuto prima di modificare collegamenti o trasformazioni
  dei colori. Conservare il controllo individuale e la reversibilità.

### v0.6.0 — Pacchetto Blender Extension

Passare al formato Extension dopo il lavoro UX pianificato, per evitare di
ripetere le modifiche al pacchetto.

- [ ] Creare e configurare `blender_manifest.toml` per Blender Extensions.
- [ ] Adattare la struttura del pacchetto e la registrazione senza cambiare il
  comportamento attuale.
- [ ] Completare verifiche isolate di installazione e dei flussi di lavoro su
  Blender 5.2.1 LTS e build 5.3.x selezionate.
- [ ] Aggiornare le istruzioni di installazione in inglese e italiano.
- [ ] Valutare requisiti e metadati per le Extension prima di considerare la
  pubblicazione su `extensions.blender.org`.

### v0.7.0 — Workspace Palette

Dare a Theme Studio un flusso di lavoro curato per le palette, basato su armonie
matematiche e non su palette generate dall’AI.

- [ ] Aggiungere una pagina **Palette** accanto a Theme, 3D View e Details.
- [ ] Offrire palette curate, applicabili in modo reversibile ai gruppi semantici.
- [ ] Generare palette complementari, analoghe e triadiche a partire da un colore
  base usando il modulo Python `colorsys`.
- [ ] Salvare e caricare palette personali, integrandole dove opportuno con il
  sistema di profili esistente.
- [ ] Applicare palette ai gruppi scelti, senza modificare indiscriminatamente
  l’intero tema.

### v1.0 — Consolidamento

Puntare su stabilità e chiarezza basate sull’uso e sui riscontri reali.

- [ ] Rifinire l’esperienza d’uso in base all’utilizzo osservato.
- [ ] Rivedere casi limite, messaggi e coerenza.
- [ ] Dare priorità alla robustezza rispetto a nuove funzioni.
- [ ] Completare la guida con schermate o una demo quando disponibili.

## Idee da valutare *(non sono impegni)*

- **Selettore di elementi dell’interfaccia (idea esplorativa)** — Consentire di
  indicare o cliccare un elemento visibile di Blender, per esempio lo sfondo di un
  pannello, e selezionare in Details i campi del tema associati. Seleziona il
  bersaglio tematico, non campiona un colore. Non è verificato che Blender
  permetta di identificare il controllo sotto il cursore e collegarlo in modo
  affidabile ai campi del tema. Da esplorare separatamente dalla visualizzazione
  delle aree interessate dai gruppi: le due funzioni potrebbero completarsi, e
  non è noto che una sostituisca l’altra.
- **Popover Modifica rapida** — Editor contestuale ridotto per i gruppi più usati.
- **Campi recenti** — Accesso rapido ai controlli modificati di recente.
- **Indicazioni di contrasto non automatiche** — Solo informative, senza correzioni
  forzate dei colori.
- **Scoperta dei campi** — Migliorare la navigazione senza aggiungere complessità
  inutile.

## Note

- La versione 1.0 non richiede il completamento di ogni voce della roadmap. La
  priorità è la stabilità.
- Il lavoro UX importante precede il pacchetto Extension: prima si stabilizza
  l’interfaccia, poi si investe in un formato di distribuzione diverso.
- Verificare esplicitamente ogni versione di Blender. Il fallback del catalogo
  non sostituisce i controlli di installazione, uso e ripristino.
