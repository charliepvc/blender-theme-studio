"""Pure advisory contrast checks for explicitly mapped theme color pairs."""

from __future__ import annotations

import math

from .core import ValidationError


_ROOT = "preferences.themes[0]."


def contrast_pairs(registry):
    """Return explicit catalog-supported color relationships in stable order."""
    fields = registry.fields
    pairs = []

    def add(foreground, background, threshold, role, *, background_is_opaque=False,
            context=None, intent_owner=None, native_8bit=False, direct_intent=False,
            conditional=None):
        if foreground in fields and background in fields:
            pair = {"id": f"{foreground}|{background}", "foreground": foreground,
                    "background": background, "threshold": threshold, "role": role}
            if background_is_opaque:
                pair["background_is_opaque"] = True
                pair["context"] = context
            if intent_owner:
                pair["intent_owner"] = intent_owner
            if native_8bit:
                pair["native_8bit"] = True
            if direct_intent:
                pair["direct_intent"] = True
            if conditional:
                pair["conditional"] = conditional
            pairs.append(pair)

    for background, spec in fields.items():
        if not spec.editable or spec.group != "surfaces.canvas":
            continue
        owner = background.rsplit(".", 1)[0]
        for suffix in ("text", "text_hi"):
            foreground = owner + "." + suffix
            if foreground in fields and fields[foreground].group == "text.editor":
                add(foreground, background, 4.5, "text")

    for foreground, spec in fields.items():
        if (not spec.editable or spec.group not in {"text.headers", "text.header_highlights"}
                or ".view_3d." in foreground
                or not foreground.endswith((".space.header_text", ".space.header_text_hi"))):
            continue
        owner = foreground.rsplit(".", 1)[0]
        add(foreground, owner + ".header", 4.5, "text",
            background_is_opaque=True, context="non-overlap editor header")
        # Image and Node Editor headers can also draw in Asset Shelf header context.
        if owner.endswith(("image_editor.space", "node_editor.space")):
            add(foreground, _ROOT + "regions.asset_shelf.header_back", 4.5, "text")

    ui = _ROOT + "user_interface."
    add(ui + "panel_text", ui + "panel_back", 4.5, "text")
    add(ui + "panel_title", ui + "panel_header", 4.5, "text")

    outliner = _ROOT + "outliner."
    if (outliner + "selected_object" in fields and outliner + "selected_highlight" in fields
            and fields[outliner + "selected_object"].group == "states.outliner_selection"
            and fields[outliner + "selected_highlight"].group == "states.outliner_selection"):
        add(outliner + "selected_object", outliner + "selected_highlight", 4.5, "text",
            background_is_opaque=True, context="nonactive selected Outliner row",
            intent_owner="text", native_8bit=True, direct_intent=True)
    if (outliner + "active_object" in fields and outliner + "active" in fields
            and fields[outliner + "active_object"].group == "states.outliner_selection"
            and fields[outliner + "active"].group == "states.outliner_selection"):
        add(outliner + "active_object", outliner + "active", 4.5, "text",
            background_is_opaque=True, context="active selected Outliner row",
            intent_owner="text", native_8bit=True, direct_intent=True)

    role_groups = {"inner": "surfaces.controls", "inner_sel": "states.control_selection",
                   "text": "text.controls", "text_sel": "text.controls",
                   "outline": "borders.controls", "outline_sel": "borders.controls",
                   "item": "symbols.control_indicators"}
    owners = sorted({".".join(path.split(".")[:-1]) for path in fields if path.startswith(ui + "wcol_")
                     and path.rsplit(".", 1)[-1] in role_groups})
    grouped_fields = {}
    for path, spec in fields.items():
        if path.startswith(ui + "wcol_") and path.rsplit(".", 1)[-1] in role_groups:
            grouped_fields.setdefault(".".join(path.split(".")[:-1]), {})[path.rsplit(".", 1)[-1]] = (path, spec.group)
    for owner in owners:
        names = {name: path for name, (path, group) in grouped_fields[owner].items()
                 if group == role_groups[name]}
        if owner == ui + "wcol_pulldown":
            for header in ("topbar.space.header", "dopesheet_editor.space.header"):
                add(names.get("text"), _ROOT + header, 4.5, "text",
                    background_is_opaque=True, context="non-overlap editor header")
            view3d_header = _ROOT + "view_3d.space.header"
            add(names.get("text"), view3d_header, 4.5, "text",
                background_is_opaque=True, context="effective opaque View 3D header")
            add(names.get("text"), names.get("inner"), 4.5, "text",
                conditional=(view3d_header, "alpha_below_one"))
        else:
            add(names.get("text"), names.get("inner"), 4.5, "text")
        add(names.get("text_sel"), names.get("inner_sel"), 4.5, "text")
        add(names.get("outline"), names.get("inner"), 3.0, "border")
        add(names.get("outline_sel"), names.get("inner_sel"), 3.0, "border")
        add(names.get("item"), names.get("inner"), 3.0, "indicator")

    return tuple(sorted(pairs, key=lambda pair: pair["id"]))


