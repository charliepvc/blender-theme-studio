# Using Theme Studio

<p><strong>English</strong> · <a href="README.it.md">Italiano</a></p>

Theme Studio edits Blender’s global theme. Version 0.5 offers a
**Workspace** choice in the add-on's properties under Preferences > Add-ons:

- **N-panel**: full workspace in **3D View > N > Theme Studio**.
- **Hybrid** (default): common palette and roundness in the N-panel; full workspace in
  **Preferences > Themes**.
- **Preferences > Themes**: full workspace in Themes; no N-panel interface.

**Open Theme Studio** in F3 search or the project top bar follows this choice.
N-panel mode requires an existing 3D View; it does not replace another editor.
All modes share one editing session. Changing placement does not end preview.
The default applies when no workspace choice is saved; existing choices are kept.

The add-on’s default language is English. To use its Italian translation, select
Italian and enable Blender’s interface translation preference. Tooltips follow
Blender’s separate tooltip-translation setting.

## Install

Install the add-on ZIP from Blender’s **Install from Disk** option in Preferences,
then enable Theme Studio. Do not install GitHub’s automatically generated source
archive. See the [README](../../README.md#build-from-source) for source-build
instructions.

## Edit a theme

This guide describes v0.5. Upgrade older installed versions to use this workflow.
The experimental picker is shelved and inactive.

1. Choose a Blender theme from the menu at the top, then choose **Start editing**.
   Selecting another theme during editing first resolves the current session.
   Theme Studio captures the original theme and disables
   text shadows in the new editable copy. Other values remain unchanged until
   you edit them; the original text shadows remain restorable.
2. Use **Theme** for common color groups, **3D View** for viewport colors, and
   **Details** for individual fields organized by category and context.
3. Changes update the theme live. RGBA fields expose alpha; RGB fields do not
   provide an editable alpha channel.
4. Use Theme Studio’s undo and redo controls to review edits during the session.
5. Open **Finish…**, choose **Update existing theme** or **Save as new** when
   available, and confirm **Save and finish**. Use **Save Theme Studio Project…** separately to
   preserve editable project metadata without ending editing.

Theme Studio profiles are JSON files, not Blender’s native XML presets. Profile
compatibility is checked against the catalog and Blender build identity. Do not
change a profile’s identity to force it to load on a different build.

### Save and load native Blender themes

> Available in v0.5; older v0.4.0 ZIPs do not include this workflow.
> Saving a theme does not save all Blender preferences.

In Theme Studio's add-on properties, use **Choose Existing Asset Library** to
select a library already configured in Blender. Selection creates no files.
Theme Studio does not register or change asset libraries for you.

**Finish…** contains the save mode, theme name and library in one dialog.
The native-style library dropdown shows configured library names, not paths.
For a verified user theme, **Update existing theme** keeps its original name and
requires consent before replacement. **Save as new** requires a different name
from the source theme. If the original library is unknown, choose a configured
library; Update is offered only if the original file association can be verified.
Otherwise use Save as new. Built-in or uncertain origins are not Update targets.

**Save and finish** writes native theme XML
under the selected library's lowercase `themes` folder, creating that folder
only when saving, and also writes a user preset for Blender's Themes selector.
Both files must be saved before editing ends. The saved appearance stays active.
If saving fails, editing remains open; if files were saved but session closure
fails, the message identifies saved files and the still-open session.

The status area distinguishes the editing session from saved copies. A reported
preset name identifies Blender's source path, not proof that the visible colors
still match that file. Unknown identity and external changes are shown explicitly.
After a successful save, the result remains visible with the saved name and
confirmation that editing ended. Routine status hides filesystem paths; safety
and recovery details retain them where needed. **Cancel** or Esc closes only the
Finish dialog, not the editing session. The primary confirmation saves and ends
editing; when there are no changes it closes harmlessly without saving.

When a name already exists, choose **Overwrite**, **Rename** or **Cancel**.
Overwrite applies only to the displayed confirmed destinations. Built-in and
extension presets cannot be overwritten. A file changed after confirmation
requires a new decision. If the selected library disappears or is unavailable,
choose a library again; Theme Studio does not silently use another destination.

**Load Blender Theme…** selects an existing native preset and applies it without
starting an editing session. Current editing must first be saved, discarded or
cancelled. Invalid presets are rejected before resolving that work. If applying
a preset fails, Theme Studio attempts to restore the native appearance immediately
before application and reports any recovery failure.

**Export Blender Theme Copy…** writes to a chosen path without registering another
preset or ending editing. **Save Theme Studio Project…** and **Load Theme Studio
Project…** remain separate:
JSON is the editable Theme Studio format, not a native Blender preset. Native XML
includes Blender theme and UI-style settings, not Theme Studio's protected-field
or project metadata.

Saving a theme does **not** save all Blender preferences or guarantee the theme
will be active at the next startup. Global preference saving remains a separate
explicit action. XML files in an asset library do not appear as Asset Browser
assets; that integration is deferred.

### Find individual fields in Details

The accepted category/context organization is restored. Choose a category, then
use its context filter and expand a relevant group. Opening Details from a common
color group restricts the fields to that group; **All Categories** removes that
restriction. Switching pages does not end the session. Individual fields retain
reset and common-follow/separate-edit controls.

### Experimental picker

The picker is shelved following usability and performance problems. Its commands
and context-menu entries are not registered in current development source. Use
common color groups and category/context Details navigation instead.

### Common colors and known limits

The seven common controls are **Backgrounds**, **Panels**, **Text**, **Controls**,
**Borders**, **Selection**, and **Active**. Panels also includes time-ruler
backgrounds. Text drives selected and active Outliner labels as well as ordinary
interface text; the corresponding row backgrounds follow Selection and Active.

A common color is an input, not a promise that every linked field will have
identical RGB. Derived text can adapt for readability across mapped backgrounds.
For example, choosing black can still produce gray menu text. Shared colors
cannot always meet the contrast target on every surface. Individual edits in
Details stay separate from common changes until reconnected. Borders are not
automatically forced to a contrasting color; contrast warnings remain advisory.

New-copy defaults disable only text shadows for controls, panel titles and
tooltips. Profile loading preserves saved values. You can re-enable text shadows
in Details; menu/popup shadows, emboss, gradients and font metrics remain
independent. There is no dedicated coordinated effects section yet.

Some visible effects are native Blender limits: the circular HSV-wheel outline
ignores its stored alpha. Transparent menu backgrounds can also depend on region
overlap and what is drawn beneath them; automatic contrast is not a guarantee
for arbitrary scenes or translucent surfaces.

## Finish a session

- In **Finish…**, expand **Other finish choices** for the alternatives to saving.
- **Restore starting theme and discard changes** attempts to restore fields still owned by the session.
  Detected external changes are preserved and reported.
- **Keep live theme and finish without saving** keeps the live theme and closes the
  session without immediately saving preferences. Blender’s auto-save may save
  them later if it is enabled.
- **Save all preferences…** explicitly saves all Blender preferences, not only
  the theme.

Closing Preferences or hiding the N-panel does not end the session. Reopen Theme
Studio from the project to finish or discard before closing Blender. During a
temporary preview, do not use Blender’s **Save Preferences**: it saves all live
preferences, and Discard cannot undo a preference file already saved manually.
Theme Studio temporarily suspends exit auto-save while it owns that setting;
this is not a veto on native manual saving.

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
