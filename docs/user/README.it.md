# Usare Theme Studio

<p><a href="README.md">English</a> · <strong>Italiano</strong></p>

Theme Studio modifica il tema globale di Blender. La versione 0.5 offre
la scelta **Area di lavoro** nelle proprietà dell'addon in Preferenze > Add-on:

- **Pannello N**: interfaccia completa in **Vista 3D > N > Theme Studio**.
- **Ibrida** (predefinita): colori capostipiti e arrotondamento nel pannello N; interfaccia
  completa in **Preferenze > Temi**.
- **Preferenze > Temi**: interfaccia completa nei Temi; nessuna interfaccia nel pannello N.

**Apri Theme Studio** nella ricerca F3 o nella barra superiore segue questa scelta.
La modalità pannello N richiede una Vista 3D esistente; non sostituisce altri editor.
Tutte le modalità condividono una sessione. Cambiare posizione non termina l'anteprima.
Il valore predefinito vale senza una scelta salvata; le scelte esistenti restano invariate.

La lingua predefinita dell’addon è l’inglese. Per usare la traduzione italiana,
seleziona l’italiano e attiva la traduzione dell’interfaccia nelle preferenze di
Blender. I tooltip seguono l’impostazione separata di Blender.

## Installazione

Installa lo ZIP dell’addon con **Install from Disk** nelle Preferenze di Blender,
poi attiva Theme Studio. Non installare l’archivio dei sorgenti generato
automaticamente da GitHub. Per creare il pacchetto dai sorgenti, consulta il
[README](../../README.it.md#creazione-dai-sorgenti).

## Modificare un tema

Questa guida descrive la v0.5. Aggiorna le versioni già installate per usare questo
flusso. Il picker sperimentale è accantonato e inattivo.

1. Scegli un tema Blender dal menu in alto, poi **Start editing** (**Inizia a modificare**).
   Se scegli un altro tema durante la modifica, prima devi risolvere la sessione corrente.
   Theme Studio acquisisce il
   tema originale e disattiva le ombre dei testi nella nuova copia modificabile.
   Gli altri valori restano invariati finché non li modifichi; le ombre originali
   restano ripristinabili.
2. Usa **Theme** (**Tema**) per i gruppi di colori comuni, **3D View** (**Vista 3D**)
    per i colori del viewport e **Details** (**Dettagli**) per i singoli campi,
    organizzati per categoria e contesto.
3. Le modifiche aggiornano il tema live. I campi RGBA espongono l’opacità; i campi
   RGB non hanno un canale alpha modificabile.
4. Usa i comandi di annullamento e ripetizione di Theme Studio per rivedere le
   modifiche durante la sessione.
5. Apri **Termina…**, scegli **Aggiorna tema esistente** o **Salva come nuovo**
   quando disponibili, poi conferma **Salva e termina**. Usa separatamente **Salva progetto Theme Studio…**
   per conservare i metadati modificabili senza terminare la modifica.

I profili di Theme Studio sono file JSON, non preset XML nativi di Blender. La
compatibilità viene controllata in base al catalogo e all’identità della build di
Blender. Non modificare l’identità di un profilo per forzarne il caricamento su
un’altra build.

### Salvare e caricare temi nativi Blender

> Disponibile nella v0.5; gli ZIP v0.4.0 precedenti non includono questo flusso.
> Salvare un tema non salva tutte le preferenze di Blender.

Nelle proprietà dell'addon Theme Studio, usa la scelta della libreria asset
esistente per selezionare una libreria già configurata in Blender. La selezione
non crea file. Theme Studio non registra o modifica le librerie asset.

**Termina…** riunisce modalità di salvataggio, nome e libreria in un solo dialogo.
La tendina nativa mostra i nomi delle librerie configurate, non i percorsi.
Per un tema utente verificato, **Aggiorna tema esistente** mantiene il nome originale
e richiede il consenso prima della sostituzione. **Salva come nuovo** richiede un
nome diverso dal tema di partenza. Se la libreria originale è sconosciuta, scegli
una libreria configurata: Aggiorna compare solo se l'associazione con il file
originale è verificabile. Altrimenti usa Salva come nuovo. I temi inclusi con
Blender e le origini incerte non sono destinazioni di aggiornamento.

**Salva e termina** scrive l'XML nativo nella
sottocartella minuscola `themes` della libreria scelta, creandola solo al
salvataggio, e crea anche il preset utente per il selettore Temi di Blender.
La sessione termina solo dopo il salvataggio di entrambi i file; l'aspetto resta
attivo. Se il salvataggio fallisce, la modifica resta aperta. Se i file sono stati
salvati ma la chiusura della sessione fallisce, il messaggio indica i file salvati
e la sessione ancora aperta.

L'area di stato distingue la sessione di modifica dalle copie salvate. Il nome di
un preset indica il percorso di origine riportato da Blender, non garantisce che
i colori visibili corrispondano ancora al file. Identità sconosciuta e modifiche
esterne sono indicate esplicitamente. Dopo un salvataggio riuscito restano visibili
il nome salvato e la conferma della fine della modifica. Lo stato ordinario nasconde
i percorsi, disponibili nei dettagli di sicurezza e recupero quando necessari.
**Annulla** o Esc chiude soltanto il dialogo Termina, non la sessione di modifica.
La conferma principale salva e termina; in assenza di modifiche chiude senza salvare.

Se il nome esiste, scegli **Sovrascrivi**, **Rinomina** o **Annulla**. La
sovrascrittura riguarda solo le destinazioni mostrate e confermate. I preset
inclusi con Blender o gestiti dalle estensioni restano protetti. Un file cambiato
dopo la conferma richiede una nuova decisione. Se la libreria scelta non è più
disponibile, selezionala nuovamente: non viene scelta un'altra destinazione in silenzio.

**Carica tema Blender…** applica un preset nativo esistente senza iniziare una
sessione di modifica. Il lavoro corrente richiede prima Salva, Scarta o Annulla.
I preset non validi sono rifiutati prima di risolvere quel lavoro. Se l'applicazione
fallisce, Theme Studio tenta di ripristinare l'aspetto nativo precedente al
caricamento e segnala eventuali problemi di recupero.

**Esporta copia del tema Blender…** scrive nel percorso scelto senza registrare un
altro preset o terminare la modifica. **Salva progetto Theme Studio…** e
**Carica progetto Theme Studio…**
restano separati: JSON è il formato modificabile di Theme Studio, non un preset
nativo. XML include tema e stili dell'interfaccia di Blender, non i metadati del
progetto o dei campi separati dalle modifiche comuni.

Salvare un tema **non** salva tutte le preferenze di Blender e non garantisce
che il tema sia attivo al prossimo avvio. Il salvataggio globale resta un'azione
esplicita separata. Gli XML nella libreria non diventano asset nell'Asset Browser:
questa integrazione è rimandata.

### Trovare i singoli campi nei Dettagli

È ripristinata l'organizzazione accettata per categoria e contesto. Scegli una
categoria, usa il filtro del contesto e apri il gruppo pertinente. Aprire i
Dettagli da un colore comune limita i campi a quel gruppo; **Tutte le categorie**
rimuove il filtro. Cambiare pagina non termina la sessione. Ogni campo conserva
il ripristino e i comandi di collegamento/separazione dalle modifiche comuni.

### Picker sperimentale accantonato

Il picker è accantonato dopo problemi di usabilità e prestazioni. I suoi comandi
e le voci dei menu contestuali non sono registrati nei sorgenti correnti. Usa
i colori comuni e i filtri categoria/contesto dei Dettagli.

### Colori comuni e limiti noti

I sette controlli comuni sono **Sfondi**, **Pannelli**, **Testo**, **Controlli**,
**Bordi**, **Selezione** e **Attivo**. Pannelli comprende anche gli sfondi dei
righelli temporali. Testo governa le etichette selezionate e attive dell’Outliner,
oltre al testo ordinario dell’interfaccia; gli sfondi delle righe seguono
Selezione e Attivo.

Un colore comune è un valore di partenza, non la promessa di RGB identici in
ogni campo collegato. Il testo derivato può adattarsi alla leggibilità sugli
sfondi mappati. Per esempio, scegliendo nero alcuni testi dei menu possono
restare grigi. I colori condivisi non possono sempre soddisfare il contrasto
su tutte le superfici. Le modifiche individuali nei Dettagli restano separate
dalle modifiche comuni finché non vengono ricollegate. I bordi non vengono
forzati automaticamente a un colore contrastante; gli avvisi restano consultivi.

Le nuove copie disattivano solo le ombre dei testi di controlli, titoli dei
pannelli e tooltip. Caricare un profilo conserva i valori salvati. Puoi
riattivare le ombre nei Dettagli; ombre di menu/popup, rilievi, gradienti e
metriche dei caratteri restano indipendenti. Non esiste ancora una sezione
dedicata al controllo coordinato degli effetti.

Alcuni effetti visibili dipendono da limiti nativi di Blender: il contorno
circolare della ruota HSV ignora l’alpha salvato. Gli sfondi trasparenti dei menu
possono dipendere anche dalla sovrapposizione delle regioni e da ciò che viene
disegnato sotto; il contrasto automatico non è garantito per scene arbitrarie
o superfici semitrasparenti.

## Terminare una sessione

- In **Termina…**, espandi **Altre opzioni di chiusura** per le alternative al salvataggio.
- **Ripristina il tema iniziale e scarta le modifiche** tenta di ripristinare i campi
  ancora gestiti dalla sessione. Le modifiche esterne rilevate vengono conservate
  e segnalate.
- **Mantieni il tema attivo e termina senza salvare**
  mantiene il tema live e chiude la sessione senza salvare subito le preferenze.
  Se attivo, il salvataggio automatico di Blender potrebbe salvarle in seguito.
- **Save all preferences…** (**Salva tutte le preferenze…**) salva esplicitamente
  tutte le preferenze di Blender, non soltanto il tema.

Chiudere le Preferenze o nascondere il pannello N non termina la sessione.
Riapri Theme Studio dal progetto per terminare o scartare prima di chiudere
Blender. Durante l'anteprima non usare **Salva preferenze** di Blender: salva
tutte le preferenze live e Scarta non annulla un file già salvato manualmente.
Theme Studio sospende temporaneamente il salvataggio automatico all'uscita finché
gestisce quell'impostazione; non blocca il salvataggio manuale nativo.

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
