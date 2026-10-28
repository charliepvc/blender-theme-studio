"""Native 3D View sidebar UI; every editable widget addresses Draft, never theme RNA.

register() is intentionally separate from the package entry point. Registration
does not create storage, read a snapshot, or change Blender preferences. A live
session is retained if lifecycle cancellation fails; unregister then fails before
removing controls/handlers so cancellation can be retried.
"""

import copy
import hashlib
import json
import math
from pathlib import Path
import traceback
import uuid

import bpy
import blf
from bpy.app.handlers import persistent
from bpy.props import (
    BoolProperty, BoolVectorProperty, CollectionProperty, EnumProperty, FloatProperty,
    FloatVectorProperty, IntProperty, IntVectorProperty, PointerProperty,
    StringProperty,
)
from bpy_extras.io_utils import ExportHelper, ImportHelper

from .blender_backend import BlenderBackend
from .core import ApplyError, ConflictError, Draft, MAX_DOCUMENT_BYTES, Profile, Session, ValidationError, _reject_constant, _unique_object, archive_recovery, classify_recovery, execute_recovery, is_archived_recovery, load_catalog, load_profile, parse_recovery, plan_recovery, read_document, save_profile
from .preferences import verify_saved_preferences
from .palette import detail_categories, palette_groups, roundness_paths, viewport_background_paths
from .labels import field_label
from .contrast import analyze_contrast


ISSUE_PAGE_SIZE = 5
_registry = None
_session = None
_storage_override = None
_attributes = {}
_color_attributes = {}
_alpha_attributes = {}
_pending_colors = {}
_color_timer_session = None
_color_timer_registered = False
_color_pending_failed = False
_LIVE_UPDATE_SECONDS = 0.1
_registered_classes = []
_journal_path = ""
_message = ""
_severity = "INFO"
_issues = ()
_preview_values = None
_comparing = False
_completion = "Tema attuale"
_file_notice = ""
_save_pending = False
_failed_action = ""
_start_failed = False
_palette_map = ()
_viewport_group = None
_detail_map = ()
_palette_keys = ()
_palette_alpha_keys = ()
_roundness_paths = ()
_detail_items = ()
_detail_context_items = ()
_detail_context_labels = {}
_detail_context_cache = {}
_recovery_path = ""
_recovery_document = None
_recovery_plan = None
_recovery_decisions = {}
_recovery_error = ""
_recovery_detail = ""
_recovery_progress = ""
_recovery_blocked = False
_recovery_records = ()
_recovery_filenames = ()


_OWNER_NAMES = {
    "node_editor": "Nodi", "graph_editor": "Graph Editor", "outliner": "Outliner",
    "image_editor": "Image / UV Editor", "dopesheet_editor": "Dope Sheet / Timeline",
    "view_3d": "Vista 3D", "text_editor": "Editor di testo", "file_browser": "File Browser",
    "nla_editor": "Animazione non lineare", "sequence_editor": "Montaggio video", "properties": "Proprietà",
    "preferences": "Preferenze", "info": "Messaggi", "console": "Console", "clip_editor": "Tracciamento video",
    "topbar": "Barra superiore", "statusbar": "Barra di stato", "spreadsheet": "Foglio dati",
    "wcol_regular": "Controlli standard", "wcol_tool": "Strumenti", "wcol_text": "Campi di testo",
    "wcol_option": "Caselle di spunta", "wcol_toggle": "Interruttori", "wcol_num": "Campi numerici",
    "wcol_numslider": "Cursori numerici", "wcol_tab": "Schede", "wcol_box": "Riquadri",
    "wcol_toolbar_item": "Elementi toolbar", "wcol_radio": "Scelte esclusive", "wcol_curve": "Curve",
    "wcol_menu": "Menu", "wcol_pulldown": "Menu a tendina", "wcol_menu_back": "Fondi menu",
    "wcol_pie_menu": "Menu radiali", "wcol_tooltip": "Tooltip", "wcol_menu_item": "Voci menu",
    "wcol_scroll": "Barre di scorrimento", "wcol_progress": "Avanzamento", "wcol_list_item": "Elementi elenco",
    "panel_title": "Titoli dei pannelli", "widget": "Testi dei controlli", "tooltip": "Suggerimenti",
}

_LABELS = {
    "node_editor.space.back": "Sfondo nodi",
    "node_editor.space.header": "Barra superiore dell'editor nodi",
    "node_editor.node_backdrop": "Sfondo dell'immagine di compositing",
    "node_editor.grid": "Griglia · colore",
    "node_editor.grid_levels": "Griglia · livelli di punti",
    "node_editor.noodle_curving": "Linee · curvatura",
    "node_editor.wire": "Linee · colore esterno",
    "node_editor.wire_inner": "Linee · colore interno",
    "node_editor.wire_select": "Linee selezionate · colore",
    "node_editor.node_outline": "Nodi · contorno",
    "node_editor.node_selected": "Nodi · selezionati",
    "node_editor.node_active": "Nodi · attivo",
    "view_3d.space.gradients.background_type": "Sfondo tema · tipo",
    "view_3d.space.gradients.high_gradient": "Sfondo tema · superiore / uniforme",
    "view_3d.space.gradients.gradient": "Sfondo tema · inferiore",
    "view_3d.grid": "Griglia · colore",
    "view_3d.grid_major": "Griglia · linee principali",
    "view_3d.grid_axis_brightness": "Assi · luminosità",
    "view_3d.wire": "Oggetti · contorno",
    "view_3d.object_selected": "Oggetti · selezionati",
    "view_3d.object_active": "Oggetti · attivo",
    "view_3d.vertex_size": "Vertici · dimensione",
}

_FIELD_NAMES = {
    "back": "Sfondo", "header": "Barra superiore", "header_text": "Testo della barra superiore",
    "header_text_hi": "Testo evidenziato della barra superiore", "text": "Testo", "text_hi": "Testo evidenziato",
    "text_sel": "Testo selezionato", "outline": "Bordo", "outline_sel": "Bordo selezionato",
    "inner": "Fondo", "inner_sel": "Fondo selezionato", "item": "Simbolo",
}
def get_registry():
    if _registry is None:
        raise RuntimeError("Theme Studio non è registrato")
    return _registry


def get_session():
    return _session if _session is not None and _session.active else None


def last_issues():
    return _issues


def draft_attribute(path):
    return _attributes[path]


def draft_color_attribute(path):
    return _color_attributes.get(path)


def draft_alpha_attribute(path):
    return _alpha_attributes.get(path)


def _owner_label(path):
    parts = _short_path(path).split(".")
    key = parts[1] if parts[0] == "user_interface" and len(parts) > 2 else parts[0]
    indexed = {"bone_color_sets": "Ossa · gruppo", "collection_color": "Collezione", "strip_color": "Traccia · gruppo"}
    base, _, number = key.partition("[")
    if base in indexed and number:
        return f"{indexed[base]} {int(number.rstrip(']')) + 1}"
    return _OWNER_NAMES.get(key, key.replace("_", " ").title())


def _edit_notice(message):
    # A field edit must not make an unresolved warning/error disappear.
    if _severity == "INFO":
        _notice(message)
    else:
        _redraw()


def _apply_live_edit(message):
    """Apply the current draft through Session's journaled reversible transaction."""
    session = _require_session()
    warning = (_message, _severity, _issues) if _severity != "INFO" else None
    draft = session.draft
    snapshot = copy.deepcopy(draft)
    try:
        report = session.preview()
    except Exception:
        if not session.faulted:
            draft.__dict__.clear()
            draft.__dict__.update(snapshot.__dict__)
        raise
    _mark_live(session)
    if report.conflicts:
        _report("Modifica bloccata.", report)
        return report
    if warning:
        _notice(*warning)
    else:
        _edit_notice(f"{message} Tema aggiornato live; preferenze non salvate.")
    return report


def _stop_color_timer():
    global _color_timer_registered
    if _color_timer_registered and bpy.app.timers.is_registered(_color_timer):
        bpy.app.timers.unregister(_color_timer)
    _color_timer_registered = False


def _discard_colors():
    global _color_timer_session, _color_pending_failed
    _stop_color_timer()
    _pending_colors.clear()
    _color_timer_session = None
    _color_pending_failed = False


def _pending_color_value(key):
    intent = _pending_colors.get(key)
    return intent[-1] if intent else None


def _linked_rgba_paths(paths, draft):
    return tuple(path for path in paths if path not in draft.protected and len(draft.value(path)) == 4)


def _representative_alpha(paths, draft):
    linked = _linked_rgba_paths(paths, draft)
    candidates = linked or tuple(path for path in paths if len(draft.value(path)) == 4)
    return draft.value(candidates[0])[3] if candidates else 1.0


def _stage_palette_alpha(group, value, session):
    key = ("palette_alpha", group["id"])
    queued = _pending_colors.get(key)
    baseline = queued[2] if queued else _representative_alpha(group["paths"], session.draft)
    value = float(value)
    if abs(value - baseline) <= 1e-6:
        _pending_colors.pop(key, None)
    else:
        _stage_color(key, ("palette_alpha", group["paths"], baseline, value), session)


def _stage_color(key, intent, session=None):
    global _color_timer_session, _color_timer_registered, _color_pending_failed
    session = session or _require_session()
    if _pending_colors and _color_timer_session is not session:
        _discard_colors()
    _color_timer_session = session
    _pending_colors.pop(key, None)
    value = tuple(intent[-1]) if isinstance(intent[-1], (tuple, list)) else intent[-1]
    _pending_colors[key] = tuple(intent[:-1]) + (value,)
    _color_pending_failed = False
    if not _color_timer_registered:
        bpy.app.timers.register(_color_timer, first_interval=_LIVE_UPDATE_SECONDS)
        _color_timer_registered = True


def _flush_colors(session=None, *, timer_fired=False):
    global _color_timer_registered, _color_timer_session, _color_pending_failed
    if not _pending_colors:
        _stop_color_timer()
        _color_timer_session = None
        return True
    session = session or _color_timer_session
    if session is None or session is not get_session() or session is not _color_timer_session:
        _discard_colors()
        return False
    if not timer_fired:
        _stop_color_timer()
    draft = session.draft
    before = copy.deepcopy(draft)
    intents = tuple(_pending_colors.values())
    unsupported_alpha = []
    try:
        with draft.transaction():
            for intent in intents:
                if intent[0] == "palette":
                    _, key, paths, anchor, rgb = intent
                    draft.apply_palette(key, paths, anchor, rgb)
                elif intent[0] == "palette_alpha":
                    _, paths, _baseline, alpha = intent
                    unsupported_alpha.extend(path for path in paths if len(draft.value(path)) == 3)
                    linked = _linked_rgba_paths(paths, draft)
                    representative = linked[0] if linked else None
                    restore_baseline = (representative is not None and
                                        abs(draft._baseline[representative][3] - alpha) <= 1e-6)
                    for path in linked:
                        target = draft._baseline[path][3] if restore_baseline else alpha
                        if abs(draft.value(path)[3] - target) > 1e-6:
                            draft.set_alpha(path, target)
                            draft.protect(path, False)
                elif intent[0] == "roundness":
                    _, paths, value = intent
                    for path in paths:
                        if path not in draft.protected and value != draft.value(path):
                            draft.set(path, value)
                            draft.protect(path, False)
                elif intent[0] == "alpha":
                    _, path, alpha = intent
                    if abs(draft.value(path)[3] - alpha) > 1e-6:
                        draft.set_alpha(path, alpha)
                else:
                    _, path, value = intent
                    current = draft.value(path)
                    if isinstance(value, tuple) and len(value) == 3 and isinstance(current, (list, tuple)) and len(current) == 4:
                        if value != tuple(current[:3]):
                            draft.set(path, list(value) + current[3:])
                    elif isinstance(value, tuple) and isinstance(current, (list, tuple)):
                        if value != tuple(current):
                            draft.set(path, list(value))
                    elif path in _roundness_paths and isinstance(value, (int, float)):
                        if value != current:
                            draft.protect(path)
                        draft.set(path, value)
                    else:
                        draft.set(path, value)
        if before._snapshot() == draft._snapshot():
            _pending_colors.clear()
            _color_timer_session = None
            return True
        if unsupported_alpha:
            _notice("Alcuni colori del gruppo non supportano l'opacità; restano invariati.",
                    "WARNING", tuple(unsupported_alpha))
        report = _apply_live_edit("Modifica aggiornata.")
        if report is not None and report.conflicts:
            session.draft = before
            _color_pending_failed = True
            return False
    except Exception as exc:
        if not session.faulted:
            session.draft = before
        _color_pending_failed = True
        _error(exc)
        return False
    _pending_colors.clear()
    _color_timer_session = None
    _color_pending_failed = False
    return True


