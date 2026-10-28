# Using Theme Studio

<p><strong>English</strong> · <a href="README.it.md">Italiano</a></p>

Theme Studio edits Blender’s global theme. Find it in the 3D View sidebar under
**N > Theme Studio**. A Preferences > Themes location is planned, but is not
available yet.

The add-on’s default language is English. To use its Italian translation, select
Italian and enable Blender’s interface translation preference. Tooltips follow
Blender’s separate tooltip-translation setting.

## Install

Install the add-on ZIP from Blender’s **Install from Disk** option in Preferences,
then enable Theme Studio. Do not install GitHub’s automatically generated source
archive. See the [README](../../README.md#build-from-source) for source-build
instructions.

## Edit a theme

1. Choose **Start editing**. Theme Studio prepares the initial copy; the theme
   does not change until you edit a field.
2. Use **Theme** for common color groups, **3D View** for viewport colors, and
   **Details** for individual fields filtered by category and context.
3. Changes update the theme live. RGBA fields expose alpha; RGB fields do not
   provide an editable alpha channel.
4. Use Theme Studio’s undo and redo controls to review edits during the session.
5. Save a theme copy to a separate file if you want to keep and reopen it later.

Theme Studio profiles are JSON files, not Blender’s native XML presets. Profile
compatibility is checked against the catalog and Blender build identity. Do not
change a profile’s identity to force it to load on a different build.

## Finish a session

- **Discard changes…** attempts to restore fields still owned by the session.
  Detected external changes are preserved and reported.
- **Finish… > Use without saving now** keeps the live theme and closes the
  session without immediately saving preferences. Blender’s auto-save may save
  them later if it is enabled.
- **Save all preferences…** explicitly saves all Blender preferences, not only
  the theme.

Hiding the N-panel does not end the session. Finish or discard your work before
closing Blender. During a temporary preview, do not manually save Blender’s
preferences.

## Errors and recovery

The recovery journal stores information used to recover after an interruption.
A pending recovery blocks editing until resolved. Follow the actions shown in the
panel; do not delete the journal to bypass the block. Completed and validated
sessions are not pending recoveries. After a Blender update, an unfinished
session from another build may remain; it is not applied automatically to the
new build.

**Keep data and continue…** keeps the current theme without restoring the earlier
one. After confirmation, Theme Studio verifies and keeps a copy of the recovery
data; it does not move or delete the originals. The decision applies only to
those exact contents. If an original changes or the copy can no longer be
verified, the data requires attention again. This action does not save
preferences or apply colors to the current theme.

Restore actions are available only when recovery data is compatible and can be
executed. File paths and complete error details remain available in technical
details; you do not need to edit them manually for the guided workflow.

If Theme Studio reports conflicts, do not assume every field was restored.
Review the result before saving preferences.

Keep a theme copy before important experiments. Recovery reduces risk, but does
not guarantee protection from every failure or external change.
