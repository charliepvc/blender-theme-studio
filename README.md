<p align="center">
  <img src="theme_studio/logo.svg" width="120" alt="Theme Studio logo" />
</p>

<p align="center"><strong>English</strong> · <a href="README.it.md">Italiano</a></p>

<h1 align="center">Shape Blender’s interface theme.</h1>

<p align="center">A focused workspace for exploring, adjusting, and safely trying Blender theme colors.</p>

Theme Studio edits Blender’s global theme live, with reversible sessions and controls grouped by meaning. No separate Apply step.

## What it does

- Adjust related interface colors together, then fine-tune individual fields.
- Browse theme controls by category and context, including 3D View colors.
- Undo and redo edits; discard a session to restore fields still owned by it.
- Save a theme copy separately from Blender preferences.

## Screenshots

Real captures from an editing session with the Italian interface. The add-on defaults to English and also supports Italian; colors shown are examples, not a bundled preset.

**Theme controls**

![Theme Studio Theme tab with linked color groups and control roundness](docs/media/theme-panel.png)

**3D View controls**

![Theme Studio 3D View tab with background, text, selection, and grid colors](docs/media/viewport-panel.png)

## Compatibility

| Blender | Status |
| --- | --- |
| **5.2.1 LTS** | Reference build for the first release |
| **5.3.x** | Development family; checks cover specific Beta builds only |
| **Other versions** | Not verified; version-based fallback does not guarantee compatibility |

## Install

1. Download `theme_studio-0.4.0.zip` from [Releases](https://github.com/charliepvc/blender-theme-studio/releases) when available. Use the add-on ZIP, not GitHub’s source archive.
2. In Blender, open `Edit > Preferences > Add-ons` and install from disk.
3. Select the ZIP and enable **Theme Studio**.
4. Open the 3D View sidebar with **N**, choose **Theme Studio**, then **Start editing**.

The add-on currently appears only in the 3D View sidebar. Its tabs are **Theme**, **3D View**, and **Details**. English is the default interface language. Italian is supplied through Blender's native translations: choose Italian and enable **Interface** translation in Blender's preferences. Tooltips follow Blender's separate tooltip translation setting. Other languages use the English source text for Theme Studio's own messages. The [user guide](docs/user/README.md) is currently in Italian.

## Use safely

Theme changes are global and visible across Blender editors. Hiding the N-panel does not end an editing session. Choose **Discard changes…** to restore session-owned fields while preserving detected external changes, or **Finish…** to choose how to end the session.

Theme Studio does not automatically save preferences. **Save all preferences…** writes all Blender preferences, not only the theme. Avoid Blender's manual preference save during a temporary preview. After keeping a theme without saving immediately, Blender's own auto-save may save it later. Recovery data can help after an interruption, but recovery is not guaranteed; keep a copy of important themes.

## Feedback and issues

Help shape Theme Studio by sharing bugs, confusing behavior, and suggestions through [GitHub Issues](https://github.com/charliepvc/blender-theme-studio/issues). Feedback on linked color groups and patterns is especially welcome: explain what you changed, what you expected, and what happened instead.

For bugs, include your Blender version and build hash, Theme Studio version, operating system, and steps to reproduce. If possible, add a screenshot showing the affected area or the exact error message. Remove personal information from screenshots and logs; do not upload Blender preferences or recovery files containing private data.

## Build from source

```bash
python -c "from pathlib import Path; Path('dist').mkdir(exist_ok=True)"
python tools/build_dev_addon.py --output dist/theme_studio-0.4.0.zip
```

The builder uses Python’s standard library and includes only required add-on files. It refuses to overwrite an existing ZIP; choose a new filename for another build. This is a legacy add-on ZIP for local installation, not a Blender Extension. Version 0.4.0 is an early preview; see [Releases](https://github.com/charliepvc/blender-theme-studio/releases) for available downloads and known limitations.

## Links

- [Releases](https://github.com/charliepvc/blender-theme-studio/releases) · downloads when available
- [Roadmap (Italian)](ROADMAP.md)
- [User guide (Italian)](docs/user/README.md)

## License

[GPL-3.0](LICENSE)