def _color_timer():
    global _color_timer_registered
    if not _pending_colors:
        _color_timer_registered = False
        return None
    if _color_pending_failed:
        _color_timer_registered = False
        return None
    session = _color_timer_session
    if session is not get_session():
        _color_timer_registered = False
        _discard_colors()
        return None
    _color_timer_registered = False
    _flush_colors(session, timer_fired=True)
    return None


def _mark_live(session):
    global _preview_values, _comparing
    _preview_values = {p: session.backend.read(p) for p in get_registry().editable_paths}
    _comparing = False


def _restore_draft(session):
    """Leave comparison by applying draft, never the comparison's initial values."""
    global _comparing, _preview_values
    if not _flush_colors(session):
        raise RuntimeError("Modifiche in attesa: risolvi il conflitto o scarta la sessione.")
    if not _comparing:
        return
    draft = session.draft
    live_values = _preview_values
    current = {p: session.backend.read(p) for p in get_registry().editable_paths}
    expected = {path: session.initial[path] for path in current}
    if any(current[path] != expected[path] for path in current):
        conflicts = tuple(path for path in current if current[path] != expected[path])
        raise ConflictError(conflicts)
    session.draft = copy.deepcopy(draft)
    try:
        report = session.preview()
    except Exception:
        if not session.faulted:
            session.draft = draft
        raise
    finally:
        session.draft = draft
    _comparing = False
    if live_values is not None:
        _preview_values = {p: session.backend.read(p) for p in get_registry().editable_paths}
    _report("Confronto chiuso; tema live ripristinato.", report)


def _color_property(path, spec, alpha=False):
    def get(_self):
        session = get_session()
        if session is None:
            return 100.0 if alpha else ((0.0, 0.0, 0.0, 1.0) if spec.length == 4 else (0.0, 0.0, 0.0))
        value = session.draft.value(path)
        if alpha:
            pending = _pending_color_value(("field_alpha", path))
            return float((value[3] if pending is None else pending) * 100)
        rgb = _pending_color_value(("field_rgb", path)) or tuple(value[:3])
        if len(value) == 4:
            opacity = _pending_color_value(("field_alpha", path))
            return tuple(rgb) + (value[3] if opacity is None else opacity,)
        return tuple(rgb)

    def set(_self, value):
        try:
            session = _require_session()
            if _comparing:
                _restore_draft(session)
                session = _require_session()
            if alpha:
                opacity = float(value) / 100
                current = session.draft.value(path)[3]
                if abs(opacity - current) > 1e-6:
                    _stage_color(("field_alpha", path), ("alpha", path, opacity), session)
                else:
                    _pending_colors.pop(("field_alpha", path), None)
            else:
                current = session.draft.value(path)
                rgb = tuple(value[:3])
                displayed_rgb = _pending_color_value(("field_rgb", path))
                if displayed_rgb is None:
                    displayed_rgb = tuple(current[:3])
                if rgb != tuple(displayed_rgb):
                    _stage_color(("field_rgb", path), ("field", path, rgb), session)
                if len(value) > 3 and len(current) == 4:
                    opacity = float(value[3])
                    if abs(opacity - current[3]) > 1e-6:
                        _stage_color(("field_alpha", path), ("alpha", path, opacity), session)
                    else:
                        _pending_colors.pop(("field_alpha", path), None)
        except Exception as exc:
            _error(exc)

    channel_description = ("Conserva il colore." if alpha else
                           "Colore e opacità nello stesso selettore." if spec.length == 4 else
                           "Questo colore non supporta opacità.")
    kwargs = dict(name="Opacità" if alpha else _label(path), get=get, set=set, options={"SKIP_SAVE"},
                  description=f"Modifica live; questo elemento non seguirà le modifiche comuni. {channel_description}")
    if alpha:
        return FloatProperty(min=0, max=100, subtype="PERCENTAGE", precision=1, **kwargs)
    return FloatVectorProperty(size=spec.length, subtype=spec.subtype, min=spec.minimum, max=spec.maximum, **kwargs)


def _short_path(path):
    return path.removeprefix("preferences.themes[0].").removeprefix("preferences.ui_styles[0].")


def _label(path):
    if path in _roundness_paths:
        return "Arrotondamento"
    return _LABELS.get(_short_path(path), _FIELD_NAMES.get(path.rsplit(".", 1)[-1], field_label(get_registry().fields[path].label)))


def _redraw():
    wm = bpy.context.window_manager
    if wm:
        for window in wm.windows:
            for area in window.screen.areas:
                area.tag_redraw()


def _notice(message, severity="INFO", issues=()):
    global _message, _severity, _issues
    _message, _severity, _issues = message, severity, tuple(issues)
    wm = bpy.context.window_manager
    if wm and hasattr(wm, "theme_studio_ui"):
        wm.theme_studio_ui.issue_page = 0
    _redraw()


def _error(exc):
    if isinstance(exc, ConflictError):
        issues = exc.paths
    elif isinstance(exc, ApplyError):
        issues = exc.rollback_errors
    else:
        issues = ()
    if isinstance(exc, ConflictError):
        message = "Modifiche esterne rilevate e conservate. Controlla gli elementi nei dettagli prima di proseguire."
    elif isinstance(exc, ApplyError):
        message = "Ripristino non completato. Riprova il ripristino." if get_session() and get_session().faulted else "Non è stato possibile applicare il tema. L'operazione è stata annullata."
    elif isinstance(exc, (RuntimeError, ValueError)) and not isinstance(exc, ValidationError):
        message = str(exc)
    else:
        message = "Non è stato possibile completare l'operazione. Consulta i dettagli dell'esito."
    _notice(message, "ERROR", (*issues, str(exc)))
    traceback.print_exc()


def _report(message, report, *, count=True):
    if report.conflicts:
        _notice(
            f"{message} {len(report.conflicts)} conflitti: modifiche esterne conservate; "
            "verifica i dettagli dell'esito prima di proseguire.",
            "WARNING", report.conflicts,
        )
        print("Theme Studio:", _message)
        for path in report.conflicts:
            print("  Conflitto:", path)
    else:
        _edit_notice(f"{message} {len(report.changed)} campi applicati." if count else message)


def _require_session(*, allow_faulted=False):
    session = get_session()
    if session is None:
        raise RuntimeError("Premi prima Inizia a modificare")
    if session.faulted and not allow_faulted:
        raise RuntimeError("Ripristino non completato: riprova il ripristino. Copia iniziale conservata nei dettagli.")
    return session


def _close_session(action):
    global _session, _completion, _preview_values, _comparing
    session = _require_session(allow_faulted=action == "cancel")
    if action == "cancel":
        _discard_colors()
    elif not _flush_colors(session):
        raise RuntimeError("Modifiche in attesa: risolvi il conflitto prima di terminare.")
    report = getattr(session, action)()
    # Never clear ownership on an exception or leave an active faulted session.
    if not session.active:
        _session = None
        _preview_values, _comparing = None, False
    _completion = "Tema attuale" if action == "cancel" else "Tema mantenuto"
    message = "Modifiche scartate." if action == "cancel" else ("Tema mantenuto. Preferenze non salvate da Theme Studio. "
              "Se il salvataggio automatico di Blender è attivo, il tema potrà essere salvato in seguito.")
    _report(message, report, count=action != "confirm")
    return report


def _cancel_for_lifecycle(reason):
    if get_session() is None:
        _discard_colors()
        return
    try:
        _close_session("cancel")
    except Exception as exc:
        _error(exc)
        print(f"Theme Studio: {reason}: annullamento FALLITO; sessione e controlli conservati. Journal: {_journal_path}")
        raise RuntimeError(f"Theme Studio: {reason}: {exc}; journal: {_journal_path}") from exc


@persistent
def _load_pre(_filename):
    # Blender may continue loading after a handler error. The persistent handler
    # and module reference keep the failed session reachable for another cancel.
    _cancel_for_lifecycle("cambio file")


def _detail_category_items(_self, _context):
    return _detail_items


def _context_buckets(paths, owner_label):
    buckets = {}
    for path in paths:
        buckets.setdefault(owner_label(path), []).append(path)
    return buckets


def _paths_in_context(paths, selected, owner_label):
    return tuple(path for path in paths if not selected or owner_label(path) == selected)


def _detail_paths(state):
    if state.palette_focus:
        if state.palette_focus == "viewport" and _viewport_group:
            return tuple(path for group in _viewport_group["groups"] for path in group["paths"]) + _viewport_group["details"]
        group = next((item for item in _palette_map if item["id"] == state.palette_focus), None)
        return group["paths"] if group else ()
    category = next((item for item in _detail_map if item["id"] == state.detail_category), None)
    return category["paths"] if category else ()


def _set_detail_contexts(state):
    global _detail_context_items, _detail_context_labels
    key = (state.palette_focus, state.detail_category if not state.palette_focus else "")
    if key not in _detail_context_cache:
        buckets = _context_buckets(_detail_paths(state), _owner_label)
        _detail_context_cache[key] = tuple((f"context_{index}", label, f"{len(paths)} controlli")
                                           for index, (label, paths) in enumerate(buckets.items()))
    _detail_context_items = _detail_context_cache[key]
    _detail_context_labels = {identifier: label for identifier, label, _description in _detail_context_items}
    state.detail_context = _detail_context_items[0][0] if _detail_context_items else ""


def _populate_detail_fields(state):
    state.detail_index = 0
    state.detail_fields.clear()
    if get_session() is None:
        return
    label = _detail_context_labels.get(state.detail_context)
    paths = _paths_in_context(_detail_paths(state), label, _owner_label)
    for path in paths:
        item = state.detail_fields.add()
        item.path, item.label = path, _label(path)


def _detail_changed(self, context):
    _set_detail_contexts(self)
    _populate_detail_fields(self)


def _detail_context_items_callback(_self, _context):
    return _detail_context_items


def _detail_context_changed(self, _context):
    _populate_detail_fields(self)


def _details_toggled(self, _context):
    if self.show_details:
        _set_detail_contexts(self)
        _populate_detail_fields(self)


def _palette_property(group):
    has_alpha = any(get_registry().fields[path].length == 4 for path in group["paths"])

    def get(_self):
        session = get_session()
        if session is None:
            return (0.0, 0.0, 0.0, 1.0) if has_alpha else (0.0, 0.0, 0.0)
        pending = _pending_color_value(("palette", group["id"]))
        rgb = pending if pending is not None else session.draft.palette_color(group["id"], group["anchor"])
        if not has_alpha:
            return rgb
        opacity = _pending_color_value(("palette_alpha", group["id"]))
        if opacity is None:
            opacity = _representative_alpha(group["paths"], session.draft)
        return tuple(rgb) + (opacity,)

    def set(_self, value):
        try:
            session = _require_session()
            if _comparing:
                _restore_draft(session)
                session = _require_session()
            rgb = tuple(value[:3])
            displayed_rgb = _pending_color_value(("palette", group["id"]))
            if displayed_rgb is None:
                displayed_rgb = session.draft.palette_color(group["id"], group["anchor"])
            if rgb != tuple(displayed_rgb):
                _stage_color(("palette", group["id"]),
                             ("palette", group["id"], group["paths"], group["anchor"], rgb), session)
            if has_alpha and len(value) > 3:
                _stage_palette_alpha(group, value[3], session)
        except Exception as exc:
            _error(exc)

    return FloatVectorProperty(name=_PALETTE_LABELS.get(group["id"], group["label"]),
                               description=_PALETTE_DESCRIPTIONS.get(group["id"], group.get("description", ""))
                               + (" L'opacità agisce solo sui colori collegati; tornando al riferimento ripristina le variazioni iniziali." if has_alpha else ""),
                               size=4 if has_alpha else 3, subtype="COLOR_GAMMA", min=0, max=1,
                               get=get, set=set, options={"SKIP_SAVE"})


