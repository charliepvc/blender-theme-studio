"""Curated palette families and complete human-readable detail routing."""

from colorsys import rgb_to_hsv, hsv_to_rgb
import math


_PREFIX = "preferences.themes[0]."
_ROLE_LIMITS = {"surface": (0.08, 0.04, 15), "indicator": (0.15, 0.06, 20),
                "text": (0.08, 0.04, 15)}
_NEUTRAL_EPSILON = 0.01
_GAMUT_ROUNDOFF = 2e-7
_GAMUT_STEPS = 24
_LIGHTNESS_TOLERANCE = 0.0005
_MATRIX_FWD = ((0.4122214708, 0.5363325363, 0.0514459929),
               (0.2119034982, 0.6806995451, 0.1073969566),
               (0.0883024619, 0.2817188376, 0.6299787005))
_MATRIX_INV = ((4.0767416621, -3.3077115913, 0.2309699292),
               (-1.2684380046, 2.6097574011, -0.3413193965),
               (-0.0041960863, -0.7034186147, 1.7076147010))
_MAIN_GROUPS = (
    ("backgrounds", "Backgrounds", "Editor canvas backgrounds", "surfaces.canvas", ()),
    ("panels", "Panels", "Panels, sidebars, asset shelf, headers and time ruler backgrounds", None,
     ("surfaces.panels", "surfaces.sidebars", "surfaces.asset_shelf", "surfaces.headers",
      "surfaces.scrubbing")),
    ("text", "Text", "Control and editor text", None,
     ("text.controls", "text.editor", "text.panels", "text.titles", "text.headers", "text.header_highlights")),
    ("controls", "Controls", "Control surfaces and indicators", None,
     ("surfaces.controls", "symbols.control_indicators")),
    ("borders", "Borders", "Interface borders and outlines", None, ("borders.controls",)),
    ("selection", "Selection", "Selected items outside the 3D View", None,
     ("states.control_selection",)),
    ("active", "Active", "General active indicators", None, ()),
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
    ("background", "Background", ("surfaces.viewport_gradient", "surfaces.viewport_masks")),
    ("headers", "Headers and text", ("surfaces.headers", "text.editor", "text.titles",
                                    "text.headers", "text.header_highlights")),
    ("selection", "Selection and modes", ("states.object_selection", "states.mesh_selection",
                                              "symbols.face_orientation", "symbols.mesh_attributes")),
    ("guides", "Guides and grids", ("guides.viewport_grid", "guides.viewport_clipping",
                                    "guides.mesh_topology", "guides.mesh_markers")),
)


