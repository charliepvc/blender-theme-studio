"""Resolve picker context to reviewed Theme Studio destinations."""

_EDITORS = {
    "VIEW_3D": ("view_3d", "3D View"),
    "IMAGE_EDITOR": ("image_editor", "Image Editor"),
    "NODE_EDITOR": ("node_editor", "Node Editor"),
    "SEQUENCE_EDITOR": ("sequence_editor", "Sequencer"),
    "CLIP_EDITOR": ("clip_editor", "Movie Clip Editor"),
    "DOPESHEET_EDITOR": ("dopesheet_editor", "Dope Sheet"),
    "GRAPH_EDITOR": ("graph_editor", "Graph Editor"),
    "NLA_EDITOR": ("nla_editor", "NLA Editor"),
    "TEXT_EDITOR": ("text_editor", "Text Editor"),
    "CONSOLE": ("console", "Console"),
    "INFO": ("info", "Info"),
    "OUTLINER": ("outliner", "Outliner"),
    "PROPERTIES": ("properties", "Properties"),
    "FILE_BROWSER": ("file_browser", "File Browser"),
    "SPREADSHEET": ("spreadsheet", "Spreadsheet"),
    "PREFERENCES": ("preferences", "Preferences"),
}
_CONTROL_REGIONS = {"HEADER", "TOOL_HEADER", "UI", "TOOLS", "TOOL_PROPS"}


def resolve_target(area_type, region_type, *, button=False):
    """Return contextual editor or shared-control destination, or None."""
    if area_type not in _EDITORS or region_type not in _CONTROL_REGIONS | {"WINDOW"}:
        return None
    if button or region_type in _CONTROL_REGIONS:
        return {"kind": "controls", "editor_id": "", "label": "Shared Controls"}
    if region_type == "WINDOW" and area_type in _EDITORS:
        editor_id, label = _EDITORS[area_type]
        return {"kind": "editor", "editor_id": editor_id, "label": label}
    return None
