# Roadmap

<p><strong>English</strong> · <a href="ROADMAP.it.md">Italiano</a></p>

Theme Studio follows three principles: **safe, reversible, and semantic**.
This roadmap separates release checks from new features. The order below is the
recommended next sequence, not authorization to implement or publish everything.

## Current status — v0.5.0 release, 2026-11-10

- **Release:** v0.5.0 Preview, a legacy add-on ZIP, not a Blender Extension.
  The release ZIP preserves the verified r2 bytes: exact 14-file source parity and
  eight passing isolated installed-ZIP lifecycle/recovery checks on 5.2.1. Earlier
  v0.4.0 packages remain unchanged. See [release notes](docs/releases/0.5.0.md).
- **Included:** accepted smart-color fixes, category/context Details,
  selectable workspaces, native theme save/load/export and source-aware Finish.
  Older v0.4.0 ZIPs do not contain all these changes.
- **Workspaces:** Hybrid is the default; full N-panel and Preferences > Themes
  are selectable in add-on properties. All share one editing session.
- **Evidence:** the latest full Python suite passed 430 tests. Previously recorded
  focused native Finish verification passed 25 checks on Blender 5.2.1 LTS
  `9e2066aef7ef`, including paired saves and exact automated-sandbox restoration.
  User accepted Finish interactions and reported positive overall manual feedback.
- **Limits:** user explicitly confirmed both manual save paths and accepted the
  installed candidate overall. This is not instrumented all-mode visual coverage
  or a real crash test. An earlier manual
  process ended without a final restoration report;
  its exact restoration is unverified. Initial enum setup warnings remain.
- **Compatibility:** 5.2.1 LTS is the reference build; 5.3.x is the development
  family. Older candidate r4 checks on 5.3.0 Beta `ace25df17a10` do not certify
  current source, the published ZIP or every 5.3 build. Catalog fallback is not
  compatibility evidence.
- **Picker:** shelved after failed usability trials; not registered and not a
  v0.5 requirement. Earlier picker experiments are historical evidence only.

## A. v0.5 release path and evidence limits

Approved scope (2026-11-09): ship the implemented color, workspace and save/session
work after bounded validation, fixing release blockers without adding section B
features. Prioritize Blender 5.2.1 LTS `9e2066aef7ef`; 5.3 remains experimental,
with no new compatibility claim. User authorized the v0.5.0 public release on
2026-11-10. Open evidence items below are not claims of universal coverage.

### 1. Close the remaining acceptance gaps

- [x] Agree the v0.5 release scope and select the exact Blender builds to support:
  existing functionality, Blender 5.2.1 LTS `9e2066aef7ef` first.
- [x] Confirm understandable Save as new and Update existing outcomes/session
  closure: explicitly accepted by the user. Do not repeat without a relevant change.
- [ ] Record itemized visual coverage of selector/status/layout/responsiveness in
  N-panel, Hybrid and Preferences if a concrete issue calls for it. Overall installed
  candidate acceptance is already recorded; this is not a new generic release gate.
- [ ] Verify saving, selecting and reloading a native theme preserves appearance;
  confirm safe library `themes` creation, replacement consent and collision handling.
  Reuse valid automated evidence; do not rebuild already implemented functionality.
- [ ] Triage observed defects and enum warnings. Fix reproducible release blockers;
  document harmless limits. Do not turn this into an unbounded redesign.

Why first: establish what still fails before spending effort packaging it.

### 2. Prepare one local release candidate

- [ ] Set consistent v0.5 version metadata and align English/Italian release notes,
  instructions and screenshots with the actual candidate.
- [x] Run the full Python suite after final source changes; run focused native
  checks for affected behavior on the selected builds.
- [x] Build a distinct, non-overwriting legacy ZIP and verify source/package parity.

Why second: test the exact deliverable, not a manually copied development folder.

### 3. Validate the installed candidate

- [ ] In disposable settings, install and enable the ZIP, edit a theme, save/load,
  use overrides and undo/redo, end/discard sessions and exercise recovery.
