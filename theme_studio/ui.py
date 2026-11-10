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
from . import native_themes
from .palette import detail_categories, palette_groups, roundness_paths, viewport_background_paths
from .picking import resolve_target
from .labels import field_label
from .contrast import analyze_contrast
from .translations import iface, tip, CONTEXT


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
_ui_hooks_registered = False
_ui_hooks = []
_picker_generation = 0
_journal_path = ""
_message = ""
_severity = "INFO"
_issues = ()
_preview_values = None
_comparing = False
_completion = "Current theme"
_file_notice = ""
_save_pending = False
_session_theme_path = ""
_theme_source_origin = None
_native_theme_library_associations = {}
_theme_result = None
_theme_identity_unknown = False
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
_detail_category_display = ()
_detail_context_display = ()
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
_native_save_plans = {}
_native_enum_item_refs = {}


_OWNER_NAMES = {
    "node_editor": "Node Editor", "graph_editor": "Graph Editor", "outliner": "Outliner",
    "image_editor": "Image / UV Editor", "dopesheet_editor": "Dope Sheet / Timeline",
    "view_3d": "3D View", "text_editor": "Text Editor", "file_browser": "File Browser",
    "nla_editor": "Nonlinear Animation", "sequence_editor": "Video Sequencer", "properties": "Properties",
    "preferences": "Preferences", "info": "Info", "console": "Console", "clip_editor": "Movie Clip Editor",
    "topbar": "Top Bar", "statusbar": "Status Bar", "spreadsheet": "Spreadsheet",
    "wcol_regular": "Regular Controls", "wcol_tool": "Tools", "wcol_text": "Text Fields",
    "wcol_option": "Checkboxes", "wcol_toggle": "Toggles", "wcol_num": "Numeric Fields",
    "wcol_numslider": "Numeric Sliders", "wcol_tab": "Tabs", "wcol_box": "Boxes",
    "wcol_toolbar_item": "Toolbar Items", "wcol_radio": "Radio Buttons", "wcol_curve": "Curves",
    "wcol_menu": "Menus", "wcol_pulldown": "Pulldown Menus", "wcol_menu_back": "Menu Backgrounds",
    "wcol_pie_menu": "Pie Menus", "wcol_tooltip": "Tooltips", "wcol_menu_item": "Menu Items",
    "wcol_scroll": "Scrollbars", "wcol_progress": "Progress Bars", "wcol_list_item": "List Items",
    "panel_title": "Panel Titles", "widget": "Widget Text", "tooltip": "Tooltips",
}

_LABELS = {
    "node_editor.space.back": "Nodes · Background",
    "node_editor.space.header": "Node Editor · Header",
    "node_editor.node_backdrop": "Compositor Image · Background",
    "node_editor.grid": "Grid · Color",
    "node_editor.grid_levels": "Grid · Dots Level",
    "node_editor.noodle_curving": "Wires · Curvature",
    "node_editor.wire": "Wires · Outer Color",
    "node_editor.wire_inner": "Wires · Inner Color",
    "node_editor.wire_select": "Selected Wires · Color",
    "node_editor.node_outline": "Nodes · Outline",
    "node_editor.node_selected": "Nodes · Selected",
    "node_editor.node_active": "Nodes · Active",
    "view_3d.space.gradients.background_type": "Theme Background · Type",
    "view_3d.space.gradients.high_gradient": "Theme Background · Top / Solid",
    "view_3d.space.gradients.gradient": "Theme Background · Bottom",
    "view_3d.grid": "Grid · Color",
    "view_3d.grid_major": "Grid · Major Lines",
    "view_3d.grid_axis_brightness": "Axes · Brightness",
    "view_3d.wire": "Objects · Outline",
    "view_3d.object_selected": "Objects · Selected",
    "view_3d.object_active": "Objects · Active",
    "view_3d.vertex_size": "Vertices · Size",
}

_FIELD_NAMES = {
    "back": "Background", "header": "Header", "header_text": "Header Text",
    "header_text_hi": "Highlighted Header Text", "text": "Text", "text_hi": "Highlighted Text",
    "text_sel": "Selected Text", "outline": "Outline", "outline_sel": "Selected Outline",
    "inner": "Inner", "inner_sel": "Selected Inner", "item": "Item",
}
def get_registry():
    if _registry is None:
        raise RuntimeError("Theme Studio is not registered")
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
    indexed = {"bone_color_sets": "Bone · Group", "collection_color": "Collection", "strip_color": "Strip · Group"}
    base, _, number = key.partition("[")
    if base in indexed and number:
        return "{owner} {index}".format(owner=indexed[base], index=int(number.rstrip(']')) + 1)
    return _OWNER_NAMES.get(key, key.replace("_", " ").title())


def _picker_paths(registry, kind, editor_id):
    paths = []
    for path, spec in registry.fields.items():
        if not spec.editable:
            continue
        parts = _short_path(path).split(".")
        owner = parts[1] if parts[0] == "user_interface" and len(parts) > 1 else parts[0]
        if (kind == "controls" and parts[0] == "user_interface") or (kind == "editor" and owner == editor_id):
            paths.append(path)
    return tuple(paths)


def _set_picker_target(state, registry, target):
    paths = _picker_paths(registry, target["kind"], target["editor_id"])
    if not paths:
        return False
    categories = {registry.fields[path].group.split(".", 1)[0] for path in paths}
    color_categories = {registry.fields[path].group.split(".", 1)[0] for path in paths
                        if registry.fields[path].subtype in {"COLOR", "COLOR_GAMMA"}}
    preferred = next((category for category in ("surfaces", "states", "text")
                      if category in color_categories), None)
    state.picker_active = True
    state.picker_kind = target["kind"]
    state.picker_editor_id = target["editor_id"]
    state.picker_label = target["label"]
    state.palette_focus = ""
    state.detail_category = preferred or next(item[0] for item in _detail_items if item[0] in categories)
    state.show_details = True
    state.workspace_page = "details"
    return True


def _owner_display_label(path):
    return _owner_display_name(_owner_label(path))


def _owner_display_name(label):
    owner, _, index = label.rpartition(" ")
    if index.isdigit():
        return iface("{owner} {index}").format(owner=iface(owner), index=index)
    return iface(label)


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
        if session._auto_save_owned and session.backend.get_auto_save():
            raise RuntimeError(iface("Save on Exit changed during preview. Discard or resolve the setting before editing."))
        report = session.preview()
    except Exception:
        if not session.faulted:
            draft.__dict__.clear()
            draft.__dict__.update(snapshot.__dict__)
        raise
    _mark_live(session)
    if report.conflicts:
        _report("Edit blocked.", report)
        return report
    if warning:
        _notice(*warning)
    else:
        _edit_notice(("{message} Theme updated live; preferences not saved.", {"message": (message, {})}))
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
            _notice("Some group colors do not support alpha; they remain unchanged.",
                    "WARNING", tuple(unsupported_alpha))
        report = _apply_live_edit("Edit updated.")
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
        raise RuntimeError(iface("Pending changes: resolve the conflict or discard the session."))
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
        _report("Comparison closed; live theme restored.", report)


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

    kwargs = dict(name="Alpha" if alpha else _label(path, translate=False), get=get, set=set, options={"SKIP_SAVE"},
                  translation_context=CONTEXT,
                  description="Live edit; this item will not follow common changes.")
    if alpha:
        return FloatProperty(min=0, max=100, subtype="PERCENTAGE", precision=1, **kwargs)
    return FloatVectorProperty(size=spec.length, subtype=spec.subtype, min=spec.minimum, max=spec.maximum, **kwargs)


def _short_path(path):
    return path.removeprefix("preferences.themes[0].").removeprefix("preferences.ui_styles[0].")


def _label(path, *, translate=True):
    if path in _roundness_paths:
        label = "Roundness"
    else:
        label = _LABELS.get(_short_path(path), _FIELD_NAMES.get(
            path.rsplit(".", 1)[-1], get_registry().fields[path].label))
    return iface(label) if translate else label


def _redraw():
    wm = bpy.context.window_manager
    if wm:
        for window in wm.windows:
            for area in window.screen.areas:
                area.tag_redraw()


def _message_text(message):
    if not isinstance(message, tuple):
        return iface(message)
    template, values = message
    return iface(template).format(**{key: _message_text(value) if isinstance(value, tuple) else value
                                     for key, value in values.items()})


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
        message = "External changes detected and preserved. Review items in Details before continuing."
    elif isinstance(exc, ApplyError):
        message = "Restore did not complete. Retry restore." if get_session() and get_session().faulted else "Could not apply theme. Operation was rolled back."
    elif isinstance(exc, (RuntimeError, ValueError)) and not isinstance(exc, ValidationError):
        message = str(exc)
    else:
        message = "Could not complete operation. Review result details."
    _notice(message, "ERROR", (*issues, str(exc)))
    traceback.print_exc()


def _report(message, report, *, count=True):
    source = message if isinstance(message, tuple) else (message, {})
    if report.conflicts:
        _notice(
            ("{message} {count} conflicts: external changes preserved; review result details before continuing.",
             {"message": source, "count": len(report.conflicts)}),
            "WARNING", report.conflicts,
        )
        print("Theme Studio:", _message_text(_message))
        for path in report.conflicts:
            print("  Conflict:", path)
    else:
        _edit_notice(("{message} {count} fields applied.",
                      {"message": source, "count": len(report.changed)}) if count else message)


def _require_session(*, allow_faulted=False):
    session = get_session()
    if session is None:
        raise RuntimeError(iface("Start editing first."))
    if session.faulted and not allow_faulted:
        raise RuntimeError(iface("Restore did not complete: retry restore. Initial copy is preserved in Details."))
    return session


def _stage_new_copy_text_shadows(draft):
    paths = (
        "preferences.ui_styles[0].widget.shadow",
        "preferences.ui_styles[0].panel_title.shadow",
        "preferences.ui_styles[0].tooltip.shadow",
    )
    changed = []
    with draft.transaction():
        for path in paths:
            if path not in draft.registry.editable_paths or draft.value(path) == 0:
                continue
            draft.set(path, 0)
            draft.protect(path, False)
            changed.append(path)
    return tuple(changed)


def _close_session(action):
    global _session, _completion, _preview_values, _comparing
    session = _require_session(allow_faulted=action == "cancel")
    if action == "cancel":
        _discard_colors()
    elif not _flush_colors(session):
        raise RuntimeError(iface("Pending changes: resolve conflict before finishing."))
    report = getattr(session, action)()
    # Never clear ownership on an exception or leave an active faulted session.
    if not session.active:
        _session = None
        _preview_values, _comparing = None, False
        _clear_native_save_plans()
        if _theme_result and _theme_result["kind"] == "export":
            _theme_result["session_open"] = False
    _completion = "Session ended"
    message = "Changes discarded." if action == "cancel" else "Theme kept. Theme Studio did not save preferences."
    if action != "cancel" and session.backend.get_auto_save():
        message += " Blender auto-save may save preferences later."
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
        print(f"Theme Studio: {reason}: cancellation FAILED; session and controls preserved. Journal: {_journal_path}")
        raise RuntimeError(f"Theme Studio: {reason}: {exc}; journal: {_journal_path}") from exc


@persistent
def _load_pre(_filename):
    global _picker_generation
    _picker_generation += 1
    try:
        bpy.context.window_manager.theme_studio_ui.picker_active = False
    except (AttributeError, RuntimeError):
        pass
    # Blender may continue loading after a handler error. The persistent handler
    # and module reference keep the failed session reachable for another cancel.
    _cancel_for_lifecycle(iface("File change"))


def _detail_category_items(_self, _context):
    global _detail_category_display
    counts = {item["id"]: len(item["paths"]) for item in _detail_map}
    if getattr(_self, "picker_active", False):
        paths = _picker_paths(get_registry(), _self.picker_kind, _self.picker_editor_id)
        counts = {identifier: sum(get_registry().fields[path].group.split(".", 1)[0] == identifier
                                  for path in paths) for identifier, _label, _description in _detail_items}
    _detail_category_display = tuple((identifier, iface(label), tip("{count} controls").format(count=counts[identifier]))
                                     for identifier, label, _description in _detail_items if counts[identifier])
    return _detail_category_display


def _context_buckets(paths, owner_label):
    buckets = {}
    for path in paths:
        buckets.setdefault(owner_label(path), []).append(path)
    return buckets


def _paths_in_context(paths, selected, owner_label):
    return tuple(path for path in paths if not selected or owner_label(path) == selected)


def _detail_paths(state):
    if getattr(state, "picker_active", False):
        paths = _picker_paths(get_registry(), state.picker_kind, state.picker_editor_id)
        return tuple(path for path in paths
                     if get_registry().fields[path].group.split(".", 1)[0] == state.detail_category)
    if state.palette_focus:
        if state.palette_focus == "viewport" and _viewport_group:
            return tuple(path for group in _viewport_group["groups"] for path in group["paths"]) + _viewport_group["details"]
        group = next((item for item in _palette_map if item["id"] == state.palette_focus), None)
        return group["paths"] if group else ()
    category = next((item for item in _detail_map if item["id"] == state.detail_category), None)
    return category["paths"] if category else ()


def _set_detail_contexts(state):
    global _detail_context_items, _detail_context_labels
    selected = state.detail_context if _detail_context_items else ""
    key = (state.palette_focus, state.detail_category if not state.palette_focus else "")
    buckets = _context_buckets(_detail_paths(state), _owner_label)
    source_items = tuple((f"context_{index}", label, "{count} controls".format(count=len(paths)))
                         for index, (label, paths) in enumerate(buckets.items()))
    _detail_context_cache[key] = source_items
    _detail_context_items = _detail_context_cache[key]
    _detail_context_labels = {identifier: label for identifier, label, _description in source_items}
    if selected not in _detail_context_labels:
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
        item.path, item.label = path, _label(path, translate=False)


def _detail_changed(self, context):
    _set_detail_contexts(self)
    _populate_detail_fields(self)