def _palette_alpha_property(group):
    def get(_self):
        session = get_session()
        if session is None:
            return 100.0
        pending = _pending_color_value(("palette_alpha", group["id"]))
        if pending is not None:
            return pending * 100
        return _representative_alpha(group["paths"], session.draft) * 100

    def set(_self, value):
        try:
            session = _require_session()
            if _comparing:
                _restore_draft(session)
                session = _require_session()
            _stage_palette_alpha(group, float(value) / 100, session)
        except Exception as exc:
            _error(exc)

    return FloatProperty(name="Opacità comune", min=0, max=100, subtype="PERCENTAGE", precision=1,
                         description="Applica ai colori collegati che supportano l'opacità.",
                         get=get, set=set, options={"SKIP_SAVE"})


def _roundness_property(paths):
    def get(_self):
        session = get_session()
        if session is None or not paths:
            return 0.5
        pending = _pending_color_value(("roundness",))
        if pending is not None:
            return pending
        path = next((path for path in paths if path not in session.draft.protected), paths[0])
        return session.draft.value(path)

    def set(_self, value):
        try:
            session = _require_session()
            if _comparing:
                _restore_draft(session)
                session = _require_session()
            _stage_color(("roundness",), ("roundness", paths, float(value)), session)
        except Exception as exc:
            _error(exc)

    return FloatProperty(name="Arrotondamento condiviso", min=0, max=1, subtype="FACTOR", precision=2,
                         description=f"Regola {len(paths)} forme wcol. Separa singoli elementi in Dettagli.",
                         get=get, set=set, options={"SKIP_SAVE"})


_PALETTE_LABELS = {"backgrounds": "Sfondi", "surfaces": "Superfici", "text": "Testi",
                   "accents": "Accenti", "selection": "Selezione", "borders": "Bordi"}
_PALETTE_DESCRIPTIONS = {
    "backgrounds": "Tonalità correlate per gli sfondi. Effetto visivo non verificato.",
    "surfaces": "Tonalità correlate per pannelli e controlli. Effetto visivo non verificato.",
    "text": "Tonalità correlate per i testi, mantenendo differenze tra stati. Effetto visivo non verificato.",
    "accents": "Tonalità correlate per gli accenti dell'interfaccia. Effetto visivo non verificato.",
    "selection": "Tonalità correlate per gli elementi selezionati. Effetto visivo non verificato.",
    "borders": "Tonalità correlate per bordi e contorni. Effetto visivo non verificato.",
}
_DETAIL_LABELS = {"surfaces": "Superfici", "text": "Testi", "states": "Stati",
                  "borders": "Bordi", "symbols": "Simboli", "guides": "Guide e griglie",
                  "geometry": "Forme", "connections": "Collegamenti", "typography": "Caratteri"}
_DETAIL_GROUP_LABELS = {
    "canvas": "Sfondi", "panels": "Pannelli", "controls": "Controlli", "editor": "Editor",
    "headers": "Barre superiori", "viewport_grid": "Griglie Vista 3D", "node_grid": "Griglia nodi",
    "node_wires": "Collegamenti nodi", "curve_handles": "Maniglie curve", "curve_vertices": "Punti curva",
    "mesh_markers": "Indicatori mesh", "mesh_topology": "Topologia mesh", "axes": "Assi",
    "gizmos": "Gizmo", "viewport_overlays": "Sovrapposizioni Vista 3D", "object_selection": "Selezione oggetti",
    "mesh_selection": "Selezione mesh", "node_selection": "Selezione nodi", "outliner_selection": "Selezione Outliner",
    "sequence_selection": "Selezione sequenza", "control_indicators": "Indicatori controlli",
    "animation_time": "Tempo animazione", "keyframes": "Fotogrammi chiave",
}


def _draft_property(path, spec):
    """RNA here is only a typed input facade for the independent Draft."""
    fallback = False if spec.kind == "BOOLEAN" else "" if spec.kind == "STRING" else 0
    if spec.kind in {"FLOAT", "INT"}:
        fallback = max(spec.minimum if spec.minimum is not None else 0, 0)
        if spec.maximum is not None:
            fallback = min(fallback, spec.maximum)
        fallback = float(fallback) if spec.kind == "FLOAT" else int(fallback)
    if spec.kind == "ENUM":
        fallback = spec.choices[0]
    if spec.length:
        fallback = [fallback] * spec.length

    is_color = spec.kind == "FLOAT" and spec.length == 3 and spec.subtype in {"COLOR", "COLOR_GAMMA"}

    def get(_self):
        session = get_session()
        pending_key = ("field_rgb", path) if is_color else ("field", path)
        pending = _pending_color_value(pending_key) if session is not None else None
        if pending is not None:
            if spec.kind == "ENUM":
                return spec.choices.index(pending)
            return pending
        value = session.draft.value(path) if session is not None else fallback
        if spec.kind == "ENUM":
            return spec.choices.index(value)
        if spec.length:
            return tuple(value)
        return float(value) if spec.kind == "FLOAT" else value

    def set(_self, value):
        try:
            session = _require_session()
            if is_color:
                if _comparing:
                    _restore_draft(session)
                    session = _require_session()
                _stage_color(("field_rgb", path), ("field", path, tuple(value)), session)
                return
            if spec.kind == "ENUM":
                value = spec.choices[value]
            elif spec.length:
                value = list(value)
            if _comparing:
                _restore_draft(session)
                session = _require_session()
            _stage_color(("field", path), ("field", path, value), session)
        except Exception as exc:
            # RNA callbacks cannot return an operator report; retain a visible
            # error and print the traceback instead of silently dropping it.
            _error(exc)

    kwargs = dict(name=_label(path), description="Modifica il tema live. Questo elemento non seguirà le prossime modifiche comuni.",
                  get=get, set=set, options={"SKIP_SAVE"})
    if spec.kind == "ENUM":
        enum_names = {"SINGLE_COLOR": "Colore uniforme", "LINEAR": "Sfumatura lineare", "RADIAL": "Sfumatura radiale"} if _short_path(path) == "view_3d.space.gradients.background_type" else {}
        kwargs["items"] = [(name, enum_names.get(name, name.replace("_", " ").title()), name, index)
                           for index, name in enumerate(spec.choices)]
        return EnumProperty(**kwargs)
    if spec.kind == "STRING":
        return StringProperty(**kwargs)
    if spec.kind in {"FLOAT", "INT"}:
        if spec.minimum is not None:
            kwargs["min"] = float(spec.minimum) if spec.kind == "FLOAT" else int(spec.minimum)
        if spec.maximum is not None:
            kwargs["max"] = float(spec.maximum) if spec.kind == "FLOAT" else int(spec.maximum)
        if spec.kind == "FLOAT":
            kwargs["precision"] = 3
    if spec.length:
        kwargs["size"] = spec.length
        # Preserve Blender's distinction between linear and gamma color inputs.
        if spec.kind == "FLOAT" and spec.subtype in {"COLOR", "COLOR_GAMMA"}:
            kwargs["subtype"] = spec.subtype
        factory = {"FLOAT": FloatVectorProperty, "INT": IntVectorProperty, "BOOLEAN": BoolVectorProperty}[spec.kind]
    else:
        factory = {"FLOAT": FloatProperty, "INT": IntProperty, "BOOLEAN": BoolProperty}[spec.kind]
    return factory(**kwargs)


def _dirty(session):
    return any(value != session.initial[path] for path, value in session.draft.values.items()) or bool(session.draft.protected)


def _theme_changed(session):
    # Inclusion/protection alone does not change Blender's appearance and must
    # never open a path to saving all Blender preferences.
    return any(value != session.initial[path] for path, value in session.draft.values.items())


def _has_pending_edits(session):
    return bool(_pending_colors) and _color_timer_session is session


def _has_pending_colors(session):
    return _has_pending_edits(session)


def _theme_changed_or_pending(session):
    return _theme_changed(session) or _has_pending_edits(session)


def session_status():
    session = get_session()
    if session is None:
        return _completion
    if session.faulted:
        return "Ripristino non completato"
    if _comparing:
        return "Confronto: tema iniziale"
    if _has_pending_edits(session):
        return "Tema live non salvato · modifiche in attesa" if _theme_changed(session) else "Modifiche in attesa"
    return "Tema live non salvato" if _theme_changed(session) else "Nessuna modifica"


def _visible_theme(session):
    reference = session.initial if _comparing else _preview_values
    if reference is None:
        reference = session.initial
    if any(session.backend.read(path) != reference[path] for path in get_registry().editable_paths):
        return "modifiche esterne rilevate; il tema visibile può differire"
    return "tema iniziale" if _comparing else "tema live"


def _get_included(self):
    session = get_session()
    return session is not None and self.path in get_registry().editable_paths and self.path not in session.draft.protected


def _set_included(self, value):
    try:
        session = _require_session()
        _restore_draft(session)
        old_draft = copy.deepcopy(session.draft)
        session.draft.protect(self.path, not value)
        _edit_notice("Campo reincluso senza cambiarne il valore." if value else "Campo mantenuto a parte dalle regolazioni comuni.")
    except Exception as exc:
        if "old_draft" in locals():
            session.draft.__dict__.clear()
            session.draft.__dict__.update(old_draft.__dict__)
        _error(exc)


class THEME_STUDIO_PG_target(bpy.types.PropertyGroup):
    path: StringProperty(options={"SKIP_SAVE"})
    label: StringProperty(options={"SKIP_SAVE"})
    included: BoolProperty(name="Segue le modifiche comuni", description="Se attivo segue le regolazioni comuni. Riattivarlo non cambia il valore attuale",
                           get=_get_included, set=_set_included, options={"SKIP_SAVE"})


class THEME_STUDIO_PG_state(bpy.types.PropertyGroup):
    workspace_page: EnumProperty(name="Vista", items=(
        ("theme", "Tema", "Regola i colori principali", "COLOR", 0),
        ("viewport", "Vista 3D", "Colori tema della Vista 3D", "VIEW3D", 1),
        ("details", "Dettagli", "Controlli avanzati e impostazioni numeriche", "PREFERENCES", 2),
    ), default="theme", options={"SKIP_SAVE"})
    show_details: BoolProperty(name="Altri controlli", options={"SKIP_SAVE"}, update=_details_toggled)
    detail_category: EnumProperty(name="Categoria", items=_detail_category_items, options={"SKIP_SAVE"}, update=_detail_changed)
    detail_context: EnumProperty(name="Contesto", items=_detail_context_items_callback, options={"SKIP_SAVE"}, update=_detail_context_changed)
    detail_fields: CollectionProperty(type=THEME_STUDIO_PG_target, options={"SKIP_SAVE"})
    detail_index: IntProperty(min=0, options={"SKIP_SAVE"})
    palette_focus: StringProperty(options={"SKIP_SAVE"})
    issue_page: IntProperty(default=0, min=0, options={"SKIP_SAVE"})
    contrast_page: IntProperty(default=0, min=0, options={"SKIP_SAVE"})
    profile_name: StringProperty(name="Nome del tema", default="Il mio tema", maxlen=80, options={"SKIP_SAVE"})
    show_issue_details: BoolProperty(name="Dettagli dell'esito", options={"SKIP_SAVE"})
    contrast_details: BoolProperty(name="Dettagli contrasto", options={"SKIP_SAVE"})
    show_safety_details: BoolProperty(name="Dettagli sulla modifica", options={"SKIP_SAVE"})
    show_recovery_details: BoolProperty(name="Dettagli tecnici", options={"SKIP_SAVE"})


