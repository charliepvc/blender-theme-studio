# ROADMAP

Questo documento traccia lo sviluppo di Theme Studio. È pensato per essere realistico, per scaglioni e in linea con la filosofia del progetto: **sicuro, reversibile, semantico**.

## Stato attuale
- **v0.4.0** – Versione locale candidata alla prima pubblicazione, distribuita come ZIP legacy. Build di riferimento **Blender 5.2.1 LTS** e sviluppo sulla famiglia **5.3.x**, con fallback per versione. Live editing, RGBA nello stesso selettore, Undo/Redo con coalescing e recupero da journal. Il salvataggio di tutte le preferenze richiede un'azione esplicita.

## Pianificazione

### v0.5.0 – Focus contestuale & navigazione *(PRIORITÀ MASSIMA)*
L'obiettivo è rendere **Dettagli** più immediato per chi usa l'addon per la prima volta. Si basa interamente sull'infrastruttura già esistente.

- [ ] **Scelta posizione UI: Themes o N-panel** – Aggiungere un'opzione nelle preferenze dell'addon per scegliere dove posizionare Theme Studio: nella sezione **Themes** delle Preferenze di Blender, oppure nel pannello **N-panel** della Vista 3D (comportamento attuale). Le due modalità devono condividere esattamente la stessa logica di sessione, live editing, history/undo e ripristino.
- [ ] **Salto diretto ai Dettagli** – Dai gruppi principali (Tema/Vista 3D) è possibile passare direttamente alla vista Dettagli con categoria e contesto prefiltrati.
- [ ] **Breadcrumb contestuale** – Mostrare il percorso di provenienza (es. `Dettagli › Testi › Controlli`) per orientarsi subito.
- [ ] **"Modificando: ..."** – Indicazione chiara in alto quando si arriva ai Dettagli da un gruppo specifico.
- [ ] **Aree influenzate** – Spiegazione visiva di quali parti dell'interfaccia vengono toccate da quel gruppo semantico.
- [ ] **Miglior chiarezza dei collegamenti** – Rendere più esplicito il significato di "Segue le modifiche comuni" / "Solo questo" e della mappa tra campi collegati.
- [ ] **Revisione dell'intelligenza dei pattern** – Rivedere come i gruppi semantici collegano e trasformano i colori: alcuni risultati non sono ancora convincenti. Raccogliere casi concreti e feedback su risultato atteso e ottenuto prima di correggere regole e associazioni, preservando controllo sui singoli campi e reversibilità.

### v0.6.0 – Passaggio a Blender Extension
Il salto "vero" dal punto di vista della distribuzione. Fatto **dopo** le modifiche di UX per evitare lavoro doppio.

- [ ] **`blender_manifest.toml`** – Creazione e configurazione del manifest per il formato Extension di Blender 4.2+.
- [ ] **Adattamento `__init__.py` / registrazione** – Sistemazione per la nuova struttura mantenendo il comportamento attuale.
- [ ] **Verifica su 5.2.1 LTS e 5.3.x** – Test completo in storage isolato su entrambe le famiglie.
- [ ] **Aggiornamento documentazione** – Nuove istruzioni di installazione (Blender Extensions) aggiornando `README.md` e `docs/user/README.md`.
- [ ] **Preparazione per `extensions.blender.org`** – Verifica requisiti e metadata in vista di un'eventuale pubblicazione ufficiale.

### v0.7.0 – Scheda "Palette"
Introduzione di una vera e propria identità visiva per Theme Studio. Approccio matematico, niente generatori AI.

- [ ] **Nuova scheda "Palette"** – Affiancata alle schede esistenti `Tema / Vista 3D / Dettagli`.
- [ ] **Palette predefinite** – Set curati applicabili per gruppi semantici mantenendo la reversibilità live.
- [ ] **Armonie matematiche** – Generazione di palette coerenti da un colore base (complementare, analoga, triadica) usando `colorsys`.
- [ ] **Palette personali** – Salvataggio e caricamento di palette custom, integrabili con il sistema profili esistente.
- [ ] **Applicazione per gruppi** – Applicazione mirata ai gruppi semantici, senza toccare l'intero tema in modo indiscriminato.

### v1.0 – Consolidamento
Obiettivo: stabilità, chiarezza e solidità basate su feedback reale.

- [ ] **Polish UX** – Ritocchi mirati emersi dall'uso reale.
- [ ] **Pulizia e rifinitura** – Revisione di edge-case, messaggi e coerenza generale.
- [ ] **Stabilità generale** – Focus su robustezza più che su nuove feature.
- [ ] **Documentazione definitiva** – README più completo con screenshot/GIF quando disponibili.

## Idee da tenere d'occhio (non impegnative)
- **Popover "Modifica rapida"** – Finestra contestuale più snella per i gruppi più usati.
- **"Recenti"** – Accesso rapido agli ultimi campi modificati.
- **Suggerimenti contrasto non automatici** – Solo indicativi, mai correttivi forzati.
- **Miglior scoperta campi** – Ulteriori affinamenti sulla navigazione senza complicare l'interfaccia.

## Note
- **v1.0 non è vincolata a tutte le voci sopra.** Può essere raggiunta anche se alcune idee restano aperte. Priorità è sempre la stabilità.
- **Le modifiche grosse vengono prima delle Extensions.** Il formato di distribuzione viene sistemato una volta che l'UX è stabile.
- **Compatibilità da verificare per ogni nuova versione.** Il fallback del catalogo non sostituisce le verifiche di installazione, funzionamento e ripristino.