def contrast_pair_applies(pair, values):
    """Return whether a conditional pair can be painted in supplied theme state."""
    condition = pair.get("conditional")
    if condition is None:
        return True
    path, predicate = condition
    value = values.get(path)
    return (predicate == "alpha_below_one" and isinstance(value, (list, tuple))
            and len(value) == 4 and value[3] < 1)


def analyze_contrast(registry, values):
    """Validate supplied color values, then assess mapped pairs where possible."""
    validated = registry.validate(values)
    results = []
    for pair in contrast_pairs(registry):
        result = dict(pair)
        if not contrast_pair_applies(pair, validated):
            result.update(ratio=None, below_threshold=None,
                          reason="Background is not applicable in this header state")
            results.append(result)
            continue
        foreground_path, background_path = pair["foreground"], pair["background"]
        if foreground_path not in validated or background_path not in validated:
            result.update(ratio=None, below_threshold=None, reason="Color value is missing")
            results.append(result)
            continue
        foreground_spec, background_spec = registry.fields[foreground_path], registry.fields[background_path]
        foreground = _color(validated[foreground_path], foreground_spec.length)
        background = _color(validated[background_path], background_spec.length)
        if foreground_spec.subtype != "COLOR_GAMMA" or background_spec.subtype != "COLOR_GAMMA":
            result.update(ratio=None, below_threshold=None,
                          reason="Scene-linear COLOR requires OCIO conversion; contrast is unassessed")
        elif (background_spec.length == 4 and background[3] < 1
              and not pair.get("background_is_opaque")):
            result.update(ratio=None, below_threshold=None, reason="Background is not opaque")
        elif foreground_spec.length == 4 and foreground[3] < 1:
            result.update(ratio=None, below_threshold=None,
                          reason="Translucent foreground depends on the runtime blend space")
        else:
            if pair.get("native_8bit"):
                fg_rgb = tuple(_linear(_native_byte_channel(c)) for c in foreground[:3])
                bg_rgb = tuple(_linear(_native_byte_channel(c)) for c in background[:3])
            else:
                fg_rgb = tuple(_linear(c) for c in foreground[:3])
                bg_rgb = tuple(_linear(c) for c in background[:3])
            ratio = (_luminance(fg_rgb) + 0.05) / (_luminance(bg_rgb) + 0.05)
            ratio = max(ratio, 1 / ratio)
            result.update(ratio=ratio, below_threshold=ratio < pair["threshold"])
        results.append(result)
    return tuple(results)


def _native_byte_channel(channel):
    return min(255, max(0, int(channel * 255 + 0.5))) / 255


def _color(value, length):
    if length not in (3, 4) or not isinstance(value, (list, tuple)) or len(value) != length:
        raise ValidationError("Contrast color must have three or four components")
    components = tuple(value)
    if any(type(component) not in (int, float) or not math.isfinite(component)
           or not 0 <= component <= 1 for component in components):
        raise ValidationError("Contrast color components must be finite numbers between 0 and 1")
    return components[:3] + ((components[3] if length == 4 else 1.0),)


def _linear(component):
    return component / 12.92 if component <= 0.04045 else ((component + 0.055) / 1.055) ** 2.4


def _luminance(rgb):
    return 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]