class _SessionAction:
    @classmethod
    def poll(cls, _context):
        session = get_session()
        return session is not None and not session.faulted

    def execute(self, context):
        global _failed_action
        try:
            if getattr(self, "_discard_pending_colors", False):
                _discard_colors()
            elif not _flush_colors():
                raise RuntimeError("Modifiche in attesa: risolvi il conflitto prima di continuare.")
            self.run(context)
            if _failed_action == self.bl_idname and _severity == "ERROR":
                _failed_action = ""
                _notice("Operazione completata.")
            return {"FINISHED"}
        except Exception as exc:
            _failed_action = self.bl_idname
            _error(exc)
            self.report({"ERROR"}, _message)
            return {"CANCELLED"}


class THEME_STUDIO_OT_start(_SessionAction, bpy.types.Operator):
    bl_idname = "theme_studio.start"
    bl_label = "Inizia a modificare"
    bl_description = "Avvia una sessione reversibile; il tema non cambia finché non modifichi un campo"

    def execute(self, context):
        global _start_failed
        try:
            self.run(context)
            _start_failed = False
            return {"FINISHED"}
        except Exception as exc:
            _start_failed = True
            _notice("Non è stato possibile creare la copia iniziale. Il tema non è stato modificato.", "ERROR", (str(exc),))
            traceback.print_exc()
            self.report({"ERROR"}, _message)
            return {"CANCELLED"}

    @classmethod
    def poll(cls, _context):
        return _registry is not None and get_session() is None and not _recovery_path

    def run(self, context):
        global _session, _journal_path, _preview_values, _comparing, _completion, _file_notice, _save_pending
        registry = get_registry()
        backend = BlenderBackend(registry)
        if _storage_override is not None:
            directory = _storage_override
            directory.mkdir(parents=True, exist_ok=True)
        else:
            directory_name = bpy.utils.user_resource("CONFIG", path="theme-studio", create=True)
            if not directory_name:
                raise OSError("Storage utente non disponibile; nessuna sessione iniziata")
            directory = Path(directory_name)
        journal = directory / f"recovery-{uuid.uuid4().hex}.json"
        session = Session(registry, backend, journal)
        _session = session
        _preview_values, _comparing = {p: copy.deepcopy(v) for p, v in _session.initial.items()
                                      if p in registry.editable_paths}, False
        _completion, _file_notice, _save_pending = "Tema attuale", "", False
        _journal_path = str(journal)
        state = context.window_manager.theme_studio_ui
        state.show_details = False
        state.palette_focus = ""
        state.workspace_page = "theme"
        if _detail_items:
            state.detail_category = _detail_items[0][0]
        _detail_changed(state, context)
        _notice("")  # The persistent state already says that nothing has changed.


class THEME_STUDIO_OT_preview(_SessionAction, bpy.types.Operator):
    bl_idname = "theme_studio.preview"
    bl_label = "Applica le modifiche"
    bl_description = "Applica la copia al tema globale di Blender in modo reversibile"

    @classmethod
    def poll(cls, _context):
        session = get_session()
        return session is not None and not session.faulted and _comparing

    def run(self, _context):
        session = _require_session()
        if not _comparing:
            raise RuntimeError("Nessun confronto da chiudere.")
        _restore_draft(session)


class THEME_STUDIO_OT_previous(_SessionAction, bpy.types.Operator):
    bl_idname = "theme_studio.previous"
    bl_label = "Confronta con l'inizio"
    bl_description = "Mostra il tema iniziale senza perdere le modifiche live"

    def run(self, _context):
        global _comparing, _preview_values
        session = _require_session()
        if not _theme_changed(session):
            raise RuntimeError("Nessuna modifica live da confrontare.")
        if _preview_values is None:
            _mark_live(session)
        expected = ({p: session.initial[p] for p in get_registry().editable_paths}
                    if _comparing else _preview_values)
        current = {p: session.backend.read(p) for p in get_registry().editable_paths}
        conflicts = tuple(path for path in current if current[path] != expected[path])
        if conflicts:
            raise ConflictError(conflicts)
        if _comparing:
            _restore_draft(session)
            return
        draft = session.draft
        live_values = _preview_values
        reference = {p: session.initial[p] for p in get_registry().editable_paths}
        original_draft = session.draft
        session.draft = Draft(get_registry(), reference)
        try:
            report = session.preview()
        finally:
            session.draft = original_draft
        if report.conflicts:
            _report("Confronto bloccato.", report)
            return
        _comparing = True
        if live_values is not None:
            _preview_values = live_values
        _report("Confronto: tema iniziale. Modifiche live non salvate.", report)


class THEME_STUDIO_OT_cancel(_SessionAction, bpy.types.Operator):
    bl_idname = "theme_studio.cancel"
    bl_label = "Scarta modifiche…"
    bl_description = "Torna al tema iniziale, conserva le modifiche esterne e chiude il lavoro; riprova anche dopo errori"
    _discard_pending_colors = True

    @classmethod
    def poll(cls, _context):
        return get_session() is not None

    def invoke(self, context, _event):
        return context.window_manager.invoke_props_dialog(self, width=440)

    def draw(self, _context):
        _wrapped(self.layout, "Ripristina lo stato iniziale dei campi ancora posseduti. "
                  "Le modifiche esterne vengono conservate e segnalate. Il lavoro viene chiuso: salva prima una copia del tema per conservarlo.", width=440)

    def run(self, _context):
        _close_session("cancel")


class THEME_STUDIO_OT_confirm(_SessionAction, bpy.types.Operator):
    bl_idname = "theme_studio.confirm"
    bl_label = "Usa senza salvare ora"
    bl_description = "Mantiene il tema live e chiude il lavoro; non salva le preferenze"

    def invoke(self, context, _event):
        return context.window_manager.invoke_props_dialog(self, width=460)

    def draw(self, _context):
        _wrapped(self.layout, "Il tema resta attivo. Se il salvataggio automatico di Blender è attivo, potrà essere salvato in seguito.", width=460)

    def run(self, _context):
        session = _require_session()
        if _comparing:
            raise RuntimeError("Esci dal confronto prima di terminare.")
        _close_session("confirm")


class THEME_STUDIO_OT_finish(_SessionAction, bpy.types.Operator):
    bl_idname = "theme_studio.finish"
    bl_label = "Termina…"

    def invoke(self, context, _event):
        return context.window_manager.invoke_props_dialog(self, width=480, confirm_text="Continua a modificare")

    def draw(self, _context):
        layout = self.layout
        layout.operator_context = "EXEC_DEFAULT"
        session = get_session()
        if session is None:
            layout.label(text=session_status(), icon="CHECKMARK")
            _wrapped(layout, "Il lavoro di modifica è chiuso. Puoi chiudere questo dialogo.", width=480)
            return
        if not _theme_changed_or_pending(session) and not _comparing:
            layout.label(text="Nessuna modifica da mantenere.", icon="INFO")
            _wrapped(layout, "Puoi tornare ai colori o chiudere il lavoro senza salvare le preferenze.", width=480)
            layout.operator("theme_studio.cancel", text="Chiudi senza modifiche", icon="X")
            return
        if _comparing:
            _wrapped(layout, "Confronto attivo: torna alle modifiche live prima di terminare.", width=480)
            layout.operator("theme_studio.previous", text="Torna alle modifiche live", icon="LOOP_BACK")
            return
        layout.label(text="Mantieni questo tema?", icon="QUESTION")
        _wrapped(layout, "Il tema live resterà attivo. Le preferenze non vengono salvate.", width=480)
        _wrapped(layout, "Salvare le preferenze scrive tutte le preferenze di Blender.", width=480)
        op = layout.operator("theme_studio.save_preferences", text="Salva tutte le preferenze…", icon="FILE_TICK")
        op.consent = True
        layout.separator()
        layout.operator("theme_studio.confirm", text="Usa senza salvare ora")
        _wrapped(layout, "Il tema resta attivo. Se il salvataggio automatico di Blender è attivo, potrà essere salvato in seguito.", width=480)

    def run(self, _context):
        pass  # Dialog confirmation is deliberately the non-destructive exit.


def _save_preferences_verified():
    # Verify Blender's result and the actual preferences file, not a static notice.
    path = Path(bpy.utils.user_resource("CONFIG")) / "userpref.blend"
    result = bpy.ops.wm.save_userpref()
    verify_saved_preferences(result, path)


class THEME_STUDIO_OT_save_preferences(bpy.types.Operator):
    bl_idname = "theme_studio.save_preferences"
    bl_label = "Riprova il salvataggio"
    consent: BoolProperty(default=False, options={"SKIP_SAVE"})

    @classmethod
    def poll(cls, _context):
        session = get_session()
        if session is None:
            return _save_pending
        return not session.faulted and _theme_changed_or_pending(session) and not _comparing

    def invoke(self, context, _event):
        self.consent = True
        return context.window_manager.invoke_props_dialog(self, width=460, confirm_text="Salva tutte le preferenze")

    def draw(self, _context):
        _wrapped(self.layout, "Blender salverà tutte le preferenze attuali, non soltanto il tema.", width=460)

    def execute(self, _context):
        global _save_pending, _completion
        try:
            if _recovery_blocked or _recovery_path:
                raise RuntimeError("Ripara manualmente il journal prima di riprovare.")
            if not self.consent:
                raise RuntimeError("È necessario il consenso al salvataggio di tutte le preferenze.")
            if get_session() is not None:
                if not _flush_colors():
                    raise RuntimeError("Modifiche in attesa: risolvi il conflitto prima di salvare.")
                if not _theme_changed(_require_session()):
                    raise RuntimeError("Nessuna modifica al tema da salvare.")
                THEME_STUDIO_OT_confirm.run(self, _context)
            elif not _save_pending:
                raise RuntimeError("Nessun salvataggio da riprovare.")
            _save_pending = True
            _save_preferences_verified()
            _save_pending = False
            _completion = "Preferenze salvate"
            _notice("Preferenze salvate. Il salvataggio riguarda tutte le preferenze di Blender.")
            return {"FINISHED"}
        except Exception as exc:
            _error(exc)
            self.report({"ERROR"}, _message)
            return {"CANCELLED"}


class THEME_STUDIO_OT_undo(_SessionAction, bpy.types.Operator):
    bl_idname = "theme_studio.undo"
    bl_label = "Annulla modifica"
    bl_description = "Annulla l'ultima modifica live in modo reversibile"

    def run(self, context):
        session = _require_session()
        _restore_draft(session)
        old_draft = copy.deepcopy(session.draft)
        changed = session.draft.undo()
        if changed:
            try:
                _apply_live_edit("Modifica annullata.")
            except Exception:
                session.draft = old_draft
                raise
        if not changed:
            _edit_notice("Nessuna modifica da annullare.")


class THEME_STUDIO_OT_redo(_SessionAction, bpy.types.Operator):
    bl_idname = "theme_studio.redo"
    bl_label = "Ripeti modifica"

    def run(self, context):
        session = _require_session()
        _restore_draft(session)
        old_draft = copy.deepcopy(session.draft)
        changed = session.draft.redo()
        if changed:
            try:
                _apply_live_edit("Modifica ripetuta.")
            except Exception:
                session.draft.__dict__.clear()
                session.draft.__dict__.update(old_draft.__dict__)
                raise
        if not changed:
            _edit_notice("Nessuna modifica da ripetere.")


