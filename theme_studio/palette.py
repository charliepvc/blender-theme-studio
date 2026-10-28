"""Curated palette families and complete human-readable detail routing."""

from colorsys import rgb_to_hsv, hsv_to_rgb


_PREFIX = "preferences.themes[0]."
_MAIN_GROUPS = (
    ("backgrounds", "Fondi", "Fondi canvas degli editor", "surfaces.canvas", ()),
    ("panels", "Pannelli", "Pannelli, sidebar, asset shelf e header", None,
     ("surfaces.panels", "surfaces.sidebars", "surfaces.asset_shelf", "surfaces.headers")),
    ("text", "Testi", "Testi di controlli ed editor", None,
     ("text.controls", "text.editor", "text.panels", "text.titles", "text.headers", "text.header_highlights")),
    ("controls", "Controlli", "Superfici e indicatori dei controlli", None,
     ("surfaces.controls", "symbols.control_indicators")),
    ("borders", "Bordi", "Bordi e contorni dell'interfaccia", None, ("borders.controls",)),
    ("selection", "Selezione", "Elementi selezionati fuori dalla Vista 3D", None,
     ("states.control_selection",)),
    ("active", "Attivi", "Indicatori attivi generali", None, ()),
)
_SELECTION_PATHS = (
    "outliner.selected_highlight", "outliner.selected_object", "node_editor.node_selected",
    "sequence_editor.selected_strip", "text_editor.selected_text", "console.select",
    "info.info_selected", "image_editor.vertex_select", "image_editor.edge_select",
    "image_editor.face_select", "image_editor.face_mode_select", "file_browser.selected_file",
)
_ACTIVE_PATHS = (
    "user_interface.panel_active", "user_interface.editor_outline_active", "outliner.active",
    "outliner.active_object", "node_editor.node_active", "sequence_editor.active_strip",
)
_VIEWPORT_GROUPS = (
    ("background", "Sfondo", ("surfaces.viewport_gradient", "surfaces.viewport_masks")),
    ("headers", "Header e testi", ("surfaces.headers", "text.editor", "text.titles",
                                    "text.headers", "text.header_highlights")),
    ("selection", "Selezione e modalità", ("states.object_selection", "states.mesh_selection",
                                              "symbols.face_orientation", "symbols.mesh_attributes")),
    ("guides", "Griglie e guide", ("guides.viewport_grid", "guides.viewport_clipping",
                                    "guides.mesh_topology", "guides.mesh_markers")),
)


_DETAIL_LABELS = {
    "surfaces": "Superfici", "text": "Testi", "states": "Stati", "symbols": "Simboli",
    "guides": "Guide e griglie", "geometry": "Forme", "connections": "Collegamenti",
    "typography": "Caratteri", "borders": "Bordi",
}


def palette_groups(registry):
    result = []
    colors = {path: spec for path, spec in registry.fields.items()
              if spec.editable and spec.subtype in {"COLOR", "COLOR_GAMMA"}}
    for key, label, description, category, categories in _MAIN_GROUPS:
        paths = tuple(path for path, spec in colors.items() if (
            (category is not None and spec.group == category)
            or (category is None and spec.group in categories
                and not (key == "panels" and path.endswith(".view_3d.space.header"))
                and not (key == "text" and path.startswith(_PREFIX + "view_3d.")))))
        if key == "backgrounds":
            paths = tuple(path for path in paths if not path.startswith(_PREFIX + "view_3d."))
        if key == "selection":
            paths += tuple(_PREFIX + path for path in _SELECTION_PATHS if _PREFIX + path in colors)
            paths += tuple(path for path, spec in colors.items() if spec.group == "states.file_selection")
        if key == "active":
            paths = tuple(_PREFIX + path for path in _ACTIVE_PATHS if _PREFIX + path in colors)
        if key == "panels":
            paths += tuple(path for path in colors if path in {
                _PREFIX + "user_interface.editor_outline", _PREFIX + "user_interface.panel_outline"})
        if key == "text":
            if registry.build_hash == "9e2066aef7ef":
                paths += tuple(path for path, spec in colors.items()
                               if spec.group in {"text.titles", "text.headers", "text.header_highlights"}
                               and not path.startswith(_PREFIX + "view_3d."))
        anchor = next((path for path in paths if path == {
            "backgrounds": _PREFIX + "properties.space.back",
            "panels": _PREFIX + "user_interface.panel_back",
            "text": _PREFIX + "user_interface.wcol_regular.text",
            "controls": _PREFIX + "user_interface.wcol_regular.item",
            "borders": _PREFIX + "user_interface.wcol_regular.outline",
            "selection": _PREFIX + "user_interface.wcol_regular.inner_sel",
            "active": _PREFIX + "user_interface.panel_active",
        }[key]), None) or (paths[0] if paths else None)
        result.append({"id": key, "label": label, "description": description,
                       "anchor": anchor, "paths": paths})
    viewport = []
    view3d = {path: spec for path, spec in colors.items() if path.startswith(_PREFIX + "view_3d.")}
    for key, label, categories in _VIEWPORT_GROUPS:
        paths = tuple(path for path, spec in view3d.items() if spec.group in categories)
        viewport.append({"id": key, "label": label, "paths": paths})
    result.append({"id": "viewport", "label": "Vista 3D", "groups": tuple(viewport),
                   "details": tuple(path for path in view3d if not any(
                       path in group["paths"] for group in viewport))})
    return tuple(result)