_DETAIL_LABELS = {
    "surfaces": "Surfaces", "text": "Text", "states": "States", "symbols": "Symbols",
    "guides": "Guides", "geometry": "Geometry", "connections": "Connections",
    "typography": "Typography", "borders": "Borders",
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
        paths = tuple(dict.fromkeys(paths))
        anchor = next((path for path in paths if path == {
            "backgrounds": _PREFIX + "properties.space.back",
            "panels": _PREFIX + "user_interface.panel_back",
            "text": _PREFIX + "user_interface.wcol_regular.text",
            "controls": _PREFIX + "user_interface.wcol_regular.inner",
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


def _dot(row, vector):
    return sum(a * b for a, b in zip(row, vector))


def _decode(channel):
    return channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4


def _encode(channel):
    return 12.92 * channel if channel <= 0.0031308 else 1.055 * channel ** (1 / 2.4) - 0.055


def _oklch(rgb):
    linear = tuple(_decode(channel) for channel in rgb[:3])
    lms = tuple(math.copysign(abs(_dot(row, linear)) ** (1 / 3), _dot(row, linear))
                for row in _MATRIX_FWD)
    lightness = 0.2104542553 * lms[0] + 0.7936177850 * lms[1] - 0.0040720468 * lms[2]
    a = 1.9779984951 * lms[0] - 2.4285922050 * lms[1] + 0.4505937099 * lms[2]
    b = 0.0259040371 * lms[0] + 0.7827717662 * lms[1] - 0.8086757660 * lms[2]
    return lightness, math.hypot(a, b), math.degrees(math.atan2(b, a)) % 360


def _linear_rgb(lightness, chroma, hue):
    angle = math.radians(hue)
    a, b = chroma * math.cos(angle), chroma * math.sin(angle)
    l_root = lightness + 0.3963377774 * a + 0.2158037573 * b
    m_root = lightness - 0.1055613458 * a - 0.0638541728 * b
    s_root = lightness - 0.0894841775 * a - 1.2914855480 * b
    lms = (l_root ** 3, m_root ** 3, s_root ** 3)
    return tuple(_dot(row, lms) for row in _MATRIX_INV)


def _in_gamut(rgb):
    return all(-_GAMUT_ROUNDOFF <= channel <= 1 + _GAMUT_ROUNDOFF for channel in rgb)


def _from_oklch(lightness, chroma, hue):
    if lightness <= 0 or lightness >= 1:
        return (float(lightness >= 1),) * 3
    low, high = 0.0, chroma
    linear = _linear_rgb(lightness, chroma, hue)
    if not _in_gamut(linear):
        linear = _linear_rgb(lightness, 0.0, hue)
        for _ in range(_GAMUT_STEPS):
            middle = (low + high) / 2
            candidate = _linear_rgb(lightness, middle, hue)
            if _in_gamut(candidate):
                low, linear = middle, candidate
            else:
                high = middle
            if high - low <= _LIGHTNESS_TOLERANCE:
                break
    return tuple(min(1.0, max(0.0, _encode(channel))) for channel in linear)


def _hue_delta(member, anchor):
    return (member - anchor + 180) % 360 - 180


def _derive_role(anchor_baseline, member_baseline, intent, role):
    from .core import _validate_rgb

    intent = _validate_rgb(intent)
    if tuple(intent) == tuple(anchor_baseline[:3]):
        return list(member_baseline)
    if tuple(member_baseline[:3]) == tuple(anchor_baseline[:3]):
        return list(intent) + list(member_baseline[3:])
    d_lightness, d_chroma, d_hue = _ROLE_LIMITS[role]
    base_anchor, base_member, target = (_oklch(rgb) for rgb in
                                       (anchor_baseline, member_baseline, intent))
    lightness = min(1.0, max(0.0, target[0] + max(-d_lightness,
                         min(d_lightness, base_member[0] - base_anchor[0]))))
    hue_offset = 0 if min(base_anchor[1], base_member[1]) <= _NEUTRAL_EPSILON else max(
        -d_hue, min(d_hue, _hue_delta(base_member[2], base_anchor[2])))
    hue = (target[2] + hue_offset) % 360
    chroma_delta = max(-d_chroma, min(d_chroma, base_member[1] - base_anchor[1]))
    chroma = 0 if target[1] <= _NEUTRAL_EPSILON else max(0.0, target[1] + chroma_delta)
    return list(_from_oklch(lightness, chroma, hue)) + list(member_baseline[3:])


def _contrast_ratio(first, second):
    def luminance(rgb):
        linear = tuple(_decode(channel) for channel in rgb[:3])
        return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

    a, b = luminance(first), luminance(second)
    return (max(a, b) + 0.05) / (min(a, b) + 0.05)


def _resolve_foreground(intent, background, threshold):
    source = tuple(intent[:3])
    if _contrast_ratio(source, background[:3]) >= threshold:
        return list(intent)
    lightness, chroma, hue = _oklch(source)
    passing = []
    for endpoint in (0.0, 1.0):
        endpoint_rgb = _from_oklch(endpoint, chroma, hue)
        if _contrast_ratio(endpoint_rgb, background[:3]) < threshold:
            continue
        failing_l, passing_l = lightness, endpoint
        for _ in range(_GAMUT_STEPS):
            middle = (failing_l + passing_l) / 2
            candidate = _from_oklch(middle, chroma, hue)
            if _contrast_ratio(candidate, background[:3]) >= threshold:
                passing_l = middle
            else:
                failing_l = middle
            if abs(passing_l - failing_l) <= _LIGHTNESS_TOLERANCE:
                break
        candidate = _from_oklch(passing_l, chroma, hue)
        passing.append((candidate, abs(_oklch(candidate)[0] - lightness)))
    if not passing:
        return list(intent)
    return list(min(passing, key=lambda result: result[1])[0]) + list(intent[3:])


def _resolve_foreground_all(intent, constraints, *, native_8bit=False):
    constraints = tuple(sorted(constraints, key=lambda item: (tuple(item[0][:3]), item[1])))
    if len(constraints) == 1 and not native_8bit:
        background, threshold = constraints[0]
        return _resolve_foreground(intent, background, threshold)
    source = tuple(intent[:3])

    def native_rgb(rgb):
        return (tuple(min(255, max(0, int(channel * 255 + 0.5))) / 255
                      for channel in rgb[:3]) if native_8bit else tuple(rgb[:3]))

    def passes(rgb):
        rgb = native_rgb(rgb)
        return all(_contrast_ratio(rgb, native_rgb(background)) >= threshold
                   for background, threshold in constraints)

    if passes(source):
        return list(intent)
    lightness, chroma, hue = _oklch(source)
    passing = []
    endpoints = {}
    for endpoint in (0.0, 1.0):
        candidate = _from_oklch(endpoint, chroma, hue)
        endpoints[endpoint] = candidate
        if not passes(candidate):
            continue
        failing_l, passing_l = lightness, endpoint
        for _ in range(_GAMUT_STEPS):
            middle = (failing_l + passing_l) / 2
            candidate = _from_oklch(middle, chroma, hue)
            if passes(candidate):
                passing_l = middle
            else:
                failing_l = middle
            if abs(passing_l - failing_l) <= _LIGHTNESS_TOLERANCE:
                break
        candidate = _from_oklch(passing_l, chroma, hue)
        passing.append((abs(_oklch(candidate)[0] - lightness), candidate))
    if passing:
        return list(min(passing, key=lambda result: (result[0], result[1]))[1]) + list(intent[3:])

    # Incompatible constraints: choose deterministic best-effort candidate, never claim all pass.
    candidates = [source, *endpoints.values()]
    candidates.extend(_resolve_foreground(intent, background, threshold)[:3]
                      for background, threshold in constraints)
    best = max(candidates, key=lambda rgb: (
        min(_contrast_ratio(native_rgb(rgb), native_rgb(background))
            for background, _threshold in constraints),
        -abs(_oklch(rgb)[0] - lightness), tuple(-channel for channel in rgb)))
    return list(best) + list(intent[3:])


def _text_pairs(registry, text_paths, values):
    from .contrast import contrast_pair_applies, contrast_pairs

    return tuple(pair for pair in contrast_pairs(registry)
                 if pair["role"] == "text" and pair["foreground"] in text_paths
                 and contrast_pair_applies(pair, values))


def _text_candidate(registry, path, backgrounds, intent, baseline, current, text_anchor,
                   direct_intent=False):
    from .core import _validate_rgb

    baseline_anchor = baseline[text_anchor]
    source = baseline[path]
    if (tuple(intent) == tuple(baseline_anchor[:3])
            and all(tuple(background) == tuple(baseline[background_path])
                    for background_path, background, _threshold, _opaque, _native in backgrounds)):
        return list(source)
    derived = list(intent) if direct_intent else _derive_role(baseline_anchor, source, intent, "text")
    foreground_spec = registry.fields[path]
    if foreground_spec.subtype != "COLOR_GAMMA":
        return transform_color(source, baseline_anchor, intent)
    if foreground_spec.length == 4 and current[path][3] < 1:
        return derived
    constraints = []
    native_8bit = False
    for background_path, background, threshold, opaque, native in backgrounds:
        spec = registry.fields[background_path]
        if spec.subtype != "COLOR_GAMMA":
            continue
        if len(background) == 4 and background[3] < 1 and not opaque:
            continue
        constraints.append((background, 4.51))
        native_8bit = native_8bit or native
    if not constraints:
        return derived
    adjusted = _resolve_foreground_all(derived, tuple(constraints), native_8bit=native_8bit)
    return list(_validate_rgb(adjusted[:3])) + list(source[3:])


def _member_role(group, spec):
    if group == "backgrounds":
        return "surface"
    if group == "panels":
        return "surface" if spec.group.startswith("surfaces.") else "text"
    if group == "text" or group == "borders":
        return "text"
    if group == "controls":
        return ("surface" if spec.group == "surfaces.controls"
                else "indicator" if spec.group == "symbols.control_indicators" else None)
    if group == "selection":
        return "surface"
    if group == "active":
        return "indicator" if spec.group.startswith("states.") else "text"
    return None


def coordinated_palette_updates(registry, baseline, current, protected, intents, changed_key):
    """Resolve one parent edit and its fixed, evidence-backed dependency closure."""
    from .contrast import contrast_pair_applies, contrast_pairs

    groups = {group["id"]: group for group in palette_groups(registry)[:7]}
    group = groups.get(changed_key)
    if group is None:
        from .core import ValidationError
        raise ValidationError("Invalid palette group")
    intent = _validate_rgb(intents[changed_key])
    anchor_path = group["anchor"]
    updates = {}

    def preserve_alpha(path, value):
        if registry.fields[path].length == 4:
            value = list(value[:3]) + [current[path][3]]
        return registry.fields[path].validate(value)

    def effective_background(path):
        return current[path] if path in protected or path not in updates else updates[path]

    def source_transform(path, role=None):
        role = role or _member_role(changed_key, registry.fields[path])
        if role:
            value = _derive_role(baseline[anchor_path], baseline[path], intent, role)
        else:
            value = transform_color(baseline[path], baseline[anchor_path], intent)
        updates[path] = preserve_alpha(path, value)

    for path in group["paths"]:
        role = None
        if changed_key == "controls":
            semantic_group = registry.fields[path].group
            if semantic_group == "surfaces.controls":
                role = "surface"
            elif semantic_group == "symbols.control_indicators":
                role = "indicator"
        source_transform(path, role)

    text_group = groups["text"]
    border_group = groups["borders"]
    text_paths = set(text_group["paths"])
    all_pairs = tuple(pair for pair in contrast_pairs(registry)
                      if contrast_pair_applies(pair, current))
    pairs = tuple(pair for pair in all_pairs
                  if pair["role"] == "text" and pair["foreground"] in text_paths)
    if changed_key in {"backgrounds", "panels"}:
        pairs = tuple(pair for pair in pairs if pair["background"] in group["paths"])
    elif changed_key == "controls":
        pairs = tuple(pair for pair in all_pairs
                      if pair["background"] in group["paths"]
                      and (pair["role"] in {"border", "indicator"}
                           or (pair["role"] == "text" and pair["foreground"].endswith(".text"))))
    elif changed_key == "text":
        pairs = tuple(pair for pair in pairs if pair["foreground"] in text_paths) + tuple(
            pair for pair in all_pairs if pair.get("direct_intent")
            and pair.get("intent_owner") == "text")
    elif changed_key == "borders":
        pairs = tuple(pair for pair in all_pairs
                      if pair["role"] == "border" and pair["foreground"] in group["paths"])
    elif changed_key == "selection":
        pairs = tuple(pair for pair in all_pairs
                      if pair["background"] in group["paths"]
                      and pair["role"] in {"text", "border"})
    elif changed_key == "active":
        pairs = tuple(pair for pair in all_pairs
                      if pair["role"] == "text" and pair.get("direct_intent")
                      and pair["background"] in group["paths"])
    else:
        return updates
    if not pairs:
        return updates

    def source_intent(key):
        anchor = groups[key]["anchor"]
        if anchor not in baseline:
            return None
        return _validate_rgb(intents[key] if key in intents else baseline[anchor][:3])

    text_foregrounds = {pair["foreground"] for pair in pairs if pair["role"] == "text"}
    all_text_pairs = {}
    text_intent_owners = {}
    for pair in all_pairs:
        if pair["role"] == "text" and pair["foreground"] in text_foregrounds:
            all_text_pairs.setdefault(pair["foreground"], []).append(pair)
            text_intent_owners[pair["foreground"]] = pair.get("intent_owner", "text")
    for path in sorted(all_text_pairs):
        intent_owner = text_intent_owners[path]
        text_intent = source_intent(intent_owner)
        if text_intent is None:
            continue
        intent_anchor = groups[intent_owner]["anchor"]
        backgrounds = tuple((pair["background"], effective_background(pair["background"]),
                             pair["threshold"], pair.get("background_is_opaque", False),
                             pair.get("native_8bit", False))
                            for pair in all_text_pairs[path])
        value = _text_candidate(registry, path, backgrounds, text_intent,
                                baseline, current, intent_anchor,
                                direct_intent=any(pair.get("direct_intent")
                                                  for pair in all_text_pairs[path]))
        updates[path] = preserve_alpha(path, value)

    for pair in pairs:
        if pair["role"] == "text":
            continue
        path, background_path = pair["foreground"], pair["background"]
        background = effective_background(background_path)
        if pair["role"] == "border":
            border_intent = source_intent("borders")
            if border_intent is None:
                continue
            value = _derive_role(baseline[border_group["anchor"]], baseline[path],
                                 border_intent, "text")
        else:
            control_intent = source_intent("controls")
            if control_intent is None:
                continue
            value = _derive_role(baseline[groups["controls"]["anchor"]], baseline[path],
                                 control_intent, "indicator")
        foreground_spec = registry.fields[path]
        background_spec = registry.fields[background_path]
        opaque = ((foreground_spec.length != 4 or current[path][3] == 1)
                  and (background_spec.length != 4 or background[3] == 1))
        if (pair["role"] == "indicator" and foreground_spec.subtype == "COLOR_GAMMA"
                and background_spec.subtype == "COLOR_GAMMA" and opaque):
            value = _resolve_foreground(value, background, pair["threshold"])
        updates[path] = preserve_alpha(path, value)

    if changed_key == "text":
        paired = {pair["foreground"] for pair in pairs}
        for path in text_group["paths"]:
            if path not in paired:
                source_transform(path)
    return updates