class THEME_STUDIO_OT_common_value(_SessionAction, bpy.types.Operator):
    bl_idname = "theme_studio.common_value"
    bl_label = "Modifica colore…"
    bl_description = "Modifica un solo campo live in modo reversibile"
    path: StringProperty(options={"SKIP_SAVE"})
    opacity: BoolProperty(options={"SKIP_SAVE"})
    color: FloatVectorProperty(name="Colore", size=3, subtype="COLOR_GAMMA", min=0, max=1, default=(0.5, 0.5, 0.5))
    linear_color: FloatVectorProperty(name="Colore", size=3, subtype="COLOR", min=0, max=1)
    alpha: FloatProperty(name="Opacità", min=0, max=100, default=100, subtype="PERCENTAGE")

    def invoke(self, context, _event):
        value = _require_session().draft.value(self.path)
        self.color, self.linear_color = value[:3], value[:3]
        self.alpha = value[3] * 100 if len(value) == 4 else 100
        return context.window_manager.invoke_props_dialog(self, width=460,
            confirm_text="Usa questa opacità" if self.opacity else "Usa questo colore")

    def draw(self, _context):
        layout = self.layout
        _wrapped(layout, f"{_label(self.path)} · {_owner_label(self.path)}", width=460)
        _wrapped(layout, "Modifica separatamente: il campo non seguirà le modifiche dei gruppi.", width=460)
        _wrapped(layout, "Valore live iniziale: l'opacità attuale." if self.opacity else
                 "Valore live iniziale: il colore attuale.", width=460)
        attr = "alpha" if self.opacity else "linear_color" if self.path and get_registry().fields[self.path].subtype == "COLOR" else "color"
        if not self.opacity:
            layout.template_color_picker(self, attr, value_slider=True)
        layout.prop(self, attr)
        _wrapped(layout, "RGB resta invariato." if self.opacity else "L'opacità di ogni elemento resta invariata.", width=460)
        _wrapped(layout, "Annulla o Esc chiude senza modificare il tema.", width=460)

    def run(self, _context):
        session = _require_session()
        _restore_draft(session)
        draft = session.draft
        old_values, old_protected = draft.values, draft.protected
        old_draft = copy.deepcopy(draft)
        with draft.transaction():
            if self.opacity:
                draft.set_alpha(self.path, self.alpha / 100)
            else:
                value = self.linear_color if get_registry().fields[self.path].subtype == "COLOR" else self.color
                draft.set(self.path, list(value) + draft.value(self.path)[3:])
        if draft.values == old_values and draft.protected == old_protected:
            return
        try:
            _apply_live_edit("Colore aggiornato · 1 elemento. Modifica separatamente.")
        except Exception:
            session.draft = old_draft
            raise


class THEME_STUDIO_OT_protect_field(_SessionAction, bpy.types.Operator):
    bl_idname = "theme_studio.protect_field"
    bl_label = "Modifica separatamente / includi"
    bl_description = "Un campo a parte non segue i gruppi. Riunirlo non cambia subito il valore"
    path: StringProperty(options={"SKIP_SAVE"})
    enabled: BoolProperty(options={"SKIP_SAVE"})

    def run(self, _context):
        _require_session().draft.protect(self.path, self.enabled)
        _edit_notice("Modifica separatamente: non seguirà le prossime modifiche comuni." if self.enabled else "Incluso nelle prossime modifiche comuni. Il valore attuale non cambia.")


class THEME_STUDIO_OT_reset_field(_SessionAction, bpy.types.Operator):
    bl_idname = "theme_studio.reset_field"
    bl_label = "Ripristina il valore iniziale"
    bl_description = "Ripristina il valore di inizio sessione live e lo protegge dai gruppi"
    path: StringProperty(options={"SKIP_SAVE"})

    def run(self, _context):
        session = _require_session()
        _restore_draft(session)
        old_draft = copy.deepcopy(session.draft)
        session.draft.set(self.path, session.initial[self.path])
        try:
            _apply_live_edit("Valore iniziale ripristinato. Modifica separatamente.")
        except Exception:
            session.draft.__dict__.clear()
            session.draft.__dict__.update(old_draft.__dict__)
            raise


class THEME_STUDIO_OT_page(bpy.types.Operator):
    bl_idname = "theme_studio.page"
    bl_label = "Cambia pagina"
    target: IntProperty(min=0, options={"SKIP_SAVE"})
    issues: BoolProperty(options={"SKIP_SAVE"})
    contrast: BoolProperty(options={"SKIP_SAVE"})

    def execute(self, context):
        state = context.window_manager.theme_studio_ui
        setattr(state, "contrast_page" if self.contrast else "issue_page" if self.issues else "page", self.target)
        _redraw()
        return {"FINISHED"}


class THEME_STUDIO_OT_copy_report(bpy.types.Operator):
    bl_idname = "theme_studio.copy_report"
    bl_label = "Copia i dettagli dell'esito"
    bl_description = "Copia il messaggio completo e tutti i conflitti/errori negli appunti"

    @classmethod
    def description(cls, _context, _properties):
        return "\n".join(filter(None, (_message, f"Journal: {_journal_path}" if _journal_path else "",
                                       cls.bl_description)))

    def execute(self, context):
        context.window_manager.clipboard = "\n".join((_message, f"Journal: {_journal_path}", *_issues))
        self.report({"INFO"}, "Esito copiato")
        return {"FINISHED"}


class THEME_STUDIO_OT_save_profile(_SessionAction, bpy.types.Operator, ExportHelper):
    bl_idname = "theme_studio.save_profile"
    bl_label = "Salva una copia del tema…"
    bl_description = "Salva il tema live e gli elementi separati in un file .json, senza salvare le preferenze"
    filename_ext = ".json"
    filter_glob: StringProperty(default="*.json", options={"HIDDEN"})
    profile_name: StringProperty(name="Nome del tema", default="Il mio tema", maxlen=80)
    overwrite: BoolProperty(name="Consenti sostituzione del file", default=False,
                            description="Consenso esplicito: per default un file esistente non viene sostituito")

    @classmethod
    def poll(cls, _context):
        return get_session() is not None  # Export a draft even if rollback failed.

    def invoke(self, context, _event):
        self.profile_name = context.window_manager.theme_studio_ui.profile_name
        self.overwrite = False
        if not self.filepath:
            self.filepath = bpy.path.clean_name(self.profile_name) + self.filename_ext
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def draw(self, _context):
        self.layout.prop(self, "profile_name")
        self.layout.prop(self, "overwrite")
        _wrapped(self.layout, "Salva il tema live in un file .json, senza salvare le preferenze di Blender.")

    def run(self, context):
        global _file_notice
        session = _require_session(allow_faulted=True)
        if not self.filepath:
            raise ValueError("Scegli un file JSON")
        path = Path(bpy.path.ensure_ext(self.filepath, self.filename_ext))
        if path.resolve() == session.recovery_path.resolve() or (path.exists() and path.samefile(session.recovery_path)):
            raise ValueError("Questo file è riservato al recupero della copia iniziale: scegli un altro file per il tema.")
        try:
            save_profile(path, session.draft.profile(self.profile_name), get_registry(), overwrite=self.overwrite)
        except FileExistsError as exc:
            raise ValueError("File già esistente: scegli un nuovo nome o consenti esplicitamente la sostituzione nel file browser") from exc
        context.window_manager.theme_studio_ui.profile_name = self.profile_name
        _file_notice = "Copia del tema salvata in un file"
        _edit_notice("Copia del tema salvata in un file. Tema attivo e preferenze non sono cambiati.")


class THEME_STUDIO_OT_load_profile(_SessionAction, bpy.types.Operator, ImportHelper):
    bl_idname = "theme_studio.load_profile"
    bl_label = "Apri un tema salvato…"
    bl_description = "Verifica il file .json e applica il tema in modo reversibile"
    filter_glob: StringProperty(default="*.json", options={"HIDDEN"})
    replace_draft: BoolProperty(name="Sostituisci le modifiche della copia", default=False)

    @classmethod
    def poll(cls, _context):
        return _registry is not None and not _recovery_path and (get_session() is None or not get_session().faulted)

    def invoke(self, context, _event):
        self.replace_draft = False
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def draw(self, _context):
        self.layout.prop(self, "replace_draft")
        _wrapped(self.layout, "Apre il file .json e aggiorna il tema live in modo reversibile. Preferenze non salvate.")

    def run(self, context):
        global _preview_values
        # Validate before starting a session or touching an existing draft.
        profile = load_profile(self.filepath, get_registry())
        if get_session() is None:
            THEME_STUDIO_OT_start.run(self, context)
        session = _require_session()
        if _dirty(session) and not self.replace_draft:
            raise ValueError("La copia contiene modifiche: salvala prima oppure consenti la sostituzione nel file browser.")
        _restore_draft(session)
        old_draft = copy.deepcopy(session.draft)
        old_preview_values = _preview_values
        session.draft.replace_profile(profile)
        try:
            _apply_live_edit("Tema caricato.")
        except Exception:
            session.draft.__dict__.clear()
            session.draft.__dict__.update(old_draft.__dict__)
            _preview_values = old_preview_values
            raise
        state = context.window_manager.theme_studio_ui
        state.profile_name = profile.name
        _detail_changed(state, context)
        _edit_notice(f"Tema «{profile.name}» attivo in Blender. Preferenze non salvate.")


def _wrap_lines(text, width, measure):
    lines = []
    for paragraph in text.splitlines() or [""]:
        words = paragraph.split()
        line = ""
        for word in words:
            candidate = f"{line} {word}" if line else word
            if measure(candidate)[0] <= width:
                line = candidate
                continue
            if line:
                lines.append(line)
                line = ""
            while measure(word)[0] > width:
                part = word
                while len(part) > 1 and measure(part)[0] > width:
                    part = part[:-1]
                lines.append(part)
                word = word[len(part):]
            line = word
        lines.append(line)
    return lines


def _wrapped(layout, text, width=None):
    scale = max(0.5, bpy.context.preferences.system.ui_scale)
    if width is None:
        region = getattr(bpy.context, "region", None)
        width = region.width if region is not None and region.width else 360 * scale
        width -= 16 * scale
    else:
        width = width * scale - 32 * scale
    for line in _wrap_lines(text, max(20 * scale, width), lambda value: blf.dimensions(0, value)):
        layout.label(text=line)


def _pager(layout, page, pages, *, issues=False, contrast=False):
    row = layout.row(align=True)
    previous = row.row(align=True)
    previous.enabled = page > 0
    op = previous.operator("theme_studio.page", text="", icon="TRIA_LEFT")
    op.target, op.issues, op.contrast = max(0, page - 1), issues, contrast
    row.label(text=f"{page + 1} / {pages}")
    following = row.row(align=True)
    following.enabled = page + 1 < pages
    op = following.operator("theme_studio.page", text="", icon="TRIA_RIGHT")
    op.target, op.issues, op.contrast = page + 1, issues, contrast


def _draw_status(layout, state):
    if not _message:
        return
    if _severity == "INFO" and not _issues:
        _wrapped(layout, _message)
        return
    box = layout.box()
    box.alert = _severity == "ERROR"
    box.label(text={"ERROR": "Operazione non completata", "WARNING": "Attenzione", "INFO": "Esito"}[_severity],
              icon={"ERROR": "ERROR", "WARNING": "ERROR", "INFO": "INFO"}[_severity])
    # Path lists belong in the paged detail, not in a giant ConflictError label.
    message = _message.split(": ", 1)[0] if _issues and len(_message) > 300 else _message
    _wrapped(box, message)
    if _issues:
        box.prop(state, "show_issue_details", icon="TRIA_DOWN" if state.show_issue_details else "TRIA_RIGHT", emboss=False)
    if _issues and state.show_issue_details:
        pages = max(1, math.ceil(len(_issues) / ISSUE_PAGE_SIZE))
        page = min(state.issue_page, pages - 1)
        box.label(text=f"Dettagli: {len(_issues)}")
        for issue in _issues[page * ISSUE_PAGE_SIZE:(page + 1) * ISSUE_PAGE_SIZE]:
            _wrapped(box, str(issue))
        _pager(box, page, pages, issues=True)
    if _severity != "INFO":
        box.operator("theme_studio.copy_report", icon="COPYDOWN")