def palette_group(registry, key):
    return next((group for group in palette_groups(registry) if group["id"] == key), None)


def detail_categories(registry):
    groups = {}
    for path, spec in registry.fields.items():
        if not spec.editable:
            continue
        category = spec.group.split(".", 1)[0]
        groups.setdefault(category, []).append(path)
    return tuple({"id": key, "label": _DETAIL_LABELS.get(key, key.replace("_", " ").title()),
                  "paths": tuple(paths)} for key, paths in groups.items())


def roundness_paths(registry):
    return tuple(path for path in registry.editable_paths
                 if path.startswith(_PREFIX + "user_interface.wcol_") and path.endswith(".roundness"))


def viewport_background_paths(registry, mode):
    base = _PREFIX + "view_3d.space.gradients."
    enum_path = base + "background_type"
    if enum_path not in registry.editable_paths:
        return ()
    if mode == "SINGLE_COLOR":
        colors = (base + "high_gradient",)
    elif mode in {"LINEAR", "RADIAL"}:
        colors = (base + "high_gradient", base + "gradient")
    else:
        colors = ()
    return (enum_path, *(path for path in colors if path in registry.editable_paths))


def _validate_rgb(rgb):
    from .core import _validate_rgb as validate
    return validate(rgb)


def transform_color(value, baseline_anchor, target):
    """Apply HSV hue/saturation offsets and baseline brightness ratio, bounded to RGB."""
    from .core import ValidationError
    target = _validate_rgb(target)
    if len(value) not in {3, 4} or len(baseline_anchor) not in {3, 4}:
        raise ValidationError("Palette color requires RGB or RGBA values")
    for channel in (*value[:3], *baseline_anchor[:3]):
        if type(channel) not in {int, float} or not 0 <= channel <= 1:
            raise ValidationError("Invalid baseline palette color")
    if tuple(target) == tuple(baseline_anchor[:3]):
        return list(value)
    if tuple(value[:3]) == tuple(baseline_anchor[:3]):
        return list(target) + list(value[3:])
    anchor_h, anchor_s, anchor_v = rgb_to_hsv(*baseline_anchor[:3])
    target_h, target_s, target_v = rgb_to_hsv(*target)
    h, s, v = rgb_to_hsv(*value[:3])
    hue_offset = h - anchor_h if anchor_s > 0 and s > 0 else 0.0
    hue = (target_h + hue_offset) % 1.0 if target_s > 0 else h
    saturation = max(0.0, min(1.0, target_s + s - anchor_s))
    if anchor_v > 0:
        brightness = max(0.0, min(1.0, target_v * (v / anchor_v)))
    else:
        brightness = max(0.0, min(1.0, target_v + v - anchor_v))
    result = list(hsv_to_rgb(hue, saturation, brightness))
    if len(value) == 4:
        result.append(value[3])
    return result
