# Roadmap

<p><strong>English</strong> · <a href="ROADMAP.it.md">Italiano</a></p>

This roadmap describes possible development in realistic steps, guided by three
principles: **safe, reversible, and semantic**. Priorities may change with user
feedback and technical validation.

## Current status

- **v0.4.0 Preview** — Published as a local-install legacy add-on ZIP, not a
  Blender Extension. Blender **5.2.1 LTS** is the reference build; development
  targets the **5.3.x** family, but version-based catalog fallback does not
  establish compatibility. Current features include live editing, RGBA controls,
  coalesced undo/redo, and journal-based recovery. Saving all Blender preferences
  requires explicit user action.

## Planned

### v0.5.0 — Contextual focus and navigation *(highest priority)*

Make **Details** easier to understand and navigate for first-time users, using
the existing semantic groups and field routing.

- [ ] **Choose the UI location: Themes or N-panel** — Add an add-on preference
  for placing Theme Studio in Blender Preferences > Themes or in the 3D View
  N-panel (the current location). Both locations must share the same session,
  live-editing, history, and restore behavior.
- [ ] **Jump directly to Details** — Open Details from a main Theme or 3D View
  group, with its category and context already filtered.
- [ ] **Context breadcrumb** — Show the source path, such as
  `Details › Text › Controls`, to make the current selection easier to follow.
- [ ] **“Editing: …” indicator** — Identify the group that led to the current
  Details view.
- [ ] **Show affected interface areas** — Provide a static, group-based visual
  explanation of which Blender interface regions a semantic color group affects.
  This uses curated mappings; it is not a picker for arbitrary UI elements.
- [ ] **Clarify linked controls** — Explain “Follow common changes” versus
  “Edit separately” and show how fields relate to a group.
- [ ] **Review semantic color patterns** — Collect concrete expected-versus-
  actual examples before revising how groups link or transform colors. Preserve
  individual control and reversible editing.

### v0.6.0 — Blender Extension packaging

Move to Blender’s Extension format after the planned UX work, to avoid repeating
packaging changes.

- [ ] Create and configure `blender_manifest.toml` for Blender Extensions.
- [ ] Adapt package structure and registration while preserving current behavior.
- [ ] Complete isolated installation and workflow checks on Blender 5.2.1 LTS
  and selected 5.3.x builds.
- [ ] Update English and Italian installation documentation.
- [ ] Assess Extension submission requirements and metadata before considering
  publication on `extensions.blender.org`.

### v0.7.0 — Palette workspace

Give Theme Studio a curated palette workflow. Use mathematical color harmony,
not AI-generated palettes.

- [ ] Add a **Palette** page beside Theme, 3D View, and Details.
- [ ] Offer curated palettes that can be applied reversibly to semantic groups.
- [ ] Generate complementary, analogous, and triadic palettes from a base color
  with Python’s `colorsys` module.
- [ ] Save and load personal palettes, integrating them with the existing profile
  system where appropriate.
- [ ] Apply palettes to selected groups rather than indiscriminately to the whole
  theme.

### v1.0 — Consolidation

Focus on stability and clarity based on real usage and feedback.

- [ ] Refine UX based on observed use.
- [ ] Review edge cases, messages, and consistency.
- [ ] Prioritize robustness over new features.
- [ ] Complete user documentation with screenshots or a demo when available.

## Ideas to investigate *(not commitments)*

- **Interface-target picker (exploratory)** — Let a user point to or click a
  visible Blender UI element, such as a panel background, then select its mapped
  theme field or fields in Details. This would select the theme target, not sample
  a color. Blender’s ability to identify the pointed-to widget and map it
  reliably to theme fields is unverified. Explore separately from the group-based
  affected-areas visualizer; the two could complement each other, and neither is
  currently known to replace the other.
- **Quick Edit popover** — A smaller contextual editor for frequently used
  groups.
- **Recent fields** — Quick access to recently edited controls.
- **Non-automatic contrast guidance** — Informational warnings only; never force
  color corrections.
- **Field discovery** — Improve navigation without adding unnecessary complexity.

## Notes

- Version 1.0 does not require every roadmap item to be complete. Stability is the
  priority.
- Major UX work comes before Extension packaging; settle the interface before
  investing in a different distribution format.
- Verify each Blender version explicitly. Catalog fallback does not replace
  installation, workflow, and restore checks.