def _draw_field(layout, state, session, draft_rna, path, *, context_label=False, reset=False,
                inclusion=None, group_id=""):
    spec = get_registry().fields[path]
    protected = path in session.draft.protected
    column = layout.column(align=True)
    if context_label:
        column.label(text=_owner_label(path))
    color = draft_color_attribute(path)
    row = column.row(align=True)
    if color:
        row.prop(draft_rna, color, text=_label(path))
    else:
        row.prop(draft_rna, draft_attribute(path), text=_label(path))
    if context_label or reset:
        op = row.operator("theme_studio.reset_field", text="", icon="LOOP_BACK")
        op.path = path
    if inclusion is not None:
        _draw_inclusion(row, inclusion, group_id)
    if not context_label and not reset:
        grouped = path in _roundness_paths or any(path in paths for paths in get_registry().recipes.values())
        if grouped:
            _wrapped(column, "Modifica separatamente" if protected else "Segue le modifiche comuni")
    layout.separator(factor=0.25)


class THEME_STUDIO_UL_fields(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index=0, flt_flag=0):
        row = layout.row(align=True)
        row.label(text=item.label)
        grouped = item.path in _roundness_paths or any(item.path in paths for paths in get_registry().recipes.values())
        row.label(text="Separato" if not item.included else "Comune" if grouped else "Individuale")
        attr = draft_color_attribute(item.path)
        if attr:
            swatch = row.row()
            swatch.enabled = False
            swatch.prop(context.window_manager.theme_studio_draft, attr, text="")


def _draw_palette(layout, state, session):
    layout.label(text="Colori principali", icon="COLOR")
    grid = layout.grid_flow(row_major=True, columns=0, even_columns=True, even_rows=False, align=True)
    for group in _palette_map:
        section = grid.box()
        row = section.row(align=True)
        row.label(text=_PALETTE_LABELS.get(group["id"], group["label"]))
        protected = sum(path in session.draft.protected for path in group["paths"])
        if protected:
            row.label(text=f"{protected} a parte", icon="DECORATE")
        op = row.operator("theme_studio.palette_details", text="Dettagli", icon="PREFERENCES")
        op.group_id = group["id"]
        swatch = section.row()
        swatch.scale_y = 1.5 if group["id"] == "borders" else 1.2
        attr = _palette_keys[group["id"]]
        swatch.prop(bpy.context.window_manager.theme_studio_palette, attr, text="")
        if any(get_registry().fields[path].length == 4 for path in group["paths"]):
            opacities = [session.draft.value(path)[3] for path in _linked_rgba_paths(group["paths"], session.draft)]
            if opacities and max(opacities) - min(opacities) > 1e-6:
                section.label(text="Opacità diverse", icon="INFO")
    _draw_roundness(layout, state, session)


def _draw_roundness(layout, state, session):
    if not _roundness_paths:
        return
    box = layout.box()
    box.label(text="Forma dei controlli", icon="MOD_UVPROJECT")
    row = box.row(align=True)
    row.prop(bpy.context.window_manager.theme_studio_palette, "roundness_common", text="Arrotondamento")
    exceptions = sum(path in session.draft.protected for path in _roundness_paths)
    if exceptions:
        row.label(text=f"{exceptions} a parte", icon="DECORATE")
    values = {session.draft.value(path) for path in _roundness_paths}
    if len(values) > 1:
        box.label(text="Valori iniziali diversi: il cursore li uniforma.", icon="INFO")
def _draw_viewport(layout, state, session, draft_rna):
    group = _viewport_group
    if group is None:
        return
    registry = get_registry()
    enum_path = next((path for path in registry.editable_paths
                      if path.endswith("view_3d.space.gradients.background_type")), None)
    if enum_path:
        background = layout.box()
        background.label(text="Sfondo · tema globale", icon="WORLD")
        background.prop(draft_rna, draft_attribute(enum_path), text="Tipo", expand=True)
        mode = session.draft.value(enum_path)
        for path in viewport_background_paths(registry, mode)[1:]:
            _draw_field(background, state, session, draft_rna, path)

    representatives = {
        "headers": ("view_3d.space.header", "view_3d.space.text"),
        "selection": ("view_3d.object_selected", "view_3d.object_active"),
        "guides": ("view_3d.grid", "view_3d.grid_major"),
    }
    for section in group["groups"]:
        suffixes = representatives.get(section["id"], ())
        if not suffixes:
            continue
        box = layout.box()
        box.label(text=section["label"])
        for suffix in suffixes:
            path = next((path for path in section["paths"] if path.endswith(suffix)), None)
            if path:
                _draw_field(box, state, session, draft_rna, path)
    more = layout.operator("theme_studio.palette_details", text="Altri colori e guide", icon="PREFERENCES")
    more.group_id = "viewport"


def _draw_contrast(layout, state, session):
    results = analyze_contrast(get_registry(), session.draft.values)
    warnings = [item for item in results if item["below_threshold"] is True]
    if warnings:
        layout.label(text="Alcuni colori potrebbero avere poco contrasto.", icon="INFO")


def _detail_group_label(group):
    category, subgroup = group.split(".", 1)
    return _DETAIL_GROUP_LABELS.get(subgroup, _DETAIL_LABELS.get(category, "Altri controlli"))


def _draw_detail_fields(layout, state, session, draft_rna, fields):
    groups = {}
    for item in fields:
        groups.setdefault(get_registry().fields[item.path].group, []).append(item)
    for group, items in groups.items():
        header, body = layout.panel(f"theme_studio_detail_{group}", default_closed=True)
        header.label(text=_detail_group_label(group))
        if body is None:
            continue
        for item in items:
            _draw_field(body, state, session, draft_rna, item.path, reset=True,
                        inclusion=item, group_id=state.palette_focus)


def _draw_details(layout, state, session, draft_rna):
    box = layout.box()
    if state.palette_focus:
        if state.palette_focus == "viewport":
            group = _viewport_group
            if group is None:
                return
            heading = box.row(align=True)
            heading.label(text=group["label"])
            heading.operator("theme_studio.palette_details", text="Tutte le categorie", icon="BACK").all_controls = True
        else:
            group = next((item for item in _palette_map if item["id"] == state.palette_focus), None)
            if group is None:
                return
            heading = box.row(align=True)
            heading.label(text=_PALETTE_LABELS.get(group["id"], group["label"]))
            heading.operator("theme_studio.palette_details", text="Tutte le categorie", icon="BACK").all_controls = True
    else:
        box.prop(state, "detail_category", text="Categoria")
        category = next((item for item in _detail_map if item["id"] == state.detail_category), None)
        if category is None:
            return
    if _detail_context_items:
        box.prop(state, "detail_context", text="Contesto")
    if not state.detail_fields:
        return
    _draw_detail_fields(layout, state, session, draft_rna, state.detail_fields)


def _draw_disclosure(layout, state, property_name, label):
    row = layout.row(align=True)
    expanded = getattr(state, property_name)
    row.prop(state, property_name, text=label, icon="TRIA_DOWN" if expanded else "TRIA_RIGHT", emboss=False)
    return layout.column(align=True) if expanded else None


def _draw_safety(layout, width=550):
    _wrapped(layout, "Le modifiche al tema sono reversibili e non salvano le preferenze di Blender.", width=width)
    _wrapped(layout, "Se Blender si è chiuso durante una modifica, risolvi il recupero prima di continuare.", width=width)
    state = bpy.context.window_manager.theme_studio_ui
    details = _draw_disclosure(layout, state, "show_safety_details", "Dettagli sulla modifica")
    if details:
        _wrapped(details, f"Copia di sicurezza: {_journal_path or 'non disponibile'}", width=width)
        if _message:
            _wrapped(details, _message, width=width)
        _wrapped(details, "Confronta mostra il tema iniziale. Scarta modifiche tenta il ripristino e segnala i conflitti. Non usare Ctrl+Z.", width=width)
        _wrapped(details, "Il salvataggio manuale esterno può rendere permanenti le modifiche live. Colore e opacità condividono il selettore.", width=width)
        _wrapped(details, "Disattivazione e cambio file tentano il ripristino. In caso di errore, la sessione resta disponibile per un nuovo tentativo.", width=width)
    if get_session() is None and _journal_path:
        layout.operator_context = "INVOKE_DEFAULT"
        layout.operator("theme_studio.reopen_initial", icon="DUPLICATE")
        _wrapped(layout, "Riapre i valori iniziali come modifica live. Per recuperare una sessione interrotta, usa i comandi qui sopra.", width=width)


class THEME_STUDIO_OT_reopen_initial(_SessionAction, bpy.types.Operator):
    bl_idname = "theme_studio.reopen_initial"
    bl_label = "Riapri la copia iniziale…"
    bl_description = "Ripristina live i valori iniziali dell'ultimo lavoro in modo reversibile"

    @classmethod
    def poll(cls, _context):
        return _registry is not None and not _recovery_path and get_session() is None and bool(_journal_path)

    def invoke(self, context, _event):
        return context.window_manager.invoke_props_dialog(self, width=460, confirm_text="Riapri nella copia")

    def draw(self, _context):
        _wrapped(self.layout, "Ripristina live i valori iniziali dell'ultimo lavoro. Puoi confrontarli o scartarli.", width=460)

    def run(self, context):
        global _preview_values
        document = read_document(_journal_path)
        registry = get_registry()
        if (document.get("format") != "theme-studio-recovery" or document.get("schema_version") != 1
                or document.get("build_hash") != registry.build_hash):
            raise ValueError("La copia iniziale non è compatibile con questa versione di Blender.")
        values = registry.validate(document.get("initial", {}), complete=True, allow_metadata=True)
        initial = {p: values[p] for p in registry.editable_paths}
        THEME_STUDIO_OT_start.run(self, context)
        session = _require_session()
        draft = session.draft
        previous_draft = copy.deepcopy(draft)
        draft.replace_profile(Profile("Copia iniziale", initial))
        try:
            _apply_live_edit("Copia iniziale riaperta.")
        except Exception:
            session.draft = previous_draft
            _close_session("cancel")
            raise


class THEME_STUDIO_OT_recovery_choice(bpy.types.Operator):
    bl_idname = "theme_studio.recovery_choice"
    bl_label = "Scegli recupero campo"
    path: StringProperty(options={"SKIP_SAVE"})
    choice: EnumProperty(items=(("keep", "Mantieni valore attuale", ""), ("restore", "Ripristina valore iniziale", "")), options={"SKIP_SAVE"})

    def execute(self, _context):
        global _recovery_error, _recovery_detail
        if _recovery_blocked or _recovery_document is None:
            self.report({"ERROR"}, "Ripara manualmente il journal prima di scegliere.")
            return {"CANCELLED"}
        _recovery_decisions[self.path] = self.choice
        _recovery_error, _recovery_detail = "", ""
        _redraw()
        return {"FINISHED"}


class THEME_STUDIO_OT_retry_recovery_discovery(bpy.types.Operator):
    bl_idname = "theme_studio.retry_recovery_discovery"
    bl_label = "Riprova a leggere il recupero"

    def execute(self, _context):
        global _recovery_path, _recovery_document, _recovery_plan
        global _recovery_error, _recovery_progress, _recovery_blocked
        _recovery_path, _recovery_document, _recovery_plan = "", None, None
        _recovery_error, _recovery_progress, _recovery_blocked = "", "", False
        _recovery_decisions.clear()
        directory = _storage_override
        if directory is None:
            directory_name = bpy.utils.user_resource("CONFIG", path="theme-studio", create=True)
            directory = Path(directory_name) if directory_name else None
        if directory:
            _discover_recovery(directory)
        else:
            _recovery_blocked = True
            _recovery_error = "Cartella di recupero non disponibile; nessun journal è stato modificato."
        _redraw()
        return {"FINISHED"}


