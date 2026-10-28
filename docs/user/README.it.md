# Usare Theme Studio

<p><a href="README.md">English</a> · <strong>Italiano</strong></p>

Theme Studio modifica il tema globale di Blender. L’interfaccia si trova nella
Vista 3D, nella barra laterale **N > Theme Studio**. La posizione alternativa in
Preferenze > Themes è pianificata, ma non è ancora disponibile.

La lingua predefinita dell’addon è l’inglese. Per usare la traduzione italiana,
seleziona l’italiano e attiva la traduzione dell’interfaccia nelle preferenze di
Blender. I tooltip seguono l’impostazione separata di Blender.

## Installazione

Installa lo ZIP dell’addon con **Install from Disk** nelle Preferenze di Blender,
poi attiva Theme Studio. Non installare l’archivio dei sorgenti generato
automaticamente da GitHub. Per creare il pacchetto dai sorgenti, consulta il
[README](../../README.it.md#creazione-dai-sorgenti).

## Modificare un tema

1. Scegli **Start editing** (**Inizia a modificare**). Theme Studio prepara la
   copia iniziale; il tema non cambia finché non modifichi un campo.
2. Usa **Theme** (**Tema**) per i gruppi di colori comuni, **3D View** (**Vista 3D**)
   per i colori del viewport e **Details** (**Dettagli**) per i singoli campi,
   filtrati per categoria e contesto.
3. Le modifiche aggiornano il tema live. I campi RGBA espongono l’opacità; i campi
   RGB non hanno un canale alpha modificabile.
4. Usa i comandi di annullamento e ripetizione di Theme Studio per rivedere le
   modifiche durante la sessione.
5. Salva una copia del tema in un file separato per conservarla e riaprirla in
   seguito.

I profili di Theme Studio sono file JSON, non preset XML nativi di Blender. La
compatibilità viene controllata in base al catalogo e all’identità della build di
Blender. Non modificare l’identità di un profilo per forzarne il caricamento su
un’altra build.

## Terminare una sessione

- **Discard changes…** (**Scarta le modifiche…**) tenta di ripristinare i campi
  ancora gestiti dalla sessione. Le modifiche esterne rilevate vengono conservate
  e segnalate.
- **Finish… > Use without saving now** (**Termina… > Usa senza salvare ora**)
  mantiene il tema live e chiude la sessione senza salvare subito le preferenze.
  Se attivo, il salvataggio automatico di Blender potrebbe salvarle in seguito.
- **Save all preferences…** (**Salva tutte le preferenze…**) salva esplicitamente
  tutte le preferenze di Blender, non soltanto il tema.

Nascondere la barra laterale N non termina la sessione. Termina o scarta il lavoro
prima di chiudere Blender. Durante un’anteprima temporanea, non salvare
manualmente le preferenze di Blender.

## Errori e recupero

Il journal conserva informazioni utili per il recupero dopo un’interruzione. Un
recupero pendente blocca le modifiche finché non viene risolto. Segui le azioni
mostrate nel pannello; non cancellare il journal per aggirare il blocco. Le
sessioni concluse e verificate non sono recuperi pendenti. Dopo un aggiornamento
di Blender può restare una sessione non conclusa di un’altra build: non viene
applicata automaticamente alla nuova build.

**Keep data and continue…** (**Conserva i dati e continua…**) mantiene il tema
attuale senza ripristinare quello precedente. Dopo la conferma, Theme Studio
verifica e conserva una copia dei dati di recupero; non sposta né cancella gli
originali. La scelta vale solo per quei contenuti esatti. Se un originale cambia
o la copia non è più verificabile, i dati richiedono nuovamente attenzione.
Questa azione non salva le preferenze e non applica colori al tema corrente.

Le azioni di ripristino sono disponibili solo se i dati sono compatibili e il
recupero è eseguibile. I percorsi e i messaggi di errore completi restano nei
dettagli tecnici; non serve modificarli manualmente per seguire il flusso guidato.

Se Theme Studio segnala conflitti, non presumere che tutti i campi siano stati
ripristinati. Controlla l’esito prima di salvare le preferenze.

Prima di prove importanti, conserva una copia del tema. Il recupero riduce il
rischio, ma non protegge da ogni possibile errore o modifica esterna.
