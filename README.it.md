<p>
  <img src="theme_studio/logo.svg" width="72" alt="Logo di Theme Studio" />
</p>

<p><a href="README.md">English</a> · <strong>Italiano</strong></p>

# Blender Theme Studio

## Dai forma all’interfaccia di Blender, a modo tuo.

Esplora più facilmente le numerose impostazioni del tema di Blender. Theme Studio raggruppa i colori correlati per funzione, permette di modificarli in tempo reale e rende reversibile ogni sessione di lavoro.

![Blender Theme Studio aperto nella Vista 3D di Blender, con il pannello dell’addon accanto alla scritta “Theme Studio”](docs/media/hero.jpg)

La schermata hero è stata acquisita con una build Beta di Blender 5.3.0; non dimostra la compatibilità di questa versione localizzata con Blender 5.3.

## Scarica l’anteprima

[**Scarica Theme Studio 0.4.0 per Blender 5.2.1 LTS**](https://github.com/charliepvc/blender-theme-studio/releases/download/v0.4.0/theme_studio-0.4.0.zip) · [Note di rilascio e limiti noti](https://github.com/charliepvc/blender-theme-studio/releases/tag/v0.4.0)

**Versione di anteprima.** Installa lo ZIP dalle preferenze degli addon di Blender: è un addon legacy per installazione locale, non una Blender Extension. La build di riferimento è Blender **5.2.1 LTS**.

## Guarda Theme Studio in azione

La demo di 30 secondi mostra la modifica dei colori collegati, l’aggiornamento immediato dell’interfaccia, le regolazioni di dettaglio e i comandi della sessione.

![Demo di 30 secondi di Theme Studio: modifica dei colori collegati, aggiornamenti live in Blender, controlli di dettaglio e azioni della sessione](docs/media/demo.gif)

La demo dovrebbe mostrare una sessione reale: modifica un gruppo di colori collegati, osserva il cambiamento in Blender, regola un singolo campo in Dettagli, poi annulla o scarta le modifiche.

## Un modo più diretto per dare forma ai colori di Blender

### Modifica insieme i colori correlati

Regola gruppi selezionati, come sfondi, pannelli, testo, controlli, bordi e selezione. Apri Dettagli quando vuoi intervenire sui singoli campi.

### Osserva subito il risultato

Le modifiche aggiornano in tempo reale il tema globale di Blender. Confronta il tema iniziale con le modifiche correnti e usa i comandi di annullamento e ripetizione durante la sessione.

### Mantieni il controllo

Scarta le modifiche per ripristinare i campi ancora gestiti dalla sessione, conservando le modifiche esterne rilevate. Oppure termina mantenendo il tema live. Se vuoi riaprire il tema in seguito, salvalo in un file separato.

## Nell’interfaccia di Blender

Queste schermate autentiche mostrano Theme Studio con l’interfaccia italiana di Blender. L’inglese è la lingua predefinita dell’addon; l’italiano è disponibile tramite il sistema di traduzione nativo di Blender. I colori mostrati sono esempi, non preset inclusi.

**Controlli del tema** — Regola i colori correlati dell’interfaccia e l’arrotondamento dei controlli.

![Scheda Theme di Theme Studio nell’interfaccia italiana di Blender, con gruppi di colori collegati e arrotondamento dei controlli](docs/media/theme-panel.png)

**Controlli della Vista 3D** — Regola sfondi, intestazioni, testo, selezione e guide del viewport.

![Scheda 3D View di Theme Studio nell’interfaccia italiana di Blender, con controlli per sfondo del viewport, testo, selezione e griglia](docs/media/viewport-panel.png)

## Installazione

1. Scarica [`theme_studio-0.4.0.zip`](https://github.com/charliepvc/blender-theme-studio/releases/download/v0.4.0/theme_studio-0.4.0.zip). Non usare l’archivio dei sorgenti generato automaticamente da GitHub.
2. In Blender, apri **Edit → Preferences → Add-ons** e scegli **Install from Disk**.
3. Seleziona lo ZIP scaricato e attiva **Theme Studio** nell’elenco degli addon.
4. Nella Vista 3D, premi **N** per aprire la barra laterale. Scegli **Theme Studio**, poi **Start editing** (**Inizia a modificare**).

Theme Studio si trova nella barra laterale della Vista 3D. Le sue pagine sono **Theme** (**Tema**), **3D View** (**Vista 3D**) e **Details** (**Dettagli**). La lingua predefinita è l’inglese. Per usare la traduzione italiana fornita, seleziona l’italiano e attiva la traduzione **Interface** nelle preferenze di Blender; la traduzione dei tooltip segue un’impostazione separata.

## Compatibilità

| Versione di Blender | Stato |
| --- | --- |
| **5.2.1 LTS** | Build di riferimento; verificati installazione dello ZIP localizzato e flussi di lavoro principali. |
| **5.3.x** | Famiglia di sviluppo. Le verifiche precedenti riguardavano specifiche build Beta; questa versione localizzata non è stata verificata nuovamente su 5.3. |
| **Altre versioni** | Non verificate. Il fallback del catalogo basato sulla versione di Blender non dimostra la compatibilità. |

## Importante: come funzionano le modifiche al tema

- **Le modifiche sono globali.** Gli altri editor di Blender mostrano il tema modificato durante la sessione.
- **Nascondere la barra laterale N non termina la sessione.** Termina o scarta la sessione prima di chiudere Blender.
- **Scarta e Termina hanno effetti diversi.** **Discard changes…** (**Scarta le modifiche…**) tenta di ripristinare i campi gestiti dalla sessione e segnala i conflitti; le modifiche esterne rilevate vengono conservate. **Finish…** (**Termina…**) permette di mantenere il tema live, salvandolo esplicitamente oppure no.
- **Theme Studio non salva automaticamente le preferenze di Blender.** **Save all preferences…** (**Salva tutte le preferenze…**) salva tutte le preferenze di Blender, non solo il tema. Durante un’anteprima temporanea, evita il salvataggio manuale delle preferenze.
- **Mantenere il tema senza salvarlo non lo rende permanente.** Se attivo, il salvataggio automatico di Blender potrebbe salvare il tema live in seguito. I dati di recupero possono aiutare dopo un’interruzione, ma non garantiscono il recupero. Per i lavori importanti, conserva una copia separata del tema.

## Segnalazioni e suggerimenti

[Segnala un problema o proponi un miglioramento nelle GitHub Issues](https://github.com/charliepvc/blender-theme-studio/issues). Per una segnalazione utile, indica versione e hash della build di Blender, versione di Theme Studio, sistema operativo, passaggi per riprodurre il problema e risultato atteso e ottenuto. Se possibile, aggiungi uno screenshot o il messaggio di errore esatto. Rimuovi le informazioni personali; non caricare preferenze di Blender o file di recupero privati.

Sono particolarmente utili i riscontri sui gruppi di colori collegati: descrivi quali colori hai modificato e quale risultato ti aspettavi.

## Documentazione e sviluppo

- [Guida all’uso](docs/user/README.md)
- [Roadmap](ROADMAP.md)
- [Tutte le release e note di rilascio](https://github.com/charliepvc/blender-theme-studio/releases)
- [Istruzioni per creare il pacchetto dai sorgenti](#creazione-dai-sorgenti)
- [Licenza GPL-3.0](LICENSE)

### Creazione dai sorgenti

Il builder di questo repository crea uno ZIP locale per addon legacy, non una Blender Extension. Crea prima la cartella di destinazione; il builder non sovrascrive i file esistenti.

```bash
python -c "from pathlib import Path; Path('dist').mkdir(exist_ok=True)"
python tools/build_dev_addon.py --output dist/theme_studio-0.4.0.zip
```

## Licenza

Theme Studio è distribuito secondo la [GNU General Public License versione 3.0](LICENSE).