class THEME_STUDIO_OT_archive_recovery(bpy.types.Operator):
    bl_idname = "theme_studio.archive_recovery"
    bl_label = "Conserva i dati di recupero…"
    snapshot: StringProperty(options={"SKIP_SAVE"})

    @classmethod
    def poll(cls, _context):
        return bool(_recovery_records) and get_session() is None

    def invoke(self, context, _event):
        self.snapshot = json.dumps({"filenames": _recovery_filenames, "records": _recovery_records})
        return context.window_manager.invoke_props_dialog(self, width=560, confirm_text="Conserva i dati")

    def draw(self, _context):
        _wrapped(self.layout, "Crea una copia dei dati di recupero nell'archivio. Gli originali restano al loro posto; il tema corrente non cambia.", width=560)
        _wrapped(self.layout, "Questa azione NON ripristina i valori iniziali. La copia archivata resta conservata.", width=560)

    def execute(self, _context):
        global _recovery_error, _recovery_detail, _recovery_progress, _recovery_blocked
        global _recovery_path, _recovery_document, _recovery_plan
        directory = _storage_override
        failure = ""
        snapshot = {"filenames": (), "records": ()}
        try:
            if directory is None:
                directory_name = bpy.utils.user_resource("CONFIG", path="theme-studio", create=True)
                directory = Path(directory_name) if directory_name else None
            if get_session() is not None or directory is None:
                raise RuntimeError("Archiviazione non disponibile durante una sessione live.")
            snapshot = json.loads(self.snapshot)
            paths = sorted(directory.glob("recovery-*.json"))
            if tuple(path.name for path in paths) != tuple(snapshot["filenames"]):
                raise RuntimeError("I file di recupero sono cambiati. Riprova a cercarli prima di archiviare.")
            records = {item["path"]: item["digest"] for item in snapshot["records"]}
            if set(records) != {item["path"] for item in _recovery_records}:
                raise RuntimeError("L'elenco dei recuperi è cambiato. Riprova a cercarli prima di archiviare.")
            for path in paths:
                if str(path) in records:
                    archive_recovery(path, records[str(path)])
            self.report({"INFO"}, "Dati conservati nell'archivio; il tema corrente non è cambiato.")
        except Exception as exc:
            failure = str(exc)
        try:
            if directory is not None:
                _discover_recovery(directory)
        except Exception as exc:
            failure = "\n".join(filter(None, (failure, f"Nuova lettura non riuscita: {exc}")))
        if failure:
            _recovery_error = "Archiviazione non completata. Il tema non è stato ripristinato; il recupero resta bloccato."
            attempted = ", ".join(item.get("path", "") for item in snapshot.get("records", ()) if item.get("path"))
            archive_location = f"Archivio: {directory / 'archive'}" if directory is not None else ""
            _recovery_detail = "\n".join(filter(None, (attempted, archive_location, failure)))
            _recovery_blocked = True
            _recovery_document, _recovery_plan = None, None
            if not _recovery_path:
                _recovery_path = next((item.get("path", "") for item in snapshot.get("records", ())
                                       if item.get("path")), "archivio")
        elif not _recovery_records:
            self.report({"INFO"}, "Copia archiviata; gli originali restano al loro posto. Il tema corrente non è stato ripristinato.")
        _redraw()
        return {"FINISHED"}


class THEME_STUDIO_OT_recovery(bpy.types.Operator):
    bl_idname = "theme_studio.recovery"
    bl_label = "Risolvi recupero"
    outcome: EnumProperty(items=(("restore", "Ripristina tema iniziale", ""), ("keep", "Mantieni tema corrente", "")), options={"SKIP_SAVE"})

    def execute(self, _context):
        global _recovery_error, _recovery_detail, _recovery_progress, _recovery_path, _recovery_document, _recovery_plan
        try:
            if _recovery_blocked or _recovery_document is None:
                raise RuntimeError("Ripara manualmente il journal prima di riprovare.")
            decisions = dict(_recovery_decisions)
            if self.outcome == "keep":
                journal = parse_recovery(read_document(_recovery_path), get_registry())
                if any(choice == "restore" for choice in journal["decisions"].values()):
                    raise RuntimeError("Il journal contiene già scelte di ripristino. Riprova Ripristina tema iniziale; non è possibile passare a Mantieni tema corrente.")
                paths = set(journal["owned"]) | set(journal["pending"]) | set(journal["conflicts"])
                decisions = {path: "keep" for path in paths}
            else:
                conflicts = {item.path for item in (_recovery_plan.conflicts if _recovery_plan else ())}
                missing = conflicts - set(decisions)
                if missing:
                    raise ValueError(f"Scegli un esito per ogni conflitto ({len(missing)} ancora da scegliere).")
            result = execute_recovery(get_registry(), BlenderBackend(get_registry()), _recovery_path,
                                      decisions, outcome="cancelled" if self.outcome == "restore" else "confirmed")
            _recovery_progress = f"Campi risolti: {len(result.settled)}"
            if result.completed:
                _recovery_path, _recovery_document, _recovery_plan = "", None, None
                _recovery_decisions.clear()
                _recovery_error, _recovery_detail = "", ""
            else:
                _recovery_error = "Recupero incompleto. Il journal è conservato; riprova."
        except Exception as exc:
            _recovery_error = "Il recupero non è stato completato. I dati restano conservati."
            _recovery_detail = str(exc)
            _recovery_progress = "Recupero non completato · journal conservato"
        _redraw()
        return {"FINISHED"}


def _discover_recovery(directory):
    global _recovery_path, _recovery_document, _recovery_plan, _recovery_error, _recovery_progress
    global _recovery_blocked, _recovery_records, _recovery_filenames, _recovery_detail
    _recovery_path, _recovery_document, _recovery_plan = "", None, None
    _recovery_error, _recovery_detail, _recovery_progress, _recovery_blocked = "", "", "", False
    _recovery_decisions.clear()
    _recovery_records = ()
    journals = sorted(directory.glob("recovery-*.json"))
    _recovery_filenames = tuple(path.name for path in journals)
    unresolved = []
    for path in journals:
        digest = ""
        try:
            with path.open("rb") as stream:
                raw = stream.read(MAX_DOCUMENT_BYTES + 1)
            digest = hashlib.sha256(raw).hexdigest()
            if len(raw) > MAX_DOCUMENT_BYTES:
                raise ValueError("Recovery journal exceeds the supported size")
            if is_archived_recovery(path, digest):
                continue
            document = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object,
                                   parse_constant=_reject_constant)
            if not isinstance(document, dict):
                raise ValueError("Recovery journal must be an object")
            status, detail = classify_recovery(document, get_registry())
            if status != "resolved":
                unresolved.append({"path": str(path), "digest": digest, "status": status,
                                   "detail": detail, "document": document})
        except Exception as exc:
            unresolved.append({"path": str(path), "digest": digest, "status": "invalid",
                               "detail": str(exc), "document": None})
    _recovery_records = tuple({key: item[key] for key in ("path", "digest", "status", "detail")}
                              for item in unresolved)
    _recovery_detail = "\n".join(f"{item['path']}: {item['detail']}" for item in unresolved if item["detail"])
    if len(unresolved) != 1 or unresolved and unresolved[0]["status"] != "pending":
        _recovery_blocked = True
        _recovery_path = unresolved[0]["path"] if unresolved else ""
        if len(unresolved) > 1:
            _recovery_error = f"Ci sono {len(unresolved)} recuperi da controllare. Nessun file è stato modificato."
        elif unresolved:
            statuses = {"incompatible": "Questa copia viene da un'altra versione di Blender.",
                        "invalid": "Il file di recupero non è leggibile o non è valido."}
            _recovery_error = statuses.get(unresolved[0]["status"], "Il recupero richiede un controllo.")
        else:
            _recovery_blocked = False
        return
    if not unresolved:
        return
    record = unresolved[0]
    _recovery_path = record["path"]
    _recovery_document = record["document"]
    try:
        parsed = parse_recovery(_recovery_document, get_registry())
        _recovery_decisions.update(parsed["decisions"])
        backend = BlenderBackend(get_registry())
        current = {field: backend.read(field) for field in set(parsed["owned"]) | set(parsed["pending"])}
        _recovery_plan = plan_recovery(_recovery_document, current, get_registry())
    except Exception as exc:
        _recovery_blocked = True
        _recovery_error = "Il recupero non può essere aperto in sicurezza."
        _recovery_detail = str(exc)


def _draw_recovery(layout):
    box = layout.box()
    box.alert = _recovery_blocked or bool(_recovery_error)
    box.label(text="Prima risolvi il recupero", icon="ERROR" if _recovery_blocked or _recovery_error else "RECOVER_LAST")
    status = _recovery_error or _recovery_progress or "Scegli cosa fare con i valori modificati prima dell'interruzione."
    _wrapped(box, status)
    if _recovery_blocked:
        box.operator("theme_studio.retry_recovery_discovery", icon="FILE_REFRESH")
    if _recovery_records and get_session() is None:
        box.operator("theme_studio.archive_recovery", text="Conserva i dati e continua…", icon="FILE_FOLDER")
        _wrapped(box, "Conserva i file senza ripristinare il tema. Puoi continuare con il tema attuale dopo averli archiviati.")
    if _recovery_plan and not _recovery_blocked:
        for conflict in _recovery_plan.conflicts:
            label_row = box.row()
            label_row.label(text=_label(conflict.path))
            explanation = ("Per questa preferenza puoi mantenere il valore attuale; il ripristino iniziale non è disponibile."
                           if conflict.path == "preferences.use_preferences_save" else
                           "Scegli se tenere il valore attuale o ripristinare quello iniziale per questo campo.")
            _wrapped(box, explanation)
            choices = (("keep", "Mantieni valore attuale"),) if conflict.path == "preferences.use_preferences_save" else (
                ("keep", "Mantieni valore attuale"), ("restore", "Ripristina valore iniziale"))
            for choice, label in choices:
                choice_row = box.row()
                op = choice_row.operator("theme_studio.recovery_choice", text=label,
                                         depress=_recovery_decisions.get(conflict.path) == choice)
                op.path, op.choice = conflict.path, choice
    state = bpy.context.window_manager.theme_studio_ui
    details = _draw_disclosure(box, state, "show_recovery_details", "Dettagli tecnici")
    if details:
        for record in _recovery_records:
            _wrapped(details, f"{record['path']} · {record['status']} · SHA-256 {record['digest']}")
        if _recovery_detail:
            _wrapped(details, _recovery_detail)
    if _recovery_plan and not _recovery_blocked:
        _wrapped(box, "Ripristina usa i valori iniziali ancora posseduti da questo lavoro. Mantieni lascia invariati i valori attuali.")
        restore = box.row()
        restore.operator("theme_studio.recovery", text="Ripristina tema iniziale", icon="LOOP_BACK").outcome = "restore"
        keep = box.row()
        keep.operator("theme_studio.recovery", text="Mantieni tema corrente", icon="CHECKMARK").outcome = "keep"


class THEME_STUDIO_OT_safety(bpy.types.Operator):
    bl_idname = "theme_studio.safety"
    bl_label = "Copia iniziale e recupero…"

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=550)

    def draw(self, context):
        _draw_safety(self.layout, width=550)

    def execute(self, context):
        return {"FINISHED"}


class THEME_STUDIO_MT_session(bpy.types.Menu):
    bl_label = "File e recupero"

    def draw(self, context):
        layout = self.layout
        layout.operator_context = "INVOKE_DEFAULT"
        state = context.window_manager.theme_studio_ui
        layout.prop(state, "profile_name")
        layout.operator("theme_studio.save_profile", icon="FILE_TICK")
        layout.operator("theme_studio.load_profile", icon="FILE_FOLDER")
        layout.separator()
        layout.operator("theme_studio.safety", icon="INFO")
        layout.operator("theme_studio.cancel", icon="CANCEL")


def _draw_inclusion(layout, item, group_id=""):
    palette_group = next((group for group in _palette_map
                          if group["id"] == group_id and item.path in group["paths"]), None)
    if palette_group is None:
        palette_group = next((group for group in _palette_map if item.path in group["paths"]), None)
    grouped = (palette_group is not None or item.path in _roundness_paths
               or any(item.path in paths for paths in get_registry().recipes.values()))
    if grouped:
        layout.prop(item, "included", text="", icon="LINKED" if item.included else "UNLINKED")


def session_draft_protected():
    session = get_session()
    return session.draft.protected if session else frozenset()


