# Usare Theme Studio

Theme Studio modifica il tema globale di Blender. L'interfaccia attuale si trova
nella Vista 3D, barra laterale **N > Theme Studio**. La scelta alternativa nella
sezione Themes delle Preferenze è una funzione pianificata, non ancora presente.

## Installazione

Installare lo ZIP dell'addon dalla funzione di installazione da disco nelle
Preferenze di Blender, quindi attivare Theme Studio. Non installare lo ZIP dei
sorgenti generato da GitHub. Per costruire il pacchetto dai sorgenti seguire il
[README](../../README.it.md#creazione-dai-sorgenti).

## Modificare il tema

1. Premere **Inizia a modificare**: viene preparata la copia iniziale.
2. Usare **Tema** per i gruppi comuni, **Vista 3D** per il viewport e **Dettagli**
   per i campi individuali filtrati per categoria e contesto.
3. Le modifiche vengono applicate live. I colori RGBA espongono anche l'alpha;
   i colori RGB non hanno una trasparenza modificabile.
4. Usare annullamento e ripetizione dell'addon per la cronologia del tema.
5. Salvare una copia del tema se si vuole conservarla e riaprirla in seguito.

I profili dell'addon sono file JSON, non preset XML nativi di Blender. La loro
compatibilità è verificata rispetto al catalogo e all'identità della build.
Non modificare l'identità del profilo per forzare il caricamento su altre build.

## Concludere una sessione

- **Scarta modifiche…** ripristina i campi ancora posseduti dalla sessione e
  conserva, segnalando i conflitti, le modifiche esterne rilevate.
- **Termina… > Usa senza salvare ora** mantiene il tema live e chiude la
  sessione senza salvare subito le preferenze. L'auto-save di Blender, se attivo,
  può salvarle successivamente.
- **Salva tutte le preferenze…** salva l'intero insieme delle preferenze di
  Blender, non soltanto il tema. Richiede una scelta esplicita.

Nascondere il pannello N non conclude la sessione. Prima di chiudere Blender,
concludere o scartare il lavoro. Durante una prova temporanea non premere il
salvataggio manuale delle preferenze di Blender.

## Errori e recupero

Il journal conserva informazioni necessarie al recupero dopo un'interruzione.
Un recupero pendente blocca la modifica finché non viene risolto. Seguire le
azioni mostrate dal pannello e non cancellare il journal per aggirare il blocco.
Le sessioni già concluse e validate non devono essere trattate come recuperi
pendenti. Dopo un aggiornamento di Blender possono invece restare dati di una
sessione non conclusa appartenenti a una build precedente: non vengono applicati
automaticamente alla build nuova.

**Conserva i dati e continua…** permette di mantenere il tema attuale senza
ripristinare quello precedente. Dopo la conferma viene conservata una copia
verificata dei dati di recupero; gli originali non vengono spostati o cancellati.
L'addon ricorda la scelta soltanto per quei contenuti esatti. Se l'originale
cambia o la copia non è più verificabile, i dati tornano a richiedere attenzione.
Questa azione non salva le preferenze e non applica colori al tema corrente.

Le azioni di ripristino sono disponibili soltanto quando il recupero è compatibile
e può essere eseguito. I percorsi dei file e gli errori completi rimangono nei
dettagli tecnici, utili per l'assistenza; non serve modificarli manualmente per
usare il normale flusso guidato.

Se vengono segnalati conflitti, non assumere che tutti i campi siano stati
ripristinati: controllare l'esito prima di salvare le preferenze.

Prima di prove importanti conservare una copia del proprio tema. Il recupero
riduce il rischio, ma non è una garanzia contro qualsiasi guasto o modifica
esterna.