- [x] Verify disable/remove behavior and exact restoration where required on each
  build for which compatibility will be claimed. Preference-save probes require
  disposable config and explicit authorization; never use personal preferences.
- [x] Obtain user acceptance of this installed candidate. A source trial alone
  does not establish ZIP installation or release acceptance.

Why third: catch missing files, lifecycle defects and installation regressions.

### 4. Publish only after acceptance and authorization

- [ ] Record the verified candidate, checksum, supported builds and known limits.
- [ ] Commit/push the final private checkpoint, then review the allow-listed public
  export through the separate publishing workflow.
- [ ] Publish/tag/release only with explicit authorization. Never push private
  history to the public repository.

The missing report from the closed manual window remains a historical evidence
limit, not an invitation to relaunch it and claim retroactive restoration.

## B. New functionality — separate, ordered backlog

These items remain available for scope decisions. No release version is assigned
here; selecting one requires its own design and validation, not silent inclusion.

1. **Clarify linked controls and affected areas.** Explain “Follow common changes”
   versus “Edit separately” and each field's parent relationship. Start with clear
   labels/help; add curated visual explanations only where they solve observed
   confusion. Preserve accepted category/context Details.
2. **Audit unresolved native color consumers.** Prioritize real rendering defects,
   shared/transparent contexts and Image `face_mode_select`. Catalog membership
   alone does not prove rendered behavior. Reassess gray menu text only with a
   concrete problem; the accepted smart-color iteration does not promise pure
   black or identical text across states. The HSV-wheel outline ignores alpha.
3. **Add coordinated non-color effect controls.** Design explicit controls for
   text shadows, menu/popup shadows, emboss and gradients. Existing Details fields
   remain available; new copies currently disable only text shadows, reversibly.
4. **Research a browsable theme collection in the Asset Browser.** First establish
   native API feasibility and representation; XML files in a library folder are
   not automatically Asset Browser assets, and a `.blend` file does not replace
   native XML or editable project data. Implement only after workflow approval.

Additional user-requested future UI work: compact, persistent shortcut buttons
for settings, support/donations and GitHub. Design placement, native icons,
accessibility and approved link destinations before implementation. No donation
provider or URL is selected; no payments or embedded tracking are implied. This
does not expand the current v0.5 release scope.

This order improves understanding before expanding controls, and leaves the most
uncertain integration until the existing save workflow is stable.

## C. Shelved work — no automatic restart

- Experimental picker, precise region destinations and contextual picking fixes.
  Resume only after an explicit new decision. Do not replace target selection
  with color sampling or revive the rejected element-based Details organization.

## Later milestones

### v0.6.0 — Blender Extension packaging

After v0.5 and any selected major UX changes, without making Extension format a
v0.5 prerequisite:

- [ ] Create `blender_manifest.toml` and adapt packaging/registration.
- [ ] Verify isolated install, workflow and restoration on selected 5.2.1/5.3 builds.
- [ ] Update English/Italian installation guides and assess Extension submission
  metadata/requirements before considering `extensions.blender.org` publication.

### v0.7.0 — Palette workspace

- [ ] Design a Palette page alongside Theme, 3D View and Details.
- [ ] Offer curated, reversibly applied semantic palettes.
- [ ] Generate complementary, analogous and triadic palettes with Python `colorsys`,
  not AI-generated palettes.
- [ ] Save/load personal palettes and apply them only to selected groups, integrating
  with profiles where appropriate.

### v1.0 — Stability and clarity

- [ ] Refine UX from observed usage; review edge cases, messages and consistency.
- [ ] Prioritize robustness over feature count; finish guides/screenshots or a demo.

## Ideas to investigate — not commitments

- Quick Edit popover for frequently used groups.
- Recent fields and simpler field discovery.
- Informational contrast guidance, never forced color correction.

Version 1.0 does not require every backlog item. Verify compatibility explicitly;
never infer it from version fallback or unrelated historical checks.