class THEME_STUDIO_OT_palette_details(bpy.types.Operator):
    bl_idname = "theme_studio.palette_details"
    bl_label = "Apri dettagli del gruppo"
    group_id: StringProperty(options={"SKIP_SAVE"})
    all_controls: BoolProperty(options={"SKIP_SAVE"})

    def execute(self, context):
        state = context.window_manager.theme_studio_ui
        if self.all_controls:
            state.palette_focus = ""
            if _detail_items:
                state.detail_category = _detail_items[0][0]
        else:
            if self.group_id == "viewport" and _viewport_group is not None:
                state.palette_focus = "viewport"
            elif not any(group["id"] == self.group_id for group in _palette_map):
                self.report({"ERROR"}, "Gruppo palette non disponibile")
                return {"CANCELLED"}
            else:
                state.palette_focus = self.group_id
        state.show_details = True
        state.workspace_page = "details"
        _detail_changed(state, context)
        _redraw()
        return {"FINISHED"}


class THEME_STUDIO_PT_theme(bpy.types.Panel):
    bl_label = "Theme Studio"
    bl_idname = "THEME_STUDIO_PT_theme"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Theme Studio"

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = False
        state = context.window_manager.theme_studio_ui
        session = get_session()
        heading = layout.row(align=True)
        heading.label(text="Personalizza il tema", icon="COLOR")
        heading.menu("THEME_STUDIO_MT_session", text="", icon="DOWNARROW_HLT")
        if _recovery_path:
            _draw_recovery(layout)
            return
        if session is None:
            layout.label(text=session_status(), icon="INFO")
        if _severity != "INFO":
            _draw_status(layout, state)
        if session is None:
            if _save_pending:
                _wrapped(layout, "Il tema resta attivo, ma il salvataggio delle preferenze non è stato verificato.")
                layout.operator_context = "INVOKE_DEFAULT"
                layout.operator("theme_studio.save_preferences", icon="FILE_TICK")
            _wrapped(layout, "Parti dai colori attuali. Le modifiche live restano reversibili e non salvate.")
            start = layout.row()
            start.scale_y = 1.3
            start.operator("theme_studio.start", text="Riprova" if _start_failed else "Inizia a modificare", icon="DUPLICATE")
            layout.operator_context = "INVOKE_DEFAULT"
            secondary = layout.row()
            secondary.scale_y = 0.85
            secondary.operator("theme_studio.load_profile", text="Apri tema salvato…", icon="FILE_FOLDER")
            if _severity == "INFO":
                _draw_status(layout, state)
            if _file_notice:
                _wrapped(layout, _file_notice)
            return

        if session.faulted:
            layout.label(text=session_status(), icon="ERROR")
            _wrapped(layout, "Ripristino non completato. Le modifiche sono bloccate. Puoi salvare una copia o riprovare il ripristino; i dettagli di recupero sono in File e recupero.")
            layout.operator("theme_studio.cancel", text="Riprova il ripristino", icon="CANCEL")
            return

        navigation = layout.row(align=True)
        navigation.prop(state, "workspace_page", expand=True)
        secondary = layout.row(align=True)
        secondary.scale_y = 0.8
        secondary.operator_context = "INVOKE_DEFAULT"
        if _comparing:
            secondary.operator("theme_studio.previous", text="Torna al tema live", icon="HIDE_OFF")
        else:
            compare = secondary.row(align=True)
            compare.enabled = _theme_changed_or_pending(session)
            compare.operator("theme_studio.previous", text="Confronta", icon="ARROW_LEFTRIGHT")
        secondary.operator("theme_studio.finish", text="Termina…", icon="CHECKMARK")
        secondary.operator("theme_studio.cancel", text="Scarta", icon="CANCEL")
        history = layout.row(align=True)
        history.scale_y = 0.8
        history.operator_context = "INVOKE_DEFAULT"
        history.label(text="Modifica")
        history.operator("theme_studio.undo", text="", icon="LOOP_BACK")
        history.operator("theme_studio.redo", text="", icon="LOOP_FORWARDS")
        layout.label(text=session_status(), icon="INFO")
        draft_rna = context.window_manager.theme_studio_draft
        if state.workspace_page == "theme":
            _draw_palette(layout, state, session)
            _draw_contrast(layout, state, session)
        elif state.workspace_page == "viewport":
            _draw_viewport(layout, state, session, draft_rna)
        else:
            _draw_details(layout, state, session, draft_rna)
        if _severity == "INFO":
            _draw_status(layout, state)


_CLASSES = (
    THEME_STUDIO_PG_target, THEME_STUDIO_PG_state, THEME_STUDIO_OT_start, THEME_STUDIO_OT_preview,
    THEME_STUDIO_OT_previous, THEME_STUDIO_OT_cancel, THEME_STUDIO_OT_confirm,
    THEME_STUDIO_OT_finish, THEME_STUDIO_OT_save_preferences, THEME_STUDIO_OT_undo, THEME_STUDIO_OT_redo,
    THEME_STUDIO_OT_common_value, THEME_STUDIO_OT_palette_details,
    THEME_STUDIO_OT_reopen_initial, THEME_STUDIO_OT_recovery_choice,
    THEME_STUDIO_OT_retry_recovery_discovery, THEME_STUDIO_OT_archive_recovery, THEME_STUDIO_OT_recovery,
    THEME_STUDIO_OT_protect_field, THEME_STUDIO_OT_reset_field,
    THEME_STUDIO_OT_copy_report, THEME_STUDIO_OT_page,
    THEME_STUDIO_OT_save_profile, THEME_STUDIO_OT_load_profile, THEME_STUDIO_OT_safety,
    THEME_STUDIO_MT_session, THEME_STUDIO_UL_fields, THEME_STUDIO_PT_theme,
)


def register(*, storage_dir=None):
    """storage_dir is an explicit override for isolated probes."""
    global _registry, _storage_override, _attributes, _color_attributes, _alpha_attributes, _palette_map, _viewport_group, _detail_map, _palette_keys, _palette_alpha_keys, _roundness_paths, _detail_items, _detail_context_items, _detail_context_labels, _recovery_path, _recovery_document, _recovery_plan, _recovery_error, _recovery_detail, _recovery_progress, _recovery_blocked, _recovery_records, _recovery_filenames
    if _registered_classes:
        raise RuntimeError("Theme Studio UI è già registrato")
    if get_session() is not None:
        raise RuntimeError("Una sessione conservata deve essere annullata prima di registrare di nuovo")
    _discard_colors()
    import bpy
    _registry = load_catalog(build_hash=bpy.app.build_hash.decode())
    _detail_context_cache.clear()
    groups = palette_groups(_registry)
    _palette_map = tuple(item for item in groups if "paths" in item)
    _viewport_group = next((item for item in groups if item["id"] == "viewport"), None)
    _detail_map = tuple(detail_categories(_registry))
    _roundness_paths = roundness_paths(_registry)
    _detail_items = tuple((item["id"], _DETAIL_LABELS.get(item["id"], item["label"]),
                           f"{len(item['paths'])} controlli") for item in _detail_map)
    _palette_keys = {group["id"]: f"palette_{index:02d}" for index, group in enumerate(_palette_map)}
    _palette_alpha_keys = {"borders": "palette_alpha_borders"}
    THEME_STUDIO_PG_state.__annotations__["detail_category"] = EnumProperty(
        name="Categoria", items=_detail_category_items, options={"SKIP_SAVE"}, update=_detail_changed,
    )
    THEME_STUDIO_PG_state.__annotations__["detail_context"] = EnumProperty(
        name="Contesto", items=_detail_context_items_callback, options={"SKIP_SAVE"}, update=_detail_context_changed,
    )
    _storage_override = Path(storage_dir).expanduser().resolve() if storage_dir is not None else None
    _attributes = {p: f"field_{index:04d}" for index, p in enumerate(_registry.fields) if p in _registry.editable_paths}
    _color_attributes = {}
    _alpha_attributes = {}
    draft_properties = {attr: _draft_property(path, _registry.fields[path]) for path, attr in _attributes.items()}
    for index, (path, spec) in enumerate(_registry.fields.items()):
        if path not in _registry.editable_paths or spec.subtype not in {"COLOR", "COLOR_GAMMA"} or spec.length not in {3, 4}:
            continue
        if spec.length == 3:
            _color_attributes[path] = _attributes[path]
        else:
            _color_attributes[path] = f"rgb_{index:04d}"
            _alpha_attributes[path] = f"alpha_{index:04d}"
            draft_properties[_color_attributes[path]] = _color_property(path, spec)
            draft_properties[_alpha_attributes[path]] = _color_property(path, spec, alpha=True)
    draft_class = type("THEME_STUDIO_PG_draft", (bpy.types.PropertyGroup,), {
        "__module__": __name__,
        "__annotations__": draft_properties,
    })
    palette_props = {key: _palette_property(group) for group in _palette_map
                     for key in (_palette_keys[group["id"]],)}
    border_group = next(group for group in _palette_map if group["id"] == "borders")
    palette_props.update({key: _palette_alpha_property(border_group) for key in _palette_alpha_keys.values()})
    palette_props["roundness_common"] = _roundness_property(_roundness_paths)
    palette_class = type("THEME_STUDIO_PG_palette", (bpy.types.PropertyGroup,), {
        "__module__": __name__, "__annotations__": palette_props,
    })
    try:
        for cls in (draft_class, palette_class, *_CLASSES):
            bpy.utils.register_class(cls)
            _registered_classes.append(cls)
        bpy.types.WindowManager.theme_studio_ui = PointerProperty(type=THEME_STUDIO_PG_state, options={"SKIP_SAVE"})
        bpy.types.WindowManager.theme_studio_draft = PointerProperty(type=draft_class, options={"SKIP_SAVE"})
        bpy.types.WindowManager.theme_studio_palette = PointerProperty(type=palette_class, options={"SKIP_SAVE"})
        bpy.app.handlers.load_pre.append(_load_pre)
        directory = _storage_override or Path(bpy.utils.user_resource("CONFIG", path="theme-studio", create=True))
        if directory:
            directory.mkdir(parents=True, exist_ok=True)
            _recovery_path, _recovery_document, _recovery_plan = "", None, None
            _recovery_error, _recovery_detail, _recovery_progress, _recovery_blocked = "", "", "", False
            _recovery_records, _recovery_filenames = (), ()
            _recovery_decisions.clear()
            _discover_recovery(directory)
    except Exception:
        for name in ("theme_studio_palette", "theme_studio_draft", "theme_studio_ui"):
            if hasattr(bpy.types.WindowManager, name):
                delattr(bpy.types.WindowManager, name)
        for cls in reversed(_registered_classes):
            bpy.utils.unregister_class(cls)
        _registered_classes.clear()
        _palette_map = _detail_map = _detail_items = ()
        _palette_keys = {}
        _detail_context_items = ()
        _detail_context_labels = {}
        _detail_context_cache.clear()
        raise


def unregister():
    global _registry, _storage_override, _palette_map, _detail_map, _palette_keys, _detail_items, _detail_context_items, _detail_context_labels, _recovery_path, _recovery_document, _recovery_plan, _recovery_blocked, _recovery_records, _recovery_filenames, _recovery_error, _recovery_detail, _recovery_progress
    # Failure deliberately leaves all registered UI and handlers intact.
    _cancel_for_lifecycle("disattivazione addon")
    _discard_colors()
    if _load_pre in bpy.app.handlers.load_pre:
        bpy.app.handlers.load_pre.remove(_load_pre)
    for name in ("theme_studio_palette", "theme_studio_draft", "theme_studio_ui"):
        if hasattr(bpy.types.WindowManager, name):
            delattr(bpy.types.WindowManager, name)
    for cls in reversed(_registered_classes):
        bpy.utils.unregister_class(cls)
    _registered_classes.clear()
    _registry = None
    _storage_override = None
    _recovery_path, _recovery_document, _recovery_plan, _recovery_blocked = "", None, None, False
    _recovery_records, _recovery_filenames = (), ()
    _recovery_error, _recovery_detail, _recovery_progress = "", "", ""
    _recovery_decisions.clear()
    _palette_map = _detail_map = _detail_items = ()
    _palette_keys = {}
    _detail_context_items = ()
    _detail_context_labels = {}
    _detail_context_cache.clear()
