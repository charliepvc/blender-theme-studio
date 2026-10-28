<p align="center">
  <img src="theme_studio/logo.svg" width="120" alt="Logo Theme Studio" />
</p>

<p align="center"><a href="README.md">English</a> · <strong>Italiano</strong></p>

<h1 align="center">Dai forma al tema dell’interfaccia di Blender.</h1>

<p align="center">Uno spazio dedicato per esplorare, regolare e provare in sicurezza i colori del tema di Blender.</p>

Theme Studio modifica live il tema globale di Blender, con sessioni reversibili e controlli raggruppati per significato. Non serve un passaggio separato per applicare le modifiche.

## Cosa offre

- Regola insieme colori correlati, poi affina i singoli campi.
- Esplora i controlli per categoria e contesto, compresi i colori della Vista 3D.
- Annulla e ripeti le modifiche; scarta una sessione per ripristinare i campi ancora gestiti dall’addon.
- Salva una copia del tema separatamente dalle preferenze di Blender.

## Screenshot

Catture reali di una sessione di modifica. L'interfaccia dell'addon è attualmente in italiano; i colori mostrati sono esempi, non un preset incluso.

**Controlli del tema**

![Scheda Tema di Theme Studio con gruppi di colori collegati e arrotondamento dei controlli](docs/media/theme-panel.png)

**Controlli della Vista 3D**

![Scheda Vista 3D di Theme Studio con colori di sfondo, testi, selezione e griglia](docs/media/viewport-panel.png)

## Compatibilità

| Blender | Stato |
| --- | --- |
| **5.2.1 LTS** | Build di riferimento per la prima versione |
| **5.3.x** | Famiglia di sviluppo; verifiche effettuate solo su specifiche build Beta |
| **Altre versioni** | Non verificate; il fallback basato sulla versione non garantisce la compatibilità |

## Installazione

1. Quando disponibile, scarica `theme_studio-0.4.0.zip` dalla sezione [Releases](https://github.com/charliepvc/blender-theme-studio/releases). Usa lo ZIP dell’addon, non l’archivio dei sorgenti GitHub.
2. In Blender, apri `Edit > Preferences > Add-ons` e installa da disco.
3. Seleziona lo ZIP e attiva **Theme Studio**.
4. Apri la barra laterale della Vista 3D con **N**, scegli **Theme Studio**, poi **Inizia a modificare**.

L’addon è disponibile solo nella barra laterale della Vista 3D. Le sue schede sono **Tema**, **Vista 3D** e **Dettagli**. L’interfaccia dell’addon e la [guida all’uso](docs/user/README.md) sono attualmente in italiano.

## Uso sicuro

Le modifiche al tema sono globali e visibili in tutti gli editor di Blender. Nascondere il pannello N non conclude una sessione di modifica. Scegli **Scarta modifiche…** per ripristinare i campi ancora gestiti dalla sessione, conservando le modifiche esterne rilevate, oppure **Termina…** per scegliere come concludere.

Theme Studio non salva automaticamente le preferenze. **Salva tutte le preferenze…** scrive tutte le preferenze di Blender, non soltanto il tema. Durante un’anteprima temporanea, evita il salvataggio manuale delle preferenze di Blender. Se mantieni il tema senza salvarlo subito, il salvataggio automatico di Blender potrebbe salvarlo in seguito. I dati di recupero possono aiutare dopo un’interruzione, ma il recupero non è garantito: conserva una copia dei temi importanti.

## Feedback e segnalazioni

Aiuta a migliorare Theme Studio condividendo bug, comportamenti poco chiari e suggerimenti tramite le [GitHub Issues](https://github.com/charliepvc/blender-theme-studio/issues). Sono particolarmente utili i riscontri sui gruppi di colori collegati e sui pattern: spiega cosa hai modificato, cosa ti aspettavi e cosa è successo invece.

Per i bug, indica versione e hash della build di Blender, versione di Theme Studio, sistema operativo e passaggi per riprodurre il problema. Se possibile, aggiungi uno screenshot dell'area interessata o il messaggio di errore esatto. Rimuovi le informazioni personali da screenshot e log; non caricare preferenze di Blender o file di recupero contenenti dati privati.

## Creazione dai sorgenti

```bash
python -c "from pathlib import Path; Path('dist').mkdir(exist_ok=True)"
python tools/build_dev_addon.py --output dist/theme_studio-0.4.0.zip
```

Il builder usa la libreria standard di Python e include solo i file necessari dell’addon. Non sovrascrive ZIP esistenti: scegli un nuovo nome per un’altra build. È uno ZIP locale di un addon legacy, non una Blender Extension. Lo ZIP 0.4.0 è un candidato locale, non una release pubblicata.

## Link

- [Releases](https://github.com/charliepvc/blender-theme-studio/releases) · download quando disponibili
- [Roadmap (in italiano)](ROADMAP.md)
- [Guida all’uso (in italiano)](docs/user/README.md)

## Licenza

[GPL-3.0](LICENSE)