def _detail_context_items_callback(_self, _context):
    global _detail_context_display
    buckets = _context_buckets(_detail_paths(_self), _owner_label)
    _detail_context_display = tuple((identifier, _owner_display_name(label),
                                     tip("{count} controls").format(count=len(buckets.get(label, ()))))
                                    for identifier, label, _description in _detail_context_items)
    return _detail_context_display


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

    has_alpha = any(get_registry().fields[path].length == 4 for path in group["paths"])
    return FloatVectorProperty(name=_PALETTE_LABELS.get(group["id"], group["label"]),
                               translation_context=CONTEXT,
                               description=_PALETTE_DESCRIPTIONS.get(group["id"], group.get("description", "")),
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

    return FloatProperty(name="Common Alpha", translation_context=CONTEXT, min=0, max=100, subtype="PERCENTAGE", precision=1,
                         description="Apply to linked colors that support alpha.",
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

    return FloatProperty(name="Common Roundness", translation_context=CONTEXT, min=0, max=1, subtype="FACTOR", precision=2,
                         description="Adjust linked widget shapes. Separate individual items in Details.",
                         get=get, set=set, options={"SKIP_SAVE"})


_PALETTE_LABELS = {"backgrounds": "Backgrounds", "surfaces": "Surfaces", "text": "Text",
                   "accents": "Accents", "selection": "Selection", "borders": "Borders"}
_PALETTE_DESCRIPTIONS = {
    "backgrounds": "Related hues for backgrounds. Visual effect not verified.",
    "surfaces": "Related hues for panels and controls. Visual effect not verified.",
    "text": "Related hues for text while preserving state differences. Visual effect not verified.",
    "accents": "Related hues for interface accents. Visual effect not verified.",
    "selection": "Related hues for selected items. Visual effect not verified.",
    "borders": "Related hues for borders and outlines. Visual effect not verified.",
}
_DETAIL_LABELS = {"surfaces": "Surfaces", "text": "Text", "states": "States",
                  "borders": "Borders", "symbols": "Symbols", "guides": "Guides and Grids",
                  "geometry": "Geometry", "connections": "Connections", "typography": "Typography"}
_DETAIL_GROUP_LABELS = {
    "canvas": "Backgrounds", "panels": "Panels", "controls": "Controls", "editor": "Editor",
    "headers": "Headers", "viewport_grid": "3D View Grids", "node_grid": "Node Grid",
    "node_wires": "Node Wires", "curve_handles": "Curve Handles", "curve_vertices": "Curve Vertices",
    "mesh_markers": "Mesh Markers", "mesh_topology": "Mesh Topology", "axes": "Axes",
    "gizmos": "Gizmos", "viewport_overlays": "3D View Overlays", "object_selection": "Object Selection",
    "mesh_selection": "Mesh Selection", "node_selection": "Node Selection", "outliner_selection": "Outliner Selection",
    "sequence_selection": "Sequencer Selection", "control_indicators": "Control Indicators",
    "animation_time": "Animation Time", "keyframes": "Keyframes",
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

    kwargs = dict(name=_label(path, translate=False), translation_context=CONTEXT,
                  description="Edit the live theme. This item will not follow future common changes.",
                  get=get, set=set, options={"SKIP_SAVE"})
    if spec.kind == "ENUM":
        enum_names = {"SINGLE_COLOR": "Solid Color", "LINEAR": "Linear Gradient", "RADIAL": "Radial Gradient"} if _short_path(path) == "view_3d.space.gradients.background_type" else {}
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
        return iface(_completion)
    if session.faulted:
        return iface("Restore incomplete")
    if _comparing:
        return iface("Comparing with starting theme")
    changed = _theme_changed(session)
    status = ("Editing · theme changes not saved" if changed else
              "Editing · no theme changes")
    if _has_pending_edits(session):
        return iface(status + " · changes pending")
    return iface(status)


def _visible_theme(session):
    reference = session.initial if _comparing else _preview_values
    if reference is None:
        reference = session.initial
    if any(session.backend.read(path) != reference[path] for path in get_registry().editable_paths):
        return iface("External changes detected; visible theme may differ")
    return iface("Initial theme") if _comparing else iface("Live theme")


def _capture_theme_origin(context):
    origin = {"path": "", "name": None, "user_owned": False,
              "source_bytes": None, "library_path": "", "library_target": ""}
    try:
        filepath = getattr(context.preferences.themes[0], "filepath", "")
    except Exception:
        return origin
    if not filepath:
        return origin
    try:
        path = native_themes._canonical(Path(filepath))
        preset = next(((name, native_themes._canonical(Path(candidate)), owned)
                       for name, candidate, owned in native_themes.native_theme_presets()
                       if native_themes._canonical(Path(candidate)) == path), None)
        if preset is None:
            return origin
        name, path, user_owned = preset
        origin.update(path=str(path), name=name, user_owned=user_owned)
        if not user_owned:
            return origin
        native_themes.validate_native_preset(str(path))
        data = path.read_bytes()
        native_themes.validate_native_preset(str(path))
        if path.read_bytes() != data:
            return origin
        origin["source_bytes"] = data
        association = _native_theme_library_associations.get(str(path))
        if association and association["source_bytes"] == data:
            library = native_themes._canonical(Path(association["library_path"]))
            target = native_themes._canonical(Path(association["library_target"]))
            configured = any(native_themes._canonical(Path(candidate)) == library
                             for _name, candidate in native_themes.configured_libraries(context))
            if (configured and target.parent == native_themes._canonical(library / "themes")
                    and target.read_bytes() == data):
                origin.update(library_path=str(library), library_target=str(target))
    except Exception:
        return origin
    return origin


def _verify_theme_source_library(context, origin, library_path, *, external=False):
    if (external or _theme_identity_unknown or not origin or not origin.get("user_owned")
            or not origin.get("name") or not origin.get("source_bytes")):
        return None
    try:
        source = native_themes._canonical(Path(origin["path"]))
        discovered = next(((native_themes._canonical(Path(path)), owned)
                           for _name, path, owned in native_themes.native_theme_presets()
                           if native_themes._canonical(Path(path)) == source), None)
        if discovered != (source, True):
            return None
        native_themes.validate_native_preset(str(source))
        source_bytes = source.read_bytes()
        native_themes.validate_native_preset(str(source))
        if source_bytes != origin["source_bytes"] or source.read_bytes() != source_bytes:
            return None
        selected = next((path for _name, path in native_themes.configured_libraries(context)
                         if native_themes._canonical(Path(path)) == native_themes._canonical(Path(library_path))), None)
        if selected is None:
            return None
        plan = native_themes.plan_native_theme(context, origin["name"], selected)
        target = native_themes._canonical(Path(plan["paths"][0]))
        library_themes = native_themes._canonical(Path(selected) / "themes")
        if target.parent != library_themes or plan["expected"].get(target) != source_bytes:
            return None
        return {"library_path": str(native_themes._canonical(Path(selected))),
                "library_target": str(target), "source_path": str(source),
                "source_bytes": source_bytes, "normalized_name": plan["stem"]}
    except Exception:
        return None


def _remember_native_theme_library_association(context, paths, library_path):
    try:
        library = native_themes._canonical(Path(_selected_native_library(context, library_path)))
        target = native_themes._canonical(Path(paths[0]))
        source = native_themes._canonical(Path(paths[-1]))
        if target.parent != native_themes._canonical(library / "themes"):
            return
        discovered = next(((native_themes._canonical(Path(path)), owned)
                           for _name, path, owned in native_themes.native_theme_presets()
                           if native_themes._canonical(Path(path)) == source), None)
        if discovered != (source, True):
            return
        native_themes.validate_native_preset(str(source))
        source_bytes = source.read_bytes()
        if target.read_bytes() != source_bytes or source.read_bytes() != source_bytes:
            return
        _native_theme_library_associations[str(source)] = {
            "library_path": str(library), "library_target": str(target),
            "source_bytes": source_bytes,
        }
    except Exception:
        return


def _theme_identity(context, session=None):
    """Return known preset provenance, never a claim that file matches appearance."""
    filepath = (_session_theme_path if session is not None else
                getattr(context.preferences.themes[0], "filepath", ""))
    try:
        path = native_themes._canonical(Path(filepath)) if filepath else None
        known_path = path is not None and path.is_file() and path.suffix.casefold() == ".xml"
    except (OSError, RuntimeError, ValueError):
        path = None
        known_path = False
    origin = _theme_source_origin
    known_origin = bool(origin and known_path and origin["path"] == str(path) and origin["name"])
    external = (session is not None and not session.faulted and _visible_theme(session) ==
                iface("External changes detected; visible theme may differ"))
    unknown = _theme_identity_unknown
    return {"name": origin["name"] if known_origin and not external and not unknown else None,
            "path": str(path) if known_path and not external and not unknown else None,
            "external": external, "unknown": unknown,
            "source_origin": origin if known_origin else None}


def _draw_identity_status(layout, context, state, session):
    identity = _theme_identity(context, session)
    if identity["external"]:
        origin = identity["source_origin"]
        if origin and origin["name"]:
            _wrapped(layout, iface("Theme at start of editing: {name}").format(name=origin["name"]))
        _wrapped(layout, "External changes detected · visible theme may differ")
    elif identity["unknown"]:
        _wrapped(layout, "Theme identity unknown")
    elif identity["name"]:
        label = "Theme at start of editing" if session is not None else "Preset reported by Blender"
        _wrapped(layout, iface("{label}: {name}").format(
            label=iface(label), name=identity["name"]))
    else:
        _wrapped(layout, "Theme active in Blender; preset name unknown")
    layout.label(text=session_status(), icon="INFO", text_ctxt=CONTEXT)
    if _theme_result:
        if _theme_result["kind"] == "save":
            label = "Previously saved copy" if identity["external"] else "Saved copy"
            _wrapped(layout, iface("{label}: {name}").format(
                label=iface(label), name=_theme_result["name"]))
            if _theme_result["session_open"]:
                _wrapped(layout, "Theme files were saved, but the editing session remains open.")
            elif _completion == "Preferences saved":
                _wrapped(layout, "Session ended. Blender preferences were saved.")
            else:
                _wrapped(layout, "Session ended. Blender preferences were not saved.")
        elif _theme_result["kind"] == "export":
            message = ("Theme copy exported. Editing session remains open." if
                       _theme_result["session_open"] else "Theme copy exported earlier.")
            _wrapped(layout, iface(message))


def _reset_theme_status():
    global _session_theme_path, _theme_source_origin, _theme_result, _theme_identity_unknown
    _session_theme_path = ""
    _theme_source_origin = None
    _theme_result = None
    _theme_identity_unknown = False


def _get_included(self):
    session = get_session()
    return session is not None and self.path in get_registry().editable_paths and self.path not in session.draft.protected


def _set_included(self, value):
    try:
        session = _require_session()
        if not _flush_colors(session):
            raise RuntimeError(iface("Pending changes: resolve conflict before continuing."))
        _restore_draft(session)
        old_draft = copy.deepcopy(session.draft)
        session.draft.protect(self.path, not value)
        _edit_notice("Field included without changing its value." if value else "Field excluded from common adjustments.")
    except Exception as exc:
        if "old_draft" in locals():
            session.draft.__dict__.clear()
            session.draft.__dict__.update(old_draft.__dict__)
        _error(exc)


class THEME_STUDIO_PG_target(bpy.types.PropertyGroup):
    bl_translation_context = "Theme Studio"
    path: StringProperty(translation_context=CONTEXT, options={"SKIP_SAVE"})
    label: StringProperty(translation_context=CONTEXT, options={"SKIP_SAVE"})
    included: BoolProperty(name="Follow common changes", translation_context=CONTEXT,
                           description="When enabled, follows common adjustments. Re-enabling does not change the current value.",
                           get=_get_included, set=_set_included, options={"SKIP_SAVE"})


class THEME_STUDIO_PG_state(bpy.types.PropertyGroup):
    bl_translation_context = "Theme Studio"
    workspace_page: EnumProperty(name="View", translation_context=CONTEXT, items=(
        ("theme", "Theme", "Adjust the main colors", "COLOR", 0),
        ("viewport", "3D View", "3D View theme colors", "VIEW3D", 1),
        ("details", "Details", "Advanced controls and numeric settings", "PREFERENCES", 2),
    ), default="theme", options={"SKIP_SAVE"})
    show_details: BoolProperty(name="Additional controls", translation_context=CONTEXT, options={"SKIP_SAVE"}, update=_details_toggled)
    detail_category: EnumProperty(name="Category", translation_context=CONTEXT, items=_detail_category_items, options={"SKIP_SAVE"}, update=_detail_changed)
    detail_context: EnumProperty(name="Context", translation_context=CONTEXT, items=_detail_context_items_callback, options={"SKIP_SAVE"}, update=_detail_context_changed)
    detail_fields: CollectionProperty(type=THEME_STUDIO_PG_target, translation_context=CONTEXT, options={"SKIP_SAVE"})
    detail_index: IntProperty(translation_context=CONTEXT, min=0, options={"SKIP_SAVE"})
    palette_focus: StringProperty(translation_context=CONTEXT, options={"SKIP_SAVE"})
    picker_active: BoolProperty(translation_context=CONTEXT, options={"SKIP_SAVE"})
    picker_kind: StringProperty(translation_context=CONTEXT, options={"SKIP_SAVE"})
    picker_editor_id: StringProperty(translation_context=CONTEXT, options={"SKIP_SAVE"})
    picker_label: StringProperty(translation_context=CONTEXT, options={"SKIP_SAVE"})
    issue_page: IntProperty(translation_context=CONTEXT, default=0, min=0, options={"SKIP_SAVE"})
    contrast_page: IntProperty(translation_context=CONTEXT, default=0, min=0, options={"SKIP_SAVE"})
    profile_name: StringProperty(name="JSON Project Name", translation_context=CONTEXT, default="My Theme", maxlen=80, options={"SKIP_SAVE"})
    show_issue_details: BoolProperty(name="Result Details", translation_context=CONTEXT, options={"SKIP_SAVE"})
    contrast_details: BoolProperty(name="Contrast Details", translation_context=CONTEXT, options={"SKIP_SAVE"})
    show_safety_details: BoolProperty(name="Editing Details", translation_context=CONTEXT, options={"SKIP_SAVE"})
    show_recovery_details: BoolProperty(name="Technical Details", translation_context=CONTEXT, options={"SKIP_SAVE"})


class _SessionAction:
    _operator_id = ""

    @classmethod
    def poll(cls, _context):
        session = get_session()
        return session is not None and not session.faulted

    def execute(self, context):
        global _failed_action
        try:
            session = get_session()
            if (session is not None and session._auto_save_owned and session.backend.get_auto_save()
                    and self._operator_id not in {"theme_studio.cancel", "theme_studio.finish"}):
                raise RuntimeError(iface("Save on Exit changed during preview. Discard or resolve the setting before editing."))
            if getattr(self, "_discard_pending_colors", False):
                _discard_colors()
            elif not _flush_colors():
                raise RuntimeError(iface("Pending changes: resolve conflict before continuing."))
            self.run(context)
            if _failed_action == self.bl_idname and _severity == "ERROR":
                _failed_action = ""
                _notice("Operation completed.")
            return {"FINISHED"}
        except Exception as exc:
            _failed_action = self.bl_idname
            _error(exc)
            self.report({"ERROR"}, _message_text(_message))
            return {"CANCELLED"}


class THEME_STUDIO_OT_start(_SessionAction, bpy.types.Operator):
    bl_translation_context = "Theme Studio"
    bl_idname = "theme_studio.start"
    bl_label = "Start editing"
    bl_description = "Create a reversible copy with text shadows disabled. Other theme values stay unchanged."

    def execute(self, context):
        global _start_failed
        try:
            self.run(context)
            _start_failed = False
            return {"FINISHED"}
        except Exception as exc:
            _start_failed = True
            message = ("Could not create the initial copy. Restore remains available in Theme Studio."
                       if get_session() is not None else
                       "Could not create the initial copy. The theme was not changed.")
            _notice(message, "ERROR", (str(exc),))
            traceback.print_exc()
            self.report({"ERROR"}, _message_text(_message))
            return {"CANCELLED"}

    @classmethod
    def poll(cls, _context):
        return _registry is not None and get_session() is None and not _recovery_path

    def run(self, context):
        global _session, _journal_path, _preview_values, _comparing, _completion, _file_notice, _save_pending
        global _session_theme_path, _theme_source_origin
        registry = get_registry()
        backend = BlenderBackend(registry)
        if _storage_override is not None:
            directory = _storage_override
            directory.mkdir(parents=True, exist_ok=True)
        else:
            directory_name = bpy.utils.user_resource("CONFIG", path="theme-studio", create=True)
            if not directory_name:
                raise OSError("User storage is unavailable; no session was started")
            directory = Path(directory_name)
        journal = directory / f"recovery-{uuid.uuid4().hex}.json"
        _reset_theme_status()
        _theme_source_origin = _capture_theme_origin(context)
        session = Session(registry, backend, journal)
        _session = session
        _session_theme_path = _theme_source_origin["path"] or getattr(
            context.preferences.themes[0], "filepath", "")
        _preview_values, _comparing = {p: copy.deepcopy(v) for p, v in _session.initial.items()
                                      if p in registry.editable_paths}, False
        _completion, _file_notice, _save_pending = "Current theme", "", False
        _journal_path = str(journal)
        try:
            if _stage_new_copy_text_shadows(session.draft):
                session.preview()
                _preview_values = {p: copy.deepcopy(backend.read(p)) for p in registry.editable_paths}
        except Exception:
            try:
                _close_session("cancel")
            except Exception as rollback_error:
                raise RuntimeError("Text-shadow defaults failed and initial-copy restore needs recovery") from rollback_error
            raise
        state = context.window_manager.theme_studio_ui
        state.palette_focus = ""
        state.show_details = state.picker_active
        state.workspace_page = "details" if state.picker_active else "theme"
        if _detail_items and not state.picker_active:
            state.detail_category = _detail_items[0][0]
        _detail_changed(state, context)
        _notice("")  # The persistent state reports the new copy's text-shadow changes.


class THEME_STUDIO_OT_preview(_SessionAction, bpy.types.Operator):
    bl_translation_context = "Theme Studio"
    bl_idname = "theme_studio.preview"
    bl_label = "Apply Changes"
    bl_description = "Reversibly apply the copy to Blender's global theme"

    @classmethod
    def poll(cls, _context):
        session = get_session()
        return session is not None and not session.faulted and _comparing

    def run(self, _context):
        session = _require_session()
        if not _comparing:
            raise RuntimeError(iface("There is no comparison to close."))
        _restore_draft(session)


class THEME_STUDIO_OT_previous(_SessionAction, bpy.types.Operator):
    bl_translation_context = "Theme Studio"
    bl_idname = "theme_studio.previous"
    bl_label = "Compare with Start"
    bl_description = "Show the initial theme without losing live changes"

    def run(self, _context):
        global _comparing, _preview_values
        session = _require_session()
        if not _theme_changed(session):
            raise RuntimeError(iface("There are no live changes to compare."))
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
            _report("Comparison blocked.", report)
            return
        _comparing = True
        if live_values is not None:
            _preview_values = live_values
        _report("Comparison: initial theme. Live changes are not saved.", report)


class THEME_STUDIO_OT_cancel(_SessionAction, bpy.types.Operator):
    bl_translation_context = "Theme Studio"
    _operator_id = "theme_studio.cancel"
    bl_idname = "theme_studio.cancel"
    bl_label = "Discard changes…"
    bl_description = "Restore the initial theme, preserve external changes, and close work. Retry after errors."
    _discard_pending_colors = True

    @classmethod
    def poll(cls, _context):
        return get_session() is not None

    def invoke(self, context, _event):
        session = get_session()
        if session and (session.faulted or not _theme_changed_or_pending(session)):
            return self.execute(context)
        return context.window_manager.invoke_props_dialog(self, width=440)

    def draw(self, _context):
        _wrapped(self.layout, "Restore initial values for fields still owned by this session. "
                  "External changes are preserved and reported. This closes the session; save a theme copy first to keep it.", width=440)

    def run(self, _context):
        _close_session("cancel")


class THEME_STUDIO_OT_confirm(_SessionAction, bpy.types.Operator):
    bl_translation_context = "Theme Studio"
    bl_idname = "theme_studio.confirm"
    bl_label = "Use without saving now"
    bl_description = "Keep the live theme and close work; preferences are not saved"

    def invoke(self, context, _event):
        return context.window_manager.invoke_props_dialog(self, width=460)

    def draw(self, _context):
        _wrapped(self.layout, "The theme stays active. If Blender auto-save is enabled, it may be saved later.", width=460)

    def run(self, _context):
        session = _require_session()
        if _comparing:
            raise RuntimeError(iface("Exit comparison before finishing."))
        _close_session("confirm")


def _native_library_choice_items(self, _context):
    options = json.loads(self.library_options or "[]")
    items = [("NONE", iface("Choose an existing library"), "")] + [
        (str(index + 1), name, "") for index, (name, _path) in enumerate(options)]
    return _retain_native_enum_items(("library", self.library_options), items)


def _finish_library_path(operator):
    try:
        libraries = json.loads(operator.library_options or "[]")
        index = int(operator.library_choice) - 1
    except (TypeError, ValueError):
        return ""
    return libraries[index][1] if 0 <= index < len(libraries) else ""


def _finish_native_stem(name):
    return native_themes._normalized(name, native_themes._blender_modules())


def _validate_finish_source(origin):
    if not origin or not origin.get("path"):
        return
    try:
        source = native_themes._canonical(Path(origin["path"]))
        preset = next(((name, native_themes._canonical(Path(path)), owned)
                       for name, path, owned in native_themes.native_theme_presets()
                       if native_themes._canonical(Path(path)) == source), None)
        if preset != (origin["name"], source, origin["user_owned"]):
            raise ValueError("Native theme source changed")
        source_bytes = origin.get("source_bytes")
        if source_bytes is None:
            return
        if not origin["user_owned"]:
            raise ValueError("Native theme source is not user-owned")
        native_themes.validate_native_preset(str(source))
        current = source.read_bytes()
        native_themes.validate_native_preset(str(source))
        if current != source_bytes or source.read_bytes() != current:
            raise ValueError("Native theme source bytes changed")
    except Exception as exc:
        raise RuntimeError(iface("The starting theme changed or is no longer available. Reopen it before saving.")) from exc


def _validate_finish_save(context, name, save_mode, library_path, *, verified_target="",
                          expected_origin=None, expected_session=None):
    session = _require_session()
    if expected_session is not None and session is not expected_session:
        raise RuntimeError(iface("The editing session changed. Reopen Finish before saving."))
    if _comparing:
        raise RuntimeError(iface("Return to live theme before saving."))
    origin = _theme_source_origin
    if expected_origin is not None and origin != expected_origin:
        raise RuntimeError(iface("The starting theme identity changed. Reopen Finish before saving."))
    library_path = _selected_native_library(context, library_path)
    normalized_name = _finish_native_stem(name)
    external = _theme_identity(context, session)["external"]
    update_target = ""
    if save_mode == "UPDATE":
        if _theme_identity_unknown:
            raise RuntimeError(iface("The starting theme cannot be verified for an update."))
        _validate_finish_source(origin)
        if external or not origin or not origin.get("user_owned") or not origin.get("source_bytes"):
            raise RuntimeError(iface("This theme cannot be updated safely. Save as new instead."))
        association = _verify_theme_source_library(context, origin, library_path, external=external)
        if not association or association["library_target"] != verified_target:
            raise RuntimeError(iface("The update destination changed. Choose the library again."))
        if normalized_name.casefold() != association["normalized_name"].casefold():
            raise RuntimeError(iface("Updating keeps the original theme name."))
        update_target = association["library_target"]
    elif save_mode == "NEW":
        if origin and origin.get("name") and normalized_name.casefold() == _finish_native_stem(
                origin["name"]).casefold():
            raise RuntimeError(iface("Choose a different name to save as new."))
    else:
        raise RuntimeError(iface("Choose Update existing theme or Save as new."))
    return {"save_mode": save_mode, "name": name, "normalized_name": normalized_name,
            "library_path": library_path, "update_target": update_target,
            "source_origin": dict(origin) if origin else None, "session": session}


def _validate_finish_save_request(context, request):
    if get_session() is not request["session"]:
        raise RuntimeError(iface("The editing session changed. Reopen Finish before saving."))
    if _theme_source_origin != request["source_origin"]:
        raise RuntimeError(iface("The starting theme origin changed. Reopen Finish before saving."))
    return _validate_finish_save(
        context, request["name"], request["save_mode"], request["library_path"],
        verified_target=request["update_target"], expected_origin=request["source_origin"],
        expected_session=request["session"])


def _finish_save_mode_items(self, _context):
    items = [("NEW", iface("Save as new"), iface("Save a separate theme copy"), 2)]
    if self.update_available:
        items.insert(0, ("UPDATE", iface("Update existing theme"),
                         iface("Replace the verified original theme files after consent"), 1))
    return _retain_native_enum_items(("finish_mode", self.library_options,
                                      self.library_choice, self.verified_update_target,
                                      self.update_available), items)


def _finish_mode_changed(self, _context):
    if self.save_mode == "UPDATE":
        if not self.update_available:
            self.save_mode = "NEW"
        elif _theme_source_origin and _theme_source_origin.get("name"):
            self.name = _theme_source_origin["name"]


def _finish_library_changed(self, context):
    save_mode = self.save_mode
    self.update_available = False
    self.verified_update_target = ""
    session = get_session()
    library_path = _finish_library_path(self)
    if session and library_path and _theme_source_origin:
        external = _theme_identity(context, session)["external"]
        association = _verify_theme_source_library(context, _theme_source_origin, library_path,
                                                   external=external)
        if association:
            self.update_available = True
            self.verified_update_target = association["library_target"]
    if save_mode == "UPDATE" and not self.update_available:
        self.save_mode = "NEW"
        source_name = _theme_source_origin.get("name") if _theme_source_origin else ""
        if source_name and _finish_native_stem(self.name).casefold() == _finish_native_stem(source_name).casefold():
            self.name = source_name + " Copy"


class THEME_STUDIO_OT_finish(_SessionAction, bpy.types.Operator):
    bl_translation_context = "Theme Studio"
    _operator_id = "theme_studio.finish"
    bl_idname = "theme_studio.finish"
    bl_label = "Finish…"
    action: EnumProperty(translation_context=CONTEXT, items=(
        ("SAVE", "", "Save the selected theme and finish editing"),
        ("KEEP", "", "Keep the live theme and finish without saving"),
        ("RETURN_LIVE", "", "Return to live theme without ending the session"),
    ), default="SAVE", options={"SKIP_SAVE"})
    name: StringProperty(name="Theme Name", translation_context=CONTEXT, default="", maxlen=80,
                         options={"SKIP_SAVE"})
    library_options: StringProperty(options={"HIDDEN", "SKIP_SAVE"})
    library_choice: EnumProperty(name="Asset Library", translation_context=CONTEXT,
                                 items=_native_library_choice_items, update=_finish_library_changed,
                                 options={"SKIP_SAVE"})
    save_mode: EnumProperty(name="Save mode", translation_context=CONTEXT,
                            items=_finish_save_mode_items, update=_finish_mode_changed,
                            options={"SKIP_SAVE"})
    update_available: BoolProperty(options={"HIDDEN", "SKIP_SAVE"})
    verified_update_target: StringProperty(options={"HIDDEN", "SKIP_SAVE"})
    show_other_choices: BoolProperty(default=False, options={"SKIP_SAVE"})

    def invoke(self, context, _event):
        session = _require_session()
        unchanged = not _theme_changed_or_pending(session) and not _comparing
        self.action = "RETURN_LIVE" if _comparing else "KEEP" if unchanged else "SAVE"
        source_name = (_theme_source_origin["name"] if _theme_source_origin and
                       _theme_source_origin.get("name") else "")
        self.name = source_name or context.window_manager.theme_studio_ui.profile_name
        libraries = native_themes.configured_libraries(context)
        self.library_options = json.dumps(libraries)
        self.update_available = False
        self.verified_update_target = ""
        self.save_mode = "NEW"
        self.library_choice = "NONE"
        associated_library = _theme_source_origin.get("library_path", "") if _theme_source_origin else ""
        if associated_library:
            selected = next((str(index + 1) for index, (_name, path) in enumerate(libraries)
                             if native_themes._canonical(Path(path)) ==
                             native_themes._canonical(Path(associated_library))), "NONE")
            if selected != "NONE":
                self.library_choice = selected
        if self.update_available:
            self.save_mode = "UPDATE"
        elif source_name and _finish_native_stem(self.name).casefold() == _finish_native_stem(source_name).casefold():
            self.name = source_name + " Copy"
        confirm_text = ("Return to live theme" if _comparing else
                        "Close without changes" if unchanged else "Save and finish")
        return context.window_manager.invoke_props_dialog(self, width=620, confirm_text=iface(confirm_text))

    def draw(self, context):
        layout = self.layout
        layout.operator_context = "EXEC_DEFAULT"
        session = get_session()
        if session is None:
            layout.label(text=session_status(), icon="CHECKMARK", text_ctxt=CONTEXT)
            _wrapped(layout, "Editing session is closed. You can close this dialog.", width=480)
            return
        unchanged = not _theme_changed_or_pending(session) and not _comparing
        if unchanged:
            layout.label(text=iface("No theme changes to save."), icon="INFO", text_ctxt=CONTEXT)
            _wrapped(layout, "Close without changes ends this editing session. The theme stays unchanged.", width=620)
            return
        if _comparing:
            _wrapped(layout, "Comparison is active. Return to live changes before finishing.", width=480)
            return
        if self.update_available:
            layout.prop(self, "save_mode", expand=True)
        layout.prop(self, "library_choice", text=iface("Save location"))
        library_path = _finish_library_path(self)
        if not library_path:
            _wrapped(layout, "Choose a save location. Selecting the library with the verified original theme enables Update existing.", width=620)
        elif not self.update_available:
            _wrapped(layout, "This theme will be saved as a new copy.", width=620)
            _wrapped(layout, "Choose its original library to enable Update existing, if Theme Studio can verify it.", width=620)
        if self.save_mode == "UPDATE":
            layout.label(text=iface("Theme name: {name}").format(name=_theme_source_origin["name"]))
        else:
            layout.prop(self, "name")
        if library_path:
            _wrapped(layout, "Saving this theme ends editing. Blender preferences are not saved.", width=620)
        if session.original_auto_save:
            _wrapped(layout, "Blender auto-save may save preferences later.", width=620)

        disclosure = layout.row(align=True)
        disclosure.prop(self, "show_other_choices", text=iface("Other finish choices"),
                        icon="TRIA_DOWN" if self.show_other_choices else "TRIA_RIGHT", emboss=False)
        if self.show_other_choices:
            keep = layout.operator("theme_studio.finish", text=iface("Keep live theme and finish without saving"), icon="CHECKMARK")
            keep.action = "KEEP"
            if not unchanged:
                layout.operator_context = "INVOKE_DEFAULT"
                layout.operator("theme_studio.cancel", text=iface("Restore starting theme and discard changes"), icon="CANCEL")

    def run(self, _context):
        session = _require_session()
        if self.action == "RETURN_LIVE":
            _restore_draft(session)
            return
        if _comparing:
            raise RuntimeError(iface("Exit comparison before finishing."))
        if self.action == "KEEP" or not _theme_changed_or_pending(session):
            _close_session("confirm")
            return
        if self.action == "SAVE":
            library_path = _finish_library_path(self)
            if not library_path:
                raise RuntimeError(iface("Select an existing asset library in Theme Studio add-on preferences."))
            request = _validate_finish_save(
                _context, self.name, self.save_mode, library_path,
                verified_target=self.verified_update_target)
            _begin_native_theme_save(_context, self.name, library_path, finish_request=request)
        else:
            raise RuntimeError(iface("Choose a Finish action."))


def _save_preferences_verified():
    # Verify Blender's result and the actual preferences file, not a static notice.
    path = Path(bpy.utils.user_resource("CONFIG")) / "userpref.blend"
    result = bpy.ops.wm.save_userpref()
    verify_saved_preferences(result, path)


class THEME_STUDIO_OT_save_preferences(bpy.types.Operator):
    bl_translation_context = "Theme Studio"
    bl_idname = "theme_studio.save_preferences"
    bl_label = "Save all preferences…"
    consent: BoolProperty(translation_context=CONTEXT, default=False, options={"SKIP_SAVE"})

    @classmethod
    def poll(cls, _context):
        session = get_session()
        if session is None:
            return _save_pending
        return not session.faulted and _theme_changed_or_pending(session) and not _comparing

    def invoke(self, context, _event):
        self.consent = True
        return context.window_manager.invoke_props_dialog(self, width=460, confirm_text=iface("Save all preferences…"))

    def draw(self, _context):
        _wrapped(self.layout, "Blender will save all current preferences, not only the theme.", width=460)

    def execute(self, _context):
        global _save_pending, _completion
        try:
            if _recovery_blocked or _recovery_path:
                raise RuntimeError(iface("Repair the journal manually before retrying."))
            if not self.consent:
                raise RuntimeError(iface("Consent is required to save all preferences."))
            if get_session() is not None:
                if not _flush_colors():
                    raise RuntimeError(iface("Pending changes: resolve conflict before saving."))
                if not _theme_changed(_require_session()):
                    raise RuntimeError(iface("There are no theme changes to save."))
                THEME_STUDIO_OT_confirm.run(self, _context)
            elif not _save_pending:
                raise RuntimeError(iface("There is no save to retry."))
            _save_pending = True
            _save_preferences_verified()
            _save_pending = False
            _completion = "Preferences saved"
            _notice("Preferences saved. This saves all Blender preferences.")
            return {"FINISHED"}
        except Exception as exc:
            _error(exc)
            self.report({"ERROR"}, _message_text(_message))
            return {"CANCELLED"}


class THEME_STUDIO_OT_undo(_SessionAction, bpy.types.Operator):
    bl_translation_context = "Theme Studio"
    bl_idname = "theme_studio.undo"
    bl_label = "Undo Change"
    bl_description = "Reversibly undo the last live change"

    def run(self, context):
        session = _require_session()
        _restore_draft(session)
        old_draft = copy.deepcopy(session.draft)
        changed = session.draft.undo()
        if changed:
            try:
                _apply_live_edit("Change undone.")
            except Exception:
                session.draft = old_draft
                raise
        if not changed:
            _edit_notice("No change to undo.")


class THEME_STUDIO_OT_redo(_SessionAction, bpy.types.Operator):
    bl_translation_context = "Theme Studio"
    bl_idname = "theme_studio.redo"
    bl_label = "Redo Change"

    def run(self, context):
        session = _require_session()
        _restore_draft(session)
        old_draft = copy.deepcopy(session.draft)
        changed = session.draft.redo()
        if changed:
            try:
                _apply_live_edit("Change redone.")
            except Exception:
                session.draft.__dict__.clear()
                session.draft.__dict__.update(old_draft.__dict__)
                raise
        if not changed:
            _edit_notice("No change to redo.")


class THEME_STUDIO_OT_common_value(_SessionAction, bpy.types.Operator):
    bl_translation_context = "Theme Studio"
    bl_idname = "theme_studio.common_value"
    bl_label = "Edit Color…"
    bl_description = "Reversibly edit one live field"
    path: StringProperty(translation_context=CONTEXT, options={"SKIP_SAVE"})
    opacity: BoolProperty(translation_context=CONTEXT, options={"SKIP_SAVE"})
    color: FloatVectorProperty(name="Color", translation_context=CONTEXT, size=3, subtype="COLOR_GAMMA", min=0, max=1, default=(0.5, 0.5, 0.5))
    linear_color: FloatVectorProperty(name="Color", translation_context=CONTEXT, size=3, subtype="COLOR", min=0, max=1)
    alpha: FloatProperty(name="Alpha", translation_context=CONTEXT, min=0, max=100, default=100, subtype="PERCENTAGE")

    def invoke(self, context, _event):
        value = _require_session().draft.value(self.path)
        self.color, self.linear_color = value[:3], value[:3]
        self.alpha = value[3] * 100 if len(value) == 4 else 100
        return context.window_manager.invoke_props_dialog(self, width=460,
            confirm_text=iface("Use This Alpha") if self.opacity else iface("Use This Color"))

    def draw(self, _context):
        layout = self.layout
        _wrapped(layout, iface("{field} · {owner}").format(field=_label(self.path), owner=_owner_display_label(self.path)), width=460)
        _wrapped(layout, "Edit separately: this field will not follow group changes.", width=460)
        _wrapped(layout, "Initial live value: current alpha." if self.opacity else
                 "Initial live value: current color.", width=460)
        attr = "alpha" if self.opacity else "linear_color" if self.path and get_registry().fields[self.path].subtype == "COLOR" else "color"
        if not self.opacity:
            layout.template_color_picker(self, attr, value_slider=True)
        layout.prop(self, attr)
        _wrapped(layout, "RGB stays unchanged." if self.opacity else "Each item's alpha stays unchanged.", width=460)
        _wrapped(layout, "Cancel or Esc closes without changing the theme.", width=460)

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
            _apply_live_edit("Color updated · 1 item. Edit separately.")
        except Exception:
            session.draft = old_draft
            raise


class THEME_STUDIO_OT_protect_field(_SessionAction, bpy.types.Operator):
    bl_translation_context = "Theme Studio"
    bl_idname = "theme_studio.protect_field"
    bl_label = "Edit Separately / Include"
    bl_description = "An excluded field does not follow groups. Including it does not change its value immediately."
    path: StringProperty(translation_context=CONTEXT, options={"SKIP_SAVE"})
    enabled: BoolProperty(translation_context=CONTEXT, options={"SKIP_SAVE"})

    def run(self, _context):
        _require_session().draft.protect(self.path, self.enabled)
        _edit_notice("Editing separately: this field will not follow future common changes." if self.enabled else "Included in future common changes. Current value is unchanged.")


class THEME_STUDIO_OT_reset_field(_SessionAction, bpy.types.Operator):
    bl_translation_context = "Theme Studio"
    bl_idname = "theme_studio.reset_field"
    bl_label = "Restore Initial Value"
    bl_description = "Restore the session's initial live value and exclude it from groups"
    path: StringProperty(translation_context=CONTEXT, options={"SKIP_SAVE"})

    def run(self, _context):
        session = _require_session()
        _restore_draft(session)
        old_draft = copy.deepcopy(session.draft)
        session.draft.set(self.path, session.initial[self.path])
        try:
            _apply_live_edit("Initial value restored. Edit separately.")
        except Exception:
            session.draft.__dict__.clear()
            session.draft.__dict__.update(old_draft.__dict__)
            raise


class THEME_STUDIO_OT_page(bpy.types.Operator):
    bl_translation_context = "Theme Studio"
    bl_idname = "theme_studio.page"
    bl_label = "Change Page"
    bl_translation_context = "Theme Studio"
    target: IntProperty(translation_context=CONTEXT, min=0, options={"SKIP_SAVE"})
    issues: BoolProperty(translation_context=CONTEXT, options={"SKIP_SAVE"})
    contrast: BoolProperty(translation_context=CONTEXT, options={"SKIP_SAVE"})

    def execute(self, context):
        state = context.window_manager.theme_studio_ui
        setattr(state, "contrast_page" if self.contrast else "issue_page" if self.issues else "page", self.target)
        _redraw()
        return {"FINISHED"}


class THEME_STUDIO_OT_copy_report(bpy.types.Operator):
    bl_translation_context = "Theme Studio"
    bl_idname = "theme_studio.copy_report"
    bl_label = "Copy Result Details"
    bl_description = "Copy full message and all conflicts/errors to clipboard"

    @classmethod
    def description(cls, _context, _properties):
        return "\n".join(filter(None, (_message_text(_message), f"Journal: {_journal_path}" if _journal_path else "",
                                       cls.bl_description)))

    def execute(self, context):
        context.window_manager.clipboard = "\n".join((_message_text(_message), f"Journal: {_journal_path}", *_issues))
        self.report({"INFO"}, iface("Result copied."))
        return {"FINISHED"}


class THEME_STUDIO_OT_save_profile(_SessionAction, bpy.types.Operator, ExportHelper):
    bl_translation_context = "Theme Studio"
    bl_idname = "theme_studio.save_profile"
    bl_label = "Save Theme Studio Project…"
    bl_description = "Save this editable project as a JSON file"
    filename_ext = ".json"
    filter_glob: StringProperty(translation_context=CONTEXT, default="*.json", options={"HIDDEN"})
    profile_name: StringProperty(name="Project Name", translation_context=CONTEXT, default="My Theme", maxlen=80)
    overwrite: BoolProperty(name="Allow File Replacement", translation_context=CONTEXT, default=False,
                            description="Explicit consent. Existing files are not replaced by default.")

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
        self.layout.prop(self, "profile_name", text_ctxt=CONTEXT)
        self.layout.prop(self, "overwrite", text_ctxt=CONTEXT)
        _wrapped(self.layout, "Save a project file you can edit later. This does not save a Blender theme or end editing.")

    def run(self, context):
        global _file_notice
        session = _require_session(allow_faulted=True)
        if not self.filepath:
            raise ValueError("Choose a JSON file")
        path = Path(bpy.path.ensure_ext(self.filepath, self.filename_ext))
        if path.resolve() == session.recovery_path.resolve() or (path.exists() and path.samefile(session.recovery_path)):
            raise ValueError("This file is reserved for the initial-copy recovery journal. Choose another theme file.")
        try:
            save_profile(path, session.draft.profile(self.profile_name), get_registry(), overwrite=self.overwrite)
        except FileExistsError as exc:
            raise ValueError("File already exists. Choose another name or explicitly allow replacement in the file browser.") from exc
        context.window_manager.theme_studio_ui.profile_name = self.profile_name
        _file_notice = "Theme copy saved to file"
        _edit_notice("Theme copy saved to file. Active theme and preferences were not changed.")


class THEME_STUDIO_OT_load_profile(_SessionAction, bpy.types.Operator, ImportHelper):
    bl_translation_context = "Theme Studio"
    bl_idname = "theme_studio.load_profile"
    bl_label = "Load Theme Studio Project…"
    bl_description = "Load an editable Theme Studio project"
    filter_glob: StringProperty(translation_context=CONTEXT, default="*.json", options={"HIDDEN"})
    replace_draft: BoolProperty(name="Replace Copy Changes", translation_context=CONTEXT, default=False)

    @classmethod
    def poll(cls, _context):
        return _registry is not None and not _recovery_path and (get_session() is None or not get_session().faulted)

    def invoke(self, context, _event):
        self.replace_draft = False
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def draw(self, _context):
        self.layout.prop(self, "replace_draft")
        _wrapped(self.layout, "Load a saved project file. Save, discard, or cancel current changes when prompted.")

    def run(self, context):
        global _preview_values
        # Validate before starting a session or touching an existing draft.
        profile = load_profile(self.filepath, get_registry())
        if get_session() is None:
            THEME_STUDIO_OT_start.run(self, context)
        session = _require_session()
        if _dirty(session) and not self.replace_draft:
            raise ValueError("The copy contains changes. Save it first or allow replacement in the file browser.")
        _restore_draft(session)
        old_draft = copy.deepcopy(session.draft)
        old_preview_values = _preview_values
        session.draft.replace_profile(profile)
        try:
            _apply_live_edit("Theme loaded.")
        except Exception:
            session.draft.__dict__.clear()
            session.draft.__dict__.update(old_draft.__dict__)
            _preview_values = old_preview_values
            raise
        state = context.window_manager.theme_studio_ui
        state.profile_name = profile.name
        _detail_changed(state, context)
        _edit_notice(("Theme '{name}' is active in Blender. Preferences are not saved.", {"name": profile.name}))


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
    text = _message_text(text)
    for line in _wrap_lines(text, max(20 * scale, width), lambda value: blf.dimensions(0, value)):
        layout.label(text=line, text_ctxt=CONTEXT, translate=False)


def _pager(layout, page, pages, *, issues=False, contrast=False):
    row = layout.row(align=True)
    previous = row.row(align=True)
    previous.enabled = page > 0
    op = previous.operator("theme_studio.page", text="", icon="TRIA_LEFT")
    op.target, op.issues, op.contrast = max(0, page - 1), issues, contrast
    row.label(text=f"{page + 1} / {pages}", text_ctxt=CONTEXT)
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
    box.label(text=iface({"ERROR": "Operation Incomplete", "WARNING": "Warning", "INFO": "Result"}[_severity]),
              icon={"ERROR": "ERROR", "WARNING": "ERROR", "INFO": "INFO"}[_severity], text_ctxt=CONTEXT)
    # Path lists belong in the paged detail, not in a giant ConflictError label.
    message = _message_text(_message)
    message = message.split(": ", 1)[0] if _issues and len(message) > 300 else message
    _wrapped(box, message)
    if _issues:
        box.prop(state, "show_issue_details", text="Result Details", text_ctxt=CONTEXT,
                 icon="TRIA_DOWN" if state.show_issue_details else "TRIA_RIGHT", emboss=False)
    if _issues and state.show_issue_details:
        pages = max(1, math.ceil(len(_issues) / ISSUE_PAGE_SIZE))
        page = min(state.issue_page, pages - 1)
        box.label(text=iface("Details: {count}").format(count=len(_issues)), text_ctxt=CONTEXT)
        for issue in _issues[page * ISSUE_PAGE_SIZE:(page + 1) * ISSUE_PAGE_SIZE]:
            _wrapped(box, str(issue))
        _pager(box, page, pages, issues=True)
    if _severity != "INFO":
        box.operator("theme_studio.copy_report", text=iface("Copy Result Details"), icon="COPYDOWN")


def _draw_field(layout, state, session, draft_rna, path, *, context_label=False, reset=False,
                inclusion=None, group_id=""):
    spec = get_registry().fields[path]
    protected = path in session.draft.protected
    column = layout.column(align=True)
    if context_label:
        column.label(text=_owner_display_label(path), text_ctxt=CONTEXT)
    color = draft_color_attribute(path)
    row = column.row(align=True)
    if color:
        row.prop(draft_rna, color, text=_label(path), text_ctxt=CONTEXT, translate=False)
    else:
        row.prop(draft_rna, draft_attribute(path), text=_label(path), text_ctxt=CONTEXT, translate=False)
    if context_label or reset:
        op = row.operator("theme_studio.reset_field", text="", icon="LOOP_BACK")
        op.path = path
    if inclusion is not None:
        _draw_inclusion(row, inclusion, group_id)
    if not context_label and not reset:
        grouped = path in _roundness_paths or any(path in paths for paths in get_registry().recipes.values())
        if grouped:
            _wrapped(column, iface("Edit separately") if protected else iface("Follow common changes"))
    layout.separator(factor=0.25)


class THEME_STUDIO_UL_fields(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index=0, flt_flag=0):
        row = layout.row(align=True)
        row.label(text=item.label)
        grouped = item.path in _roundness_paths or any(item.path in paths for paths in get_registry().recipes.values())
        row.label(text="Separate" if not item.included else "Common" if grouped else "Individual", text_ctxt=CONTEXT)
        attr = draft_color_attribute(item.path)
        if attr:
            swatch = row.row()
            swatch.enabled = False
            swatch.prop(context.window_manager.theme_studio_draft, attr, text="")


def _draw_palette(layout, state, session):
    layout.label(text="Main Colors", icon="COLOR", text_ctxt=CONTEXT)
    grid = layout.grid_flow(row_major=True, columns=0, even_columns=True, even_rows=False, align=True)
    for group in _palette_map:
        section = grid.box()
        row = section.row(align=True)
        row.label(text=_PALETTE_LABELS.get(group["id"], group["label"]), text_ctxt=CONTEXT)
        protected = sum(path in session.draft.protected for path in group["paths"])
        if protected:
            row.label(text=iface("{count} excluded").format(count=protected), icon="DECORATE", text_ctxt=CONTEXT)
        op = row.operator("theme_studio.palette_details", text="Details", icon="PREFERENCES", text_ctxt=CONTEXT)
        op.group_id = group["id"]
        swatch = section.row()
        swatch.scale_y = 1.5 if group["id"] == "borders" else 1.2
        attr = _palette_keys[group["id"]]
        swatch.prop(bpy.context.window_manager.theme_studio_palette, attr, text="")
        if any(get_registry().fields[path].length == 4 for path in group["paths"]):
            opacities = [session.draft.value(path)[3] for path in _linked_rgba_paths(group["paths"], session.draft)]
            if opacities and max(opacities) - min(opacities) > 1e-6:
                section.label(text="Different Alpha Values", icon="INFO", text_ctxt=CONTEXT)
    _draw_roundness(layout, state, session)


def _draw_roundness(layout, state, session):
    if not _roundness_paths:
        return
    box = layout.box()
    box.label(text="Control Shape", icon="MOD_UVPROJECT", text_ctxt=CONTEXT)
    row = box.row(align=True)
    row.prop(bpy.context.window_manager.theme_studio_palette, "roundness_common", text="Roundness", text_ctxt=CONTEXT)
    exceptions = sum(path in session.draft.protected for path in _roundness_paths)
    if exceptions:
        row.label(text=iface("{count} excluded").format(count=exceptions), icon="DECORATE", text_ctxt=CONTEXT)
    values = {session.draft.value(path) for path in _roundness_paths}
    if len(values) > 1:
        box.label(text=iface("Initial values differ; the slider makes them uniform."), icon="INFO", text_ctxt=CONTEXT)
def _draw_viewport(layout, state, session, draft_rna):
    group = _viewport_group
    if group is None:
        return
    registry = get_registry()
    enum_path = next((path for path in registry.editable_paths
                      if path.endswith("view_3d.space.gradients.background_type")), None)
    if enum_path:
        background = layout.box()
        background.label(text="Background · Global Theme", icon="WORLD", text_ctxt=CONTEXT)
        background.prop(draft_rna, draft_attribute(enum_path), text="Type", expand=True, text_ctxt=CONTEXT)
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
        box.label(text=section["label"], text_ctxt=CONTEXT)
        for suffix in suffixes:
            path = next((path for path in section["paths"] if path.endswith(suffix)), None)
            if path:
                _draw_field(box, state, session, draft_rna, path)
    more = layout.operator("theme_studio.palette_details", text="More Colors and Guides", icon="PREFERENCES", text_ctxt=CONTEXT)
    more.group_id = "viewport"


def _draw_contrast(layout, state, session):
    results = analyze_contrast(get_registry(), session.draft.values)
    warnings = [item for item in results if item["below_threshold"] is True]
    if warnings:
        layout.label(text=iface("Some colors may have low contrast."), icon="INFO", text_ctxt=CONTEXT)


def _detail_group_label(group):
    category, subgroup = group.split(".", 1)
    return _DETAIL_GROUP_LABELS.get(subgroup, _DETAIL_LABELS.get(category, "Additional Controls"))


def _draw_detail_fields(layout, state, session, draft_rna, fields):
    groups = {}
    for item in fields:
        groups.setdefault(get_registry().fields[item.path].group, []).append(item)
    for group, items in groups.items():
        header, body = layout.panel(f"theme_studio_detail_{group}", default_closed=True)
        header.label(text=_detail_group_label(group), text_ctxt=CONTEXT)
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
            heading.label(text=group["label"], text_ctxt=CONTEXT)
            heading.operator("theme_studio.palette_details", text="All Categories", icon="BACK", text_ctxt=CONTEXT).all_controls = True
        else:
            group = next((item for item in _palette_map if item["id"] == state.palette_focus), None)
            if group is None:
                return
            heading = box.row(align=True)
            heading.label(text=_PALETTE_LABELS.get(group["id"], group["label"]), text_ctxt=CONTEXT)
            heading.operator("theme_studio.palette_details", text="All Categories", icon="BACK", text_ctxt=CONTEXT).all_controls = True
    else:
        box.prop(state, "detail_category", text="Category", text_ctxt=CONTEXT)
        category = next((item for item in _detail_map if item["id"] == state.detail_category), None)
        if category is None:
            return
    if _detail_context_items:
        box.prop(state, "detail_context", text="Context", text_ctxt=CONTEXT)
    if not state.detail_fields:
        return
    _draw_detail_fields(layout, state, session, draft_rna, state.detail_fields)


def _draw_disclosure(layout, state, property_name, label):
    row = layout.row(align=True)
    expanded = getattr(state, property_name)
    row.prop(state, property_name, text=label, text_ctxt=CONTEXT, icon="TRIA_DOWN" if expanded else "TRIA_RIGHT", emboss=False)
    return layout.column(align=True) if expanded else None


def _draw_safety(layout, width=550):
    _wrapped(layout, "Theme changes are reversible and do not save Blender preferences.", width=width)
    _wrapped(layout, "If Blender closed during editing, resolve recovery before continuing.", width=width)
    state = bpy.context.window_manager.theme_studio_ui
    details = _draw_disclosure(layout, state, "show_safety_details", iface("Editing Details"))
    if details:
        _wrapped(details, iface("Recovery journal: {path}").format(path=_journal_path or "unavailable"), width=width)
        if _message:
            _wrapped(details, _message, width=width)
        _wrapped(details, "Compare shows the initial theme. Discard Changes attempts restoration and reports conflicts. Do not use Ctrl+Z.", width=width)
        _wrapped(details, "External manual saves can make live changes permanent. Color and alpha share a picker.", width=width)
        _wrapped(details, "Disabling the add-on and changing files attempt restoration. If restoration fails, the session remains available for retry.", width=width)
    if get_session() is None and _journal_path:
        layout.operator_context = "INVOKE_DEFAULT"
        layout.operator("theme_studio.reopen_initial", icon="DUPLICATE")
        _wrapped(layout, "Reopen initial values as live changes. To recover an interrupted session, use controls above.", width=width)


class THEME_STUDIO_OT_reopen_initial(_SessionAction, bpy.types.Operator):
    bl_translation_context = "Theme Studio"
    bl_idname = "theme_studio.reopen_initial"
    bl_label = "Reopen Initial Copy…"
    bl_description = "Reversibly restore initial values from the last editing session"

    @classmethod
    def poll(cls, _context):
        return _registry is not None and not _recovery_path and get_session() is None and bool(_journal_path)

    def invoke(self, context, _event):
        return context.window_manager.invoke_props_dialog(self, width=460, confirm_text="Reopen in Copy")

    def draw(self, _context):
        _wrapped(self.layout, iface("Restore the last session's initial values live. You can compare or discard them."), width=460)

    def run(self, context):
        global _preview_values
        document = read_document(_journal_path)
        registry = get_registry()
        if (document.get("format") != "theme-studio-recovery" or document.get("schema_version") != 1
                or document.get("build_hash") != registry.build_hash):
            raise ValueError("Initial copy is not compatible with this Blender version.")
        values = registry.validate(document.get("initial", {}), complete=True, allow_metadata=True)
        initial = {p: values[p] for p in registry.editable_paths}
        THEME_STUDIO_OT_start.run(self, context)
        session = _require_session()
        draft = session.draft
        previous_draft = copy.deepcopy(draft)
        draft.replace_profile(Profile("Initial Copy", initial))
        try:
            _apply_live_edit("Initial copy reopened.")
        except Exception:
            session.draft = previous_draft
            _close_session("cancel")
            raise


class THEME_STUDIO_OT_recovery_choice(bpy.types.Operator):
    bl_translation_context = "Theme Studio"
    bl_idname = "theme_studio.recovery_choice"
    bl_label = "Choose Field Recovery"
    path: StringProperty(translation_context=CONTEXT, options={"SKIP_SAVE"})
    choice: EnumProperty(items=(("keep", "Keep Current Value", ""), ("restore", "Restore Initial Value", "")), options={"SKIP_SAVE"}, translation_context=CONTEXT)

    def execute(self, _context):
        global _recovery_error, _recovery_detail
        if _recovery_blocked or _recovery_document is None:
            self.report({"ERROR"}, iface("Repair the journal manually before choosing."))
            return {"CANCELLED"}
        _recovery_decisions[self.path] = self.choice
        _recovery_error, _recovery_detail = "", ""
        _redraw()
        return {"FINISHED"}


class THEME_STUDIO_OT_retry_recovery_discovery(bpy.types.Operator):
    bl_translation_context = "Theme Studio"
    bl_idname = "theme_studio.retry_recovery_discovery"
    bl_label = "Retry Recovery Scan"

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
            _recovery_error = iface("Recovery folder is unavailable; no journal was changed.")
        _redraw()
        return {"FINISHED"}


class THEME_STUDIO_OT_archive_recovery(bpy.types.Operator):
    bl_translation_context = "Theme Studio"
    bl_idname = "theme_studio.archive_recovery"
    bl_label = "Archive Recovery Data…"
    snapshot: StringProperty(translation_context=CONTEXT, options={"SKIP_SAVE"})

    @classmethod
    def poll(cls, _context):
        return bool(_recovery_records) and get_session() is None

    def invoke(self, context, _event):
        self.snapshot = json.dumps({"filenames": _recovery_filenames, "records": _recovery_records})
        return context.window_manager.invoke_props_dialog(self, width=560, confirm_text="Archive Data")

    def draw(self, _context):
        _wrapped(self.layout, iface("Create an archive copy of recovery data. Originals stay in place; current theme does not change."), width=560)
        _wrapped(self.layout, "This action does NOT restore initial values. The archived copy is preserved.", width=560)

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
                raise RuntimeError(iface("Archiving is unavailable during a live session."))
            snapshot = json.loads(self.snapshot)
            paths = sorted(directory.glob("recovery-*.json"))
            if tuple(path.name for path in paths) != tuple(snapshot["filenames"]):
                raise RuntimeError(iface("Recovery files changed. Scan again before archiving."))
            records = {item["path"]: item["digest"] for item in snapshot["records"]}
            if set(records) != {item["path"] for item in _recovery_records}:
                raise RuntimeError(iface("Recovery list changed. Scan again before archiving."))
            for path in paths:
                if str(path) in records:
                    archive_recovery(path, records[str(path)])
            self.report({"INFO"}, iface("Data archived; current theme was not changed."))
        except Exception as exc:
            failure = str(exc)
        try:
            if directory is not None:
                _discover_recovery(directory)
        except Exception as exc:
            failure = "\n".join(filter(None, (failure, iface("Recovery rescan failed: {detail}").format(detail=exc))))
        if failure:
            _recovery_error = iface("Archiving did not complete. Theme was not restored; recovery remains blocked.")
            attempted = ", ".join(item.get("path", "") for item in snapshot.get("records", ()) if item.get("path"))
            archive_location = iface("Archive: {path}").format(path=directory / "archive") if directory is not None else ""
            _recovery_detail = "\n".join(filter(None, (attempted, archive_location, failure)))
            _recovery_blocked = True
            _recovery_document, _recovery_plan = None, None
            if not _recovery_path:
                _recovery_path = next((item.get("path", "") for item in snapshot.get("records", ())
                                       if item.get("path")), "archivio")
        elif not _recovery_records:
            self.report({"INFO"}, iface("Copy archived; originals remain in place. Current theme was not restored."))
        _redraw()
        return {"FINISHED"}


class THEME_STUDIO_OT_recovery(bpy.types.Operator):
    bl_translation_context = "Theme Studio"
    bl_idname = "theme_studio.recovery"
    bl_label = "Resolve Recovery"
    outcome: EnumProperty(items=(("restore", "Restore Initial Theme", ""), ("keep", "Keep Current Theme", "")), options={"SKIP_SAVE"}, translation_context=CONTEXT)

    def execute(self, _context):
        global _recovery_error, _recovery_detail, _recovery_progress, _recovery_path, _recovery_document, _recovery_plan
        try:
            if _recovery_blocked or _recovery_document is None:
                raise RuntimeError(iface("Repair the journal manually before retrying."))
            decisions = dict(_recovery_decisions)
            if self.outcome == "keep":
                journal = parse_recovery(read_document(_recovery_path), get_registry())
                if any(choice == "restore" for choice in journal["decisions"].values()):
                    raise RuntimeError(iface("Journal already contains restore choices. Retry Restore Initial Theme; you cannot switch to Keep Current Theme."))
                paths = set(journal["owned"]) | set(journal["pending"]) | set(journal["conflicts"])
                decisions = {path: "keep" for path in paths}
            else:
                conflicts = {item.path for item in (_recovery_plan.conflicts if _recovery_plan else ())}
                missing = conflicts - set(decisions)
                if missing:
                    raise ValueError(iface("Choose an outcome for each conflict ({count} remain).").format(count=len(missing)))
            result = execute_recovery(get_registry(), BlenderBackend(get_registry()), _recovery_path,
                                      decisions, outcome="cancelled" if self.outcome == "restore" else "confirmed")
            _recovery_progress = iface("Fields resolved: {count}").format(count=len(result.settled))
            if result.completed:
                _recovery_path, _recovery_document, _recovery_plan = "", None, None
                _recovery_decisions.clear()
                _recovery_error, _recovery_detail = "", ""
            else:
                _recovery_error = iface("Recovery incomplete. Journal is preserved; retry.")
        except Exception as exc:
            _recovery_error = iface("Recovery did not complete. Data remains preserved.")
            _recovery_detail = str(exc)
            _recovery_progress = iface("Recovery incomplete · journal preserved")
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
            _recovery_error = iface("There are {count} recovery items to review. No files were changed.").format(count=len(unresolved))
        elif unresolved:
            statuses = {"incompatible": iface("This copy is from another Blender version."),
                        "invalid": iface("The recovery file cannot be read or is invalid.")}
            _recovery_error = statuses.get(unresolved[0]["status"], iface("Recovery requires review."))
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
        _recovery_error = iface("Recovery cannot be opened safely.")
        _recovery_detail = str(exc)


def _draw_recovery(layout):
    box = layout.box()
    box.alert = _recovery_blocked or bool(_recovery_error)
    box.label(text=iface("Resolve recovery first"), icon="ERROR" if _recovery_blocked or _recovery_error else "RECOVER_LAST", text_ctxt=CONTEXT)
    status = _recovery_error or _recovery_progress or iface("Choose what to do with values changed before the interruption.")
    _wrapped(box, status)
    if _recovery_blocked:
        box.operator("theme_studio.retry_recovery_discovery", text="Retry Recovery Scan", icon="FILE_REFRESH", text_ctxt=CONTEXT)
    if _recovery_records and get_session() is None:
        box.operator("theme_studio.archive_recovery", text="Keep data and continue…", icon="FILE_FOLDER")
        _wrapped(box, "Archive files without restoring the theme. You can continue with the current theme after archiving them.")
    if _recovery_plan and not _recovery_blocked:
        for conflict in _recovery_plan.conflicts:
            label_row = box.row()
            label_row.label(text=_label(conflict.path), text_ctxt=CONTEXT)
            explanation = ("You can keep the current value for this preference; restoring its initial value is unavailable."
                           if conflict.path == "preferences.use_preferences_save" else
                           "Choose whether to keep the current value or restore its initial value for this field.")
            _wrapped(box, iface(explanation))
            choices = (("keep", "Keep Current Value"),) if conflict.path == "preferences.use_preferences_save" else (
                ("keep", "Keep Current Value"), ("restore", "Restore Initial Value"))
            for choice, label in choices:
                choice_row = box.row()
                op = choice_row.operator("theme_studio.recovery_choice", text=label, text_ctxt=CONTEXT,
                                         depress=_recovery_decisions.get(conflict.path) == choice)
                op.path, op.choice = conflict.path, choice
    state = bpy.context.window_manager.theme_studio_ui
    details = _draw_disclosure(box, state, "show_recovery_details", iface("Technical Details"))
    if details:
        for record in _recovery_records:
            _wrapped(details, f"{record['path']} · {iface(record['status'])} · SHA-256 {record['digest']}")
        if _recovery_detail:
            _wrapped(details, _recovery_detail)
    if _recovery_plan and not _recovery_blocked:
        _wrapped(box, "Restore applies initial values still owned by this session. Keep leaves current values unchanged.")
        restore = box.row()
        restore.operator("theme_studio.recovery", text="Restore Initial Theme", icon="LOOP_BACK", text_ctxt=CONTEXT).outcome = "restore"
        keep = box.row()
        keep.operator("theme_studio.recovery", text="Keep Current Theme", icon="CHECKMARK", text_ctxt=CONTEXT).outcome = "keep"


class THEME_STUDIO_OT_safety(bpy.types.Operator):
    bl_translation_context = "Theme Studio"
    bl_idname = "theme_studio.safety"
    bl_label = "Initial Copy and Recovery…"

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=550)

    def draw(self, context):
        _draw_safety(self.layout, width=550)

    def execute(self, context):
        return {"FINISHED"}


class THEME_STUDIO_MT_session(bpy.types.Menu):
    bl_translation_context = "Theme Studio"
    bl_label = "Files and Recovery"

    def draw(self, context):
        layout = self.layout
        layout.operator_context = "INVOKE_DEFAULT"
        state = context.window_manager.theme_studio_ui
        layout.prop(state, "profile_name")
        layout.operator("theme_studio.export_native_xml", text=iface("Export Blender Theme Copy…"), icon="EXPORT")
        _wrapped(layout, "Export a Blender theme file. Editing stays open.")
        layout.separator()
        layout.operator("theme_studio.save_profile", text=iface("Save Theme Studio Project…"), icon="FILE_TICK")
        _wrapped(layout, "Save a project file to edit later.")
        layout.operator("theme_studio.load_profile", text=iface("Load Theme Studio Project…"), icon="FILE_FOLDER")
        _wrapped(layout, "Load a project file. Current changes stay protected by a save, discard, or cancel choice.")
        layout.operator("theme_studio.load_native_theme", text=iface("Load Blender Theme…"), icon="IMPORT")
        layout.separator()
        layout.operator("theme_studio.safety", icon="INFO")
        layout.operator("theme_studio.cancel", icon="CANCEL")


class THEME_STUDIO_MT_theme_selector(bpy.types.Menu):
    bl_translation_context = CONTEXT
    bl_label = "Choose a Blender theme"

    def draw(self, _context):
        layout = self.layout
        layout.operator_context = "EXEC_DEFAULT"
        presets = native_themes.native_theme_presets()
        if not presets:
            layout.label(text=iface("No Blender theme presets were found."))
            return
        for name, filepath, _user_owned in presets:
            operator = layout.operator("theme_studio.load_native_theme", text=name, icon="COLOR")
            operator.filepath = filepath


def _draw_theme_selector(layout, context, session):
    identity = _theme_identity(context, session)
    label = identity["name"] or iface("Choose a Blender theme")
    layout.menu("THEME_STUDIO_MT_theme_selector", text=label, icon="COLOR")


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


def _workspace_mode(context=None):
    context = context or bpy.context
    addons = getattr(getattr(context, "preferences", None), "addons", None)
    addon = addons.get(__package__) if addons is not None else None
    mode = getattr(getattr(addon, "preferences", None), "workspace_mode", "HYBRID")
    return mode if mode in {"PREFERENCES", "HYBRID", "NPANEL"} else "HYBRID"


def _addon_preferences(context):
    addons = getattr(getattr(context, "preferences", None), "addons", None)
    addon = addons.get(__package__) if addons is not None else None
    return getattr(addon, "preferences", None)


def _selected_native_library(context, selected_path=None):
    preferences = _addon_preferences(context)
    path = selected_path if selected_path is not None else getattr(preferences, "native_library_path", "")
    if not path:
        raise RuntimeError(iface("Select an existing asset library in Theme Studio add-on preferences."))
    if path not in {library_path for _name, library_path in native_themes.configured_libraries(context)}:
        raise RuntimeError(iface("Selected asset library is unavailable. Choose an existing library again."))
    return path


def _prepare_native_save(context):
    if _comparing:
        raise RuntimeError(iface("Return to live theme before saving a native theme."))
    session = _require_session()
    if session._auto_save_owned and session.backend.get_auto_save():
        raise RuntimeError(iface("Save on Exit changed during preview. Resolve it before saving a native theme."))
    if not _flush_colors(session):
        raise RuntimeError(iface("Pending changes: resolve conflict before saving."))
    session.preview()
    _mark_live(session)
    return session


def _commit_native_theme(context, name, library_path, expected):
    global _theme_source_origin
    _prepare_native_save(context)
    paths = native_themes.save_native_theme(context, name, library_path, expected=expected)
    _remember_native_theme_library_association(context, paths, library_path)
    try:
        _close_session("confirm")
    except Exception as exc:
        _notice(("Native theme files were saved to {paths}. Session remains open: {detail}.",
                 {"paths": ", ".join(map(str, paths)), "detail": str(exc)}), "ERROR", paths)
        return paths, False
    _theme_source_origin = _capture_theme_origin(context)
    return paths, True


def _record_native_save_result(name, paths, closed):
    global _theme_result
    _theme_result = {"kind": "save", "name": name,
                     "paths": tuple(map(str, paths)), "session_open": not closed}


def _export_native_xml(context, filepath, expected):
    global _theme_result
    _prepare_native_save(context)
    native_themes.export_native_theme(context, filepath, expected=expected)
    _theme_result = {"kind": "export", "path": str(Path(filepath)), "session_open": True}


def _apply_native_theme_preset(context, filepath):
    global _session_theme_path, _theme_source_origin, _theme_result, _theme_identity_unknown, _completion, _message, _severity, _issues
    filepath = str(Path(filepath).resolve())
    discovered = {str(Path(path).resolve()) for _label, path, _user_owned in native_themes.native_theme_presets()}
    if filepath not in discovered:
        raise RuntimeError(iface("Choose an existing Blender theme."))
    native_themes.validate_native_preset(filepath)
    try:
        native_themes.apply_native_theme(context, filepath)
    except Exception:
        _theme_identity_unknown = True
        raise
    _reset_theme_status()
    _session_theme_path = filepath
    _theme_source_origin = _capture_theme_origin(context)
    _completion = "Session ended"
    _message, _severity, _issues = "", "INFO", ()


def _native_preset_choice_items(self, _context):
    options = json.loads(self.preset_options or "[]")
    items = [("NONE", iface("Choose a Blender theme"), "")] + [
        (str(index + 1), label, "") for index, (label, _path, _user_owned) in enumerate(options)]
    return _retain_native_enum_items(("preset", self.preset_options), items)


def _load_selected_native_theme(context, filepath):
    path = native_themes._canonical(Path(filepath))
    discovered = {native_themes._canonical(Path(candidate))
                  for _name, candidate, _owned in native_themes.native_theme_presets()}
    if path not in discovered:
        raise RuntimeError(iface("Choose an existing Blender theme."))
    native_themes.validate_native_preset(str(path))
    if get_session() is not None:
        bpy.ops.theme_studio.resolve_native_load("INVOKE_DEFAULT", filepath=str(path))
    else:
        _apply_native_theme_preset(context, str(path))


def _native_collision_choice_items(self, _context):
    plan = _native_save_plans.get(self.plan_token, {})
    choices = [("RENAME", iface("Rename"), iface("Choose a different name or path.")),
               ("CANCEL", iface("Cancel"), iface("Leave existing files and editing session unchanged."))]
    if not plan.get("protected"):
        choices.insert(0, ("OVERWRITE", iface("Overwrite"), iface("Replace only the listed confirmed files.")))
    return _retain_native_enum_items(("collision", self.plan_token, plan.get("protected")), choices)


def _retain_native_enum_items(key, items):
    retained = tuple(tuple(str(value) for value in item[:3]) + tuple(item[3:]) for item in items)
    return _native_enum_item_refs.setdefault((key, retained), retained)


def _clear_native_save_plans():
    _native_save_plans.clear()


def _cache_native_save_plan(record):
    record["session"] = get_session()
    token = uuid.uuid4().hex
    _native_save_plans[token] = record
    return token


class THEME_STUDIO_AP_preferences(bpy.types.AddonPreferences):
    bl_idname = __package__
    workspace_mode: EnumProperty(name="Workspace", translation_context=CONTEXT, items=(
        ("PREFERENCES", "Preferences > Themes", "Full workspace in Preferences > Themes"),
        ("HYBRID", "Hybrid", "Common palette in the N-panel; full workspace in Preferences > Themes"),
        ("NPANEL", "N-panel", "Full workspace in the N-panel only"),
    ), default="HYBRID")
    native_library_path: StringProperty(name="Asset Library", translation_context=CONTEXT, default="")

    def draw(self, context):
        self.layout.prop(self, "workspace_mode")
        libraries = native_themes.configured_libraries(context)
        selected = next((name for name, path in libraries if path == self.native_library_path), "")
        if selected:
            self.layout.label(text=iface("Selected library: {name}").format(name=selected), icon="ASSET_MANAGER")
        elif self.native_library_path:
            self.layout.label(text=iface("Selected asset library is unavailable."), icon="ERROR")
        else:
            self.layout.label(text=iface("No asset library selected."), icon="INFO")
        self.layout.operator("theme_studio.select_native_library", text=iface("Choose Existing Asset Library"), icon="FILE_FOLDER")


class THEME_STUDIO_OT_select_native_library(bpy.types.Operator):
    bl_translation_context = CONTEXT
    bl_idname = "theme_studio.select_native_library"
    bl_label = "Choose Existing Asset Library"
    library_options: StringProperty(options={"HIDDEN", "SKIP_SAVE"})
    library_choice: EnumProperty(items=_native_library_choice_items, options={"SKIP_SAVE"},
                                 translation_context=CONTEXT)

    def invoke(self, context, _event):
        self.library_options = json.dumps(native_themes.configured_libraries(context))
        if not json.loads(self.library_options):
            self.report({"WARNING"}, iface("No configured asset libraries are available."))
            return {"CANCELLED"}
        self.library_choice = "NONE"
        return context.window_manager.invoke_props_dialog(self, width=620)

    def draw(self, _context):
        self.layout.prop(self, "library_choice", text=iface("Asset Library"))

    def execute(self, context):
        try:
            if self.library_choice == "NONE":
                raise ValueError(iface("Choose an existing asset library."))
            libraries = json.loads(self.library_options)
            index = int(self.library_choice) - 1
            if not 0 <= index < len(libraries):
                raise ValueError(iface("Asset library selection expired. Choose again."))
            name, path = libraries[index]
            if (name, path) not in native_themes.configured_libraries(context):
                raise RuntimeError(iface("Selected asset library changed. Choose an existing library again."))
            _addon_preferences(context).native_library_path = path
            return {"FINISHED"}
        except Exception as exc:
            self.report({"WARNING"}, str(exc))
            return {"CANCELLED"}


def _begin_native_theme_save(context, name, library_path, resume_native_path="", *, finish_request=None):
    if not name.strip():
        raise ValueError(iface("Enter a theme name."))
    if finish_request is not None:
        finish_request = _validate_finish_save_request(context, finish_request)
    library_path = _selected_native_library(context, library_path)
    _prepare_native_save(context)
    try:
        plan = native_themes.plan_native_theme(context, name, library_path)
        if finish_request is not None and finish_request["save_mode"] == "UPDATE":
            if (str(native_themes._canonical(Path(plan["paths"][0]))) != finish_request["update_target"]
                    or plan["expected"].get(native_themes._canonical(Path(finish_request["update_target"])))
                    != finish_request["source_origin"]["source_bytes"]):
                raise RuntimeError(iface("The update destination changed. Choose the library again."))
        record = {"kind": "save", "name": name, "library_path": library_path,
                  "paths": tuple(plan["paths"]), "expected": dict(plan["expected"]),
                  "protected": False, "resume_native_path": resume_native_path,
                  "finish_request": finish_request}
    except native_themes.ProtectedThemeCollision as exc:
        record = {"kind": "save", "name": name, "library_path": library_path,
                  "paths": tuple(exc.paths), "expected": {}, "protected": True,
                  "resume_native_path": resume_native_path, "finish_request": finish_request}
    if record["protected"] or any(value is not None for value in record["expected"].values()):
        token = _cache_native_save_plan(record)
        result = bpy.ops.theme_studio.native_theme_collision("INVOKE_DEFAULT", plan_token=token)
        if "CANCELLED" in result:
            _native_save_plans.pop(token, None)
        return {"FINISHED"}
    if finish_request is not None:
        _validate_finish_save_request(context, finish_request)
    paths, closed = _commit_native_theme(context, name, library_path, record["expected"])
    _record_native_save_result(name, paths, closed)
    if closed and resume_native_path:
        _apply_native_theme_preset(context, resume_native_path)
    return {"FINISHED"}


class THEME_STUDIO_OT_save_native_theme(bpy.types.Operator):
    bl_translation_context = CONTEXT
    bl_idname = "theme_studio.save_native_theme"
    bl_label = "Save Blender Theme…"
    bl_description = "Save a native Blender theme preset and finish editing"
    name: StringProperty(name="Theme Name", translation_context=CONTEXT, default="", maxlen=80)
    library_path: StringProperty(options={"HIDDEN", "SKIP_SAVE"})
    resume_native_path: StringProperty(options={"HIDDEN", "SKIP_SAVE"})

    @classmethod
    def poll(cls, _context):
        session = get_session()
        return session is not None and not session.faulted

    def invoke(self, context, _event):
        if not self.name:
            self.name = context.window_manager.theme_studio_ui.profile_name
        if not self.library_path:
            preferences = _addon_preferences(context)
            self.library_path = getattr(preferences, "native_library_path", "")
        return context.window_manager.invoke_props_dialog(self, width=560, confirm_text=iface("Save Blender Theme"))

    def draw(self, context):
        self.layout.prop(self, "name")
        library_name = next((name for name, path in native_themes.configured_libraries(context)
                             if path == self.library_path), iface("not selected"))
        self.layout.label(text=iface("Selected asset library: {name}").format(name=library_name))
        _wrapped(self.layout, "Saving writes a native XML theme preset and ends this editing session only after both files are saved.")

    def execute(self, context):
        try:
            result = _begin_native_theme_save(context, self.name, self.library_path, self.resume_native_path)
            context.window_manager.theme_studio_ui.profile_name = self.name
            return result
        except Exception as exc:
            _error(exc)
            self.report({"ERROR"}, _message_text(_message))
            return {"CANCELLED"}


class THEME_STUDIO_OT_native_theme_collision(bpy.types.Operator):
    bl_translation_context = CONTEXT
    bl_idname = "theme_studio.native_theme_collision"
    bl_label = "Existing Theme Files"
    plan_token: StringProperty(options={"HIDDEN", "SKIP_SAVE"})
    resolution: EnumProperty(items=_native_collision_choice_items, options={"SKIP_SAVE"},
                              translation_context=CONTEXT)
    new_name: StringProperty(name="New Name", translation_context=CONTEXT, default="", maxlen=80)

    def invoke(self, context, _event):
        self.resolution = "CANCEL"
        return context.window_manager.invoke_props_dialog(self, width=620)

    def draw(self, _context):
        plan = _native_save_plans.get(self.plan_token)
        if plan is None:
            self.layout.label(text=iface("Save request expired. Start again."), icon="ERROR")
            return
        self.layout.label(text=iface("Existing paths need a decision:"), icon="ERROR")
        for path in plan["paths"]:
            _wrapped(self.layout, str(path))
        self.layout.prop(self, "resolution", expand=True)
        if self.resolution == "RENAME" and plan["kind"] == "save":
            self.layout.prop(self, "new_name")
        elif self.resolution == "RENAME":
            _wrapped(self.layout, "Choose a different destination in the file browser.")

    def cancel(self, _context):
        _native_save_plans.pop(self.plan_token, None)

    def execute(self, context):
        plan = _native_save_plans.get(self.plan_token)
        if plan is None:
            self.report({"ERROR"}, iface("Save request expired. Start again."))
            return {"CANCELLED"}
        if plan["session"] is not get_session():
            _native_save_plans.pop(self.plan_token, None)
            self.report({"ERROR"}, iface("Save request expired. Start again."))
            return {"CANCELLED"}
        if self.resolution == "CANCEL":
            _native_save_plans.pop(self.plan_token, None)
            return {"CANCELLED"}
        if self.resolution == "RENAME":
            record = _native_save_plans.get(self.plan_token)
            if record["kind"] == "save" and not self.new_name.strip():
                self.report({"WARNING"}, iface("Enter a new name."))
                return {"CANCELLED"}
            if record["kind"] == "save":
                try:
                    request = record.get("finish_request")
                    if request is not None:
                        request = _validate_finish_save_request(context, request)
                        if request["save_mode"] == "UPDATE":
                            raise RuntimeError(iface(
                                "Update keeps the original name. Choose Overwrite or Cancel; choose Save as new to rename."))
                        if request["save_mode"] == "NEW" and (
                                _finish_native_stem(self.new_name).casefold() ==
                                _finish_native_stem(request["source_origin"]["name"]).casefold()
                                if request["source_origin"] and request["source_origin"].get("name")
                                else False):
                            raise RuntimeError(iface("Choose a different name to save as new."))
                        request = dict(request, name=self.new_name,
                                       normalized_name=_finish_native_stem(self.new_name))
                    _native_save_plans.pop(self.plan_token, None)
                    _begin_native_theme_save(context, self.new_name, record["library_path"],
                                             record["resume_native_path"], finish_request=request)
                except Exception as exc:
                    _error(exc)
                    self.report({"ERROR"}, _message_text(_message))
                    return {"CANCELLED"}
            else:
                _native_save_plans.pop(self.plan_token, None)
                bpy.ops.theme_studio.export_native_xml("INVOKE_DEFAULT")
            return {"FINISHED"}
        try:
            if plan["kind"] == "save":
                request = plan.get("finish_request")
                if request is not None:
                    request = _validate_finish_save_request(context, request)
                    refreshed = native_themes.plan_native_theme(context, plan["name"], plan["library_path"])
                    if (tuple(map(str, refreshed["paths"])) != tuple(map(str, plan["paths"]))
                            or refreshed["expected"] != plan["expected"]):
                        raise RuntimeError(iface("Theme files changed after confirmation. Start saving again."))
                paths, closed = _commit_native_theme(context, plan["name"], plan["library_path"],
                                                      plan["expected"])
                _record_native_save_result(plan["name"], paths, closed)
                if closed and plan["resume_native_path"]:
                    _apply_native_theme_preset(context, plan["resume_native_path"])
            else:
                _export_native_xml(context, plan["filepath"], plan["expected"])
            return {"FINISHED"}
        except Exception as exc:
            _error(exc)
            self.report({"ERROR"}, _message_text(_message))
            return {"CANCELLED"}
        finally:
            _native_save_plans.pop(self.plan_token, None)


class THEME_STUDIO_OT_export_native_xml(bpy.types.Operator, ExportHelper):
    bl_translation_context = CONTEXT
    bl_idname = "theme_studio.export_native_xml"
    bl_label = "Export Blender Theme Copy…"
    bl_description = "Export a Blender theme copy without ending editing"
    filename_ext = ".xml"
    filter_glob: StringProperty(default="*.xml", options={"HIDDEN"})

    @classmethod
    def poll(cls, _context):
        session = get_session()
        return session is not None and not session.faulted

    def invoke(self, context, _event):
        if not self.filepath:
            self.filepath = "theme.xml"
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        try:
            _prepare_native_save(context)
            path = native_themes._canonical(Path(bpy.path.ensure_ext(self.filepath, self.filename_ext)))
            expected = {path: path.read_bytes() if path.exists() else None}
            if expected[path] is not None:
                token = _cache_native_save_plan({"kind": "export", "filepath": str(path),
                                                 "paths": (path,), "expected": expected,
                                                 "protected": False})
                result = bpy.ops.theme_studio.native_theme_collision("INVOKE_DEFAULT", plan_token=token)
                if "CANCELLED" in result:
                    _native_save_plans.pop(token, None)
                return {"FINISHED"}
            _export_native_xml(context, str(path), expected)
            _notice("Native XML copy exported. Editing session remains open.")
            return {"FINISHED"}
        except Exception as exc:
            _error(exc)
            self.report({"ERROR"}, _message_text(_message))
            return {"CANCELLED"}


class THEME_STUDIO_OT_load_native_theme(bpy.types.Operator):
    bl_translation_context = CONTEXT
    bl_idname = "theme_studio.load_native_theme"
    bl_label = "Load Blender Theme…"
    bl_description = "Load an existing Blender native theme preset"
    filepath: StringProperty(options={"HIDDEN", "SKIP_SAVE"})
    preset_options: StringProperty(options={"HIDDEN", "SKIP_SAVE"})
    preset_choice: EnumProperty(items=_native_preset_choice_items, options={"SKIP_SAVE"},
                                translation_context=CONTEXT)

    @classmethod
    def poll(cls, _context):
        return _registry is not None and not _recovery_path and not (get_session() and get_session().faulted)

    def invoke(self, context, _event):
        if self.filepath:
            return self.execute(context)
        self.preset_options = json.dumps(native_themes.native_theme_presets())
        if not json.loads(self.preset_options):
            self.report({"WARNING"}, iface("No Blender theme presets were found."))
            return {"CANCELLED"}
        self.preset_choice = "NONE"
        return context.window_manager.invoke_props_dialog(self, width=620)

    def draw(self, _context):
        self.layout.prop(self, "preset_choice", text=iface("Blender Theme"))

    def execute(self, context):
        try:
            if self.filepath:
                _load_selected_native_theme(context, self.filepath)
                return {"FINISHED"}
            if self.preset_choice == "NONE":
                raise ValueError(iface("Choose an existing Blender theme."))
            options = json.loads(self.preset_options)
            index = int(self.preset_choice) - 1
            if not 0 <= index < len(options):
                raise ValueError(iface("Theme preset selection expired. Choose again."))
            _label, filepath, _user_owned = options[index]
            _load_selected_native_theme(context, filepath)
            return {"FINISHED"}
        except Exception as exc:
            _error(exc)
            self.report({"ERROR"}, _message_text(_message))
            return {"CANCELLED"}


class THEME_STUDIO_OT_resolve_native_load(bpy.types.Operator):
    bl_translation_context = CONTEXT
    bl_idname = "theme_studio.resolve_native_load"
    bl_label = "Resolve Editing Before Loading"
    filepath: StringProperty(options={"HIDDEN", "SKIP_SAVE"})
    resolution: EnumProperty(name="Current Editing", translation_context=CONTEXT, items=(
        ("SAVE", "Save Current", "Save a named native preset, then load selected preset"),
        ("DISCARD", "Discard Current", "Restore initial theme, then load selected preset"),
        ("CANCEL", "Cancel", "Keep current editing and do not load"),
    ), default="CANCEL", options={"SKIP_SAVE"})

    def invoke(self, context, _event):
        self.resolution = "CANCEL"
        return context.window_manager.invoke_props_dialog(self, width=560)

    def draw(self, _context):
        self.layout.label(text=iface("Resolve the current session before loading this Blender theme."))
        self.layout.prop(self, "resolution", expand=True)

    def execute(self, context):
        try:
            discovered = {str(Path(path).resolve()) for _label, path, _user_owned
                          in native_themes.native_theme_presets()}
            if str(Path(self.filepath).resolve()) not in discovered:
                raise RuntimeError(iface("Choose an existing Blender theme."))
            native_themes.validate_native_preset(self.filepath)
            if self.resolution == "CANCEL":
                return {"CANCELLED"}
            if self.resolution == "SAVE":
                bpy.ops.theme_studio.save_native_theme("INVOKE_DEFAULT", resume_native_path=self.filepath)
                return {"FINISHED"}
            _close_session("cancel")
            _apply_native_theme_preset(context, self.filepath)
            return {"FINISHED"}
        except Exception as exc:
            _error(exc)
            self.report({"ERROR"}, _message_text(_message))
            return {"CANCELLED"}


class THEME_STUDIO_OT_palette_details(bpy.types.Operator):
    bl_translation_context = "Theme Studio"
    bl_idname = "theme_studio.palette_details"
    bl_label = "Open Group Details"
    group_id: StringProperty(translation_context=CONTEXT, options={"SKIP_SAVE"})
    all_controls: BoolProperty(translation_context=CONTEXT, options={"SKIP_SAVE"})

    def execute(self, context):
        state = context.window_manager.theme_studio_ui
        if self.all_controls:
            state.picker_active = False
            state.picker_kind = state.picker_editor_id = state.picker_label = ""
            state.palette_focus = ""
            if _detail_items:
                state.detail_category = _detail_items[0][0]
        else:
            if self.group_id == "viewport":
                if _viewport_group is None:
                    self.report({"ERROR"}, iface("Palette group is unavailable."))
                    return {"CANCELLED"}
                focus = "viewport"
            elif any(group["id"] == self.group_id for group in _palette_map):
                focus = self.group_id
            else:
                self.report({"ERROR"}, iface("Palette group is unavailable."))
                return {"CANCELLED"}
            state.picker_active = False
            state.picker_kind = state.picker_editor_id = state.picker_label = ""
            state.palette_focus = focus
        state.show_details = True
        state.workspace_page = "details"
        _detail_changed(state, context)
        _redraw()
        mode = _workspace_mode(context)
        if mode == "NPANEL":
            if not _show_theme_npanel(context):
                self.report({"WARNING"}, iface("Theme details are ready. Open a 3D View to see them in the sidebar."))
        elif context.area is None or context.area.type != "PREFERENCES":
            bpy.ops.theme_studio.open()
        return {"FINISHED"}


class THEME_STUDIO_OT_clear_picker(bpy.types.Operator):
    bl_translation_context = CONTEXT
    bl_idname = "theme_studio.clear_picker"
    bl_label = "Back to all Details"

    def execute(self, context):
        state = context.window_manager.theme_studio_ui
        state.picker_active = False
        state.picker_kind = state.picker_editor_id = state.picker_label = ""
        state.palette_focus = ""
        if _detail_items:
            state.detail_category = _detail_items[0][0]
        _detail_changed(state, context)
        _redraw()
        return {"FINISHED"}


def _draw_workspace(layout, context):
    layout.use_property_split = False
    state = context.window_manager.theme_studio_ui
    session = get_session()
    heading = layout.row(align=True)
    heading.label(text=iface("Customize Theme"), icon="COLOR", text_ctxt=CONTEXT)
    heading.menu("THEME_STUDIO_MT_session", text="", icon="DOWNARROW_HLT")
    if _recovery_path:
        _draw_recovery(layout)
        return
    _draw_theme_selector(layout, context, session)
    _draw_identity_status(layout, context, state, session)
    if _severity != "INFO":
        _draw_status(layout, state)
    if session is None:
        if _save_pending:
            _wrapped(layout, "Theme remains active, but preference saving was not verified.")
            layout.operator_context = "INVOKE_DEFAULT"
            layout.operator("theme_studio.save_preferences", icon="FILE_TICK")
        _wrapped(layout, "Start with current colors. Live changes remain reversible and unsaved.")
        start = layout.row()
        start.scale_y = 1.3
        start.operator("theme_studio.start", text=iface("Retry") if _start_failed else iface("Start editing"), icon="DUPLICATE")
        layout.operator_context = "INVOKE_DEFAULT"
        secondary = layout.row(align=True)
        secondary.scale_y = 0.85
        secondary.operator("theme_studio.load_profile", text=iface("Load Theme Studio Project…"), icon="FILE_FOLDER")
        if _workspace_mode(context) != "NPANEL":
            secondary.operator("theme_studio.open", text=iface("Open Preferences"), icon="PREFERENCES")
        if _severity == "INFO":
            _draw_status(layout, state)
        if _file_notice:
            _wrapped(layout, _file_notice)
        return
    if session.faulted:
        _wrapped(layout, "Restore incomplete. Editing is blocked. Save a copy or retry restoration; recovery details are under Files and Recovery." if
                 _workspace_mode(context) != "NPANEL" else
                 "Restore incomplete. Editing is blocked. Retry restoration here; recovery details are under Files and Recovery.")
        layout.operator("theme_studio.cancel", text=iface("Retry Restore"), icon="CANCEL")
        return
    warning = layout.box()
    _wrapped(warning, "Preview is live, not saved. Do not use Blender's Save Preferences during preview.")
    _wrapped(warning, "Closing Preferences does not end preview. Use Finish here." if
             _workspace_mode(context) != "NPANEL" else
             "Hiding this panel does not end preview. Use Finish here.")
    if _workspace_mode(context) != "NPANEL":
        warning.operator("theme_studio.open", text=iface("Open Preferences"), icon="PREFERENCES")
    if session._auto_save_owned and session.backend.get_auto_save():
        warning.alert = True
        _wrapped(warning, "Save on Exit changed during preview. Further edits are blocked.")
    navigation = layout.row(align=True)
    navigation.prop(state, "workspace_page", expand=True)
    secondary = layout.row(align=True)
    secondary.scale_y = 0.8
    secondary.operator_context = "INVOKE_DEFAULT"
    if _comparing:
        secondary.operator("theme_studio.previous", text=iface("Return to Live Theme"), icon="HIDE_OFF")
    else:
        compare = secondary.row(align=True)
        compare.enabled = _theme_changed_or_pending(session)
        compare.operator("theme_studio.previous", text=iface("Compare"), icon="ARROW_LEFTRIGHT")
    secondary.operator("theme_studio.finish", text=iface("Finish…"), icon="CHECKMARK")
    history = layout.row(align=True)
    history.scale_y = 0.8
    history.operator_context = "INVOKE_DEFAULT"
    history.label(text=iface("Edit"), text_ctxt=CONTEXT)
    history.operator("theme_studio.undo", text="", icon="LOOP_BACK")
    history.operator("theme_studio.redo", text="", icon="LOOP_FORWARDS")
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


def _draw_preferences_entry(self, context):
    if _workspace_mode(context) != "NPANEL":
        _draw_workspace(self.layout, context)


def _draw_project_access(self, _context):
    self.layout.operator("theme_studio.open", text=iface("Theme Studio"), icon="PREFERENCES")


def _area_region_at(screen, mouse_x, mouse_y):
    for area in screen.areas:
        if not (area.x <= mouse_x < area.x + area.width and area.y <= mouse_y < area.y + area.height):
            continue
        regions = sorted(area.regions, key=lambda region: (
            region.type not in {"UI", "TOOLS", "HEADER", "TOOL_HEADER", "TOOL_PROPS"},
            region.width <= 0 or region.height <= 0,
        ))
        for region in regions:
            if region.width > 0 and region.height > 0 and (
                    region.x <= mouse_x < region.x + region.width
                    and region.y <= mouse_y < region.y + region.height):
                return area, region
    return None


def _picker_target_at(screen, mouse_x, mouse_y):
    hit = _area_region_at(screen, mouse_x, mouse_y)
    if hit is None:
        return None
    area, region = hit
    return resolve_target(area.type, region.type)


def _open_picker_preferences(generation, window):
    if generation != _picker_generation or _registry is None:
        return None
    try:
        if window.as_pointer() not in {item.as_pointer() for item in bpy.context.window_manager.windows}:
            return None
    except (AttributeError, ReferenceError, RuntimeError):
        return None
    try:
        with bpy.context.temp_override(window=window):
            result = bpy.ops.theme_studio.open()
        if "CANCELLED" in result:
            raise RuntimeError("Preferences could not be opened")
    except Exception:
        _notice("Location is saved, but Blender Preferences could not be opened.", "WARNING")
    return None


def _route_pick_target(context, target):
    state = context.window_manager.theme_studio_ui
    if target is None or not _set_picker_target(state, get_registry(), target):
        return False
    _detail_changed(state, context)
    _redraw()
    return True


class THEME_STUDIO_OT_pick(bpy.types.Operator):
    bl_translation_context = CONTEXT
    bl_idname = "theme_studio.pick"
    bl_label = "Locate in Theme Studio"
    bl_description = "Choose an editor or shared controls in this project window"

    @classmethod
    def poll(cls, context):
        return (_registry is not None and not _recovery_path and context.window is not None
                and context.window.screen is not None and context.area is not None
                and context.area.type != "PREFERENCES")

    def invoke(self, context, _event):
        global _picker_generation
        _picker_generation += 1
        self._picker_window = context.window.as_pointer()
        self._picker_window_ref = context.window
        self._picker_screen = context.window.screen
        self._picker_generation = _picker_generation
        self._picker_target = None
        self._picker_pressed = False
        self._picker_cancel_right = False
        context.window.cursor_modal_set("EYEDROPPER")
        try:
            context.window_manager.modal_handler_add(self)
        except Exception:
            try:
                context.window.cursor_modal_restore()
            except (AttributeError, ReferenceError, RuntimeError):
                pass
            raise
        self.report({"INFO"}, iface("Picker active: click an editor or control. Esc or right-click cancels."))
        return {"RUNNING_MODAL"}

    def _end_picker(self, result, message=None, level="INFO"):
        try:
            self._picker_window_ref.cursor_modal_restore()
        except (AttributeError, ReferenceError, RuntimeError):
            pass
        if message:
            self.report({level}, iface(message))
        return {result}

    def modal(self, context, event):
        if self._picker_generation != _picker_generation:
            return self._end_picker("CANCELLED", "Location cancelled.")
        if not context.window or context.window.as_pointer() != self._picker_window:
            return self._end_picker("CANCELLED", "Location cancelled.")
        if event.type == "ESC" and event.value == "PRESS":
            return self._end_picker("CANCELLED", "Location cancelled.")
        if event.type == "RIGHTMOUSE":
            if event.value == "PRESS":
                self._picker_cancel_right = True
            elif event.value == "RELEASE" and self._picker_cancel_right:
                return self._end_picker("CANCELLED", "Location cancelled.")
            return {"RUNNING_MODAL"}
        if event.type == "MOUSEMOVE":
            return {"RUNNING_MODAL", "PASS_THROUGH"}
        if event.type == "LEFTMOUSE" and event.value == "PRESS":
            try:
                self._picker_target = _picker_target_at(self._picker_screen, event.mouse_x, event.mouse_y)
            except Exception:
                return self._end_picker("CANCELLED", "Could not inspect this location.", "WARNING")
            self._picker_pressed = True
            return {"RUNNING_MODAL"}
        if event.type == "LEFTMOUSE" and event.value == "RELEASE":
            if not self._picker_pressed:
                return {"RUNNING_MODAL"}
            self._picker_pressed = False
            if self._picker_target is None:
                return self._end_picker("CANCELLED", "No Theme Studio destination matches this location.", "WARNING")
            try:
                routed = _route_pick_target(context, self._picker_target)
            except Exception:
                return self._end_picker("CANCELLED", "Could not locate this destination.", "WARNING")
            if not routed:
                return self._end_picker("CANCELLED", "No editable Theme Studio fields match this location.", "WARNING")
            generation, window = self._picker_generation, self._picker_window_ref
            label = self._picker_target["label"]
            message = ("Shared control styles selected. Exact widget is not identified."
                       if self._picker_target["kind"] == "controls" else
                       "Outliner theme fields selected. Clicked row is not identified."
                       if self._picker_target["editor_id"] == "outliner" else
                       iface("{label} theme fields selected.").format(label=iface(label)))
            result = self._end_picker("FINISHED", message)
            try:
                bpy.app.timers.register(lambda: _open_picker_preferences(generation, window), first_interval=0.1)
            except (AttributeError, ReferenceError, RuntimeError):
                self.report({"WARNING"}, iface("Location is saved, but Blender Preferences could not be opened."))
            return result
        return {"RUNNING_MODAL"}


class THEME_STUDIO_OT_locate(bpy.types.Operator):
    bl_translation_context = CONTEXT
    bl_idname = "theme_studio.locate"
    bl_label = "Locate in Theme Studio"
    bl_description = "Open matching editor fields or shared control styles in Theme Studio"
    button_context: BoolProperty(options={"SKIP_SAVE"})

    @classmethod
    def poll(cls, _context):
        return _registry is not None and not _recovery_path

    def execute(self, context):
        area, region = context.area, context.region
        target = (resolve_target(area.type, region.type, button=self.button_context)
                  if area is not None and region is not None else None)
        if target is None:
            self.report({"WARNING"}, iface("No Theme Studio destination matches this location."))
            return {"CANCELLED"}
        if not _route_pick_target(context, target):
            self.report({"WARNING"}, iface("No editable Theme Studio fields match this location."))
            return {"CANCELLED"}
        if "CANCELLED" in bpy.ops.theme_studio.open():
            self.report({"ERROR"}, iface("Location is saved, but Blender Preferences could not be opened."))
        return {"FINISHED"}


class THEME_STUDIO_OT_open(bpy.types.Operator):
    bl_translation_context = CONTEXT
    bl_idname = "theme_studio.open"
    bl_label = "Open Theme Studio"
    bl_description = "Open Theme Studio in the selected workspace mode"

    def execute(self, context):
        if _workspace_mode(context) == "NPANEL":
            if _show_theme_npanel(context):
                self.report({"INFO"}, iface("Theme Studio is in the 3D View sidebar. Select the Theme Studio tab."))
                return {"FINISHED"}
            self.report({"WARNING"}, iface("Open a 3D View to use Theme Studio in its sidebar."))
            return {"CANCELLED"}
        try:
            result = bpy.ops.screen.userpref_show()
            if "CANCELLED" in result:
                raise RuntimeError(iface("Blender Preferences could not be opened."))
            preferences_window = next((window for window in context.window_manager.windows
                                       if window.screen and any(area.type == "PREFERENCES"
                                                                for area in window.screen.areas)), None)
            if preferences_window is None:
                raise RuntimeError(iface("Blender Preferences window is unavailable."))
            context.preferences.active_section = "THEMES"
            for area in preferences_window.screen.areas:
                if area.type == "PREFERENCES":
                    area.tag_redraw()
            return {"FINISHED"}
        except Exception as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}


class THEME_STUDIO_PT_theme(bpy.types.Panel):
    bl_label = "Theme Studio"
    bl_idname = "THEME_STUDIO_PT_theme"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Theme Studio"

    @classmethod
    def poll(cls, context):
        return _workspace_mode(context) != "PREFERENCES"

    def draw(self, context):
        _draw_npanel_shortcut(self.layout, context)


def _draw_npanel_shortcut(layout, context):
    mode = _workspace_mode(context)
    if mode == "NPANEL":
        _draw_workspace(layout, context)
        return
    layout.use_property_split = False
    heading = layout.row(align=True)
    heading.label(text=iface("Theme Studio · Hybrid"), icon="COLOR", text_ctxt=CONTEXT)
    heading.operator("theme_studio.open", text=iface("Full Workspace"), icon="PREFERENCES")
    if _recovery_path:
        _draw_recovery(layout)
        return
    session = get_session()
    _draw_theme_selector(layout, context, session)
    layout.label(text=session_status(), icon="INFO" if session else "PAUSE", text_ctxt=CONTEXT)
    if session is None:
        layout.operator("theme_studio.start", text=iface("Start editing"), icon="DUPLICATE")
        return
    if session.faulted:
        _wrapped(layout, "Restore incomplete. Editing is blocked. Retry restoration in Theme Studio Preferences." if
                 _workspace_mode(context) != "NPANEL" else
                 "Restore incomplete. Editing is blocked. Retry restoration here.")
        layout.operator("theme_studio.cancel", text=iface("Retry Restore"), icon="CANCEL")
        return
    _wrapped(layout, "Preview is live, not saved. Do not use Blender's Save Preferences during preview.")
    actions = layout.row(align=True)
    actions.operator("theme_studio.finish", text=iface("Finish…"), icon="CHECKMARK")
    _draw_palette(layout, context.window_manager.theme_studio_ui, session)


def _show_theme_npanel(context):
    window = getattr(context, "window", None)
    screen = getattr(window, "screen", None)
    if screen is None:
        return False
    area = context.area if context.area and context.area.type == "VIEW_3D" else next(
        (item for item in screen.areas if item.type == "VIEW_3D"), None)
    if area is None:
        return False
    area.spaces.active.show_region_ui = True
    area.tag_redraw()
    return True


def _install_ui_hooks():
    global _ui_hooks_registered
    required = (("USERPREF_PT_theme", "prepend", _draw_preferences_entry),
                ("TOPBAR_MT_editor_menus", "append", _draw_project_access))
    for name, method, callback in required:
        menu = getattr(bpy.types, name, None)
        if menu is None:
            raise RuntimeError(iface("Required Blender menu is unavailable: {name}").format(name=name))
        getattr(menu, method)(callback)
        _ui_hooks.append((menu, callback))
        _ui_hooks_registered = True


def _remove_ui_hooks():
    global _ui_hooks_registered
    while _ui_hooks:
        menu, callback = _ui_hooks[-1]
        menu.remove(callback)
        _ui_hooks.pop()
    _ui_hooks_registered = False



_CLASSES = (
    THEME_STUDIO_AP_preferences, THEME_STUDIO_PG_target, THEME_STUDIO_PG_state,
    THEME_STUDIO_OT_start, THEME_STUDIO_OT_preview,
    THEME_STUDIO_OT_previous, THEME_STUDIO_OT_cancel, THEME_STUDIO_OT_confirm,
    THEME_STUDIO_OT_finish, THEME_STUDIO_OT_save_preferences, THEME_STUDIO_OT_undo, THEME_STUDIO_OT_redo,
    THEME_STUDIO_OT_common_value, THEME_STUDIO_OT_palette_details,
    THEME_STUDIO_OT_select_native_library, THEME_STUDIO_OT_save_native_theme,
    THEME_STUDIO_OT_native_theme_collision, THEME_STUDIO_OT_export_native_xml,
    THEME_STUDIO_OT_load_native_theme, THEME_STUDIO_OT_resolve_native_load,
    THEME_STUDIO_OT_reopen_initial, THEME_STUDIO_OT_recovery_choice,
    THEME_STUDIO_OT_retry_recovery_discovery, THEME_STUDIO_OT_archive_recovery, THEME_STUDIO_OT_recovery,
    THEME_STUDIO_OT_protect_field, THEME_STUDIO_OT_reset_field,
    THEME_STUDIO_OT_copy_report, THEME_STUDIO_OT_page,
    THEME_STUDIO_OT_save_profile, THEME_STUDIO_OT_load_profile, THEME_STUDIO_OT_safety,
    THEME_STUDIO_MT_session, THEME_STUDIO_MT_theme_selector, THEME_STUDIO_UL_fields,
    THEME_STUDIO_OT_open, THEME_STUDIO_PT_theme,
)


def register(*, storage_dir=None):
    """storage_dir is an explicit override for isolated probes."""
    global _registry, _storage_override, _attributes, _color_attributes, _alpha_attributes, _palette_map, _viewport_group, _detail_map, _palette_keys, _palette_alpha_keys, _roundness_paths, _detail_items, _detail_context_items, _detail_context_labels, _recovery_path, _recovery_document, _recovery_plan, _recovery_error, _recovery_detail, _recovery_progress, _recovery_blocked, _recovery_records, _recovery_filenames, _ui_hooks_registered, _theme_source_origin
    if _registered_classes:
        raise RuntimeError(iface("Theme Studio UI is already registered."))
    if get_session() is not None:
        raise RuntimeError(iface("A retained session must be cancelled before registering again."))
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
                           "{count} controls".format(count=len(item["paths"]))) for item in _detail_map)
    _palette_keys = {group["id"]: f"palette_{index:02d}" for index, group in enumerate(_palette_map)}
    _palette_alpha_keys = {"borders": "palette_alpha_borders"}
    THEME_STUDIO_PG_state.__annotations__["detail_category"] = EnumProperty(
        name="Category", translation_context=CONTEXT, items=_detail_category_items, options={"SKIP_SAVE"}, update=_detail_changed,
    )
    THEME_STUDIO_PG_state.__annotations__["detail_context"] = EnumProperty(
        name="Context", translation_context=CONTEXT, items=_detail_context_items_callback, options={"SKIP_SAVE"}, update=_detail_context_changed,
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
        _install_ui_hooks()
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
        _theme_source_origin = _capture_theme_origin(bpy.context)
    except Exception:
        if _ui_hooks_registered:
            _remove_ui_hooks()
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
    global _registry, _storage_override, _palette_map, _detail_map, _palette_keys, _detail_items, _detail_context_items, _detail_context_labels, _recovery_path, _recovery_document, _recovery_plan, _recovery_blocked, _recovery_records, _recovery_filenames, _recovery_error, _recovery_detail, _recovery_progress, _ui_hooks_registered, _picker_generation, _session_theme_path, _theme_result
    # Failure deliberately leaves all registered UI and handlers intact.
    _picker_generation += 1
    _cancel_for_lifecycle(iface("Add-on disabled"))
    _clear_native_save_plans()
    _native_theme_library_associations.clear()
    _discard_colors()
    if _ui_hooks_registered:
        _remove_ui_hooks()
    if _load_pre in bpy.app.handlers.load_pre:
        bpy.app.handlers.load_pre.remove(_load_pre)
    for name in ("theme_studio_palette", "theme_studio_draft", "theme_studio_ui"):
        if hasattr(bpy.types.WindowManager, name):
            delattr(bpy.types.WindowManager, name)
    for cls in reversed(_registered_classes):
        bpy.utils.unregister_class(cls)
    _registered_classes.clear()
    _native_enum_item_refs.clear()
    _registry = None
    _storage_override = None
    _recovery_path, _recovery_document, _recovery_plan, _recovery_blocked = "", None, None, False
    _recovery_records, _recovery_filenames = (), ()
    _recovery_error, _recovery_detail, _recovery_progress = "", "", ""
    _reset_theme_status()
    _recovery_decisions.clear()
    _palette_map = _detail_map = _detail_items = ()
    _palette_keys = {}
    _detail_context_items = ()
    _detail_context_labels = {}
    _detail_context_cache.clear()
