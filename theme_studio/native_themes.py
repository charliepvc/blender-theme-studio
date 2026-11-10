"""Blender-native theme XML and preset adapter."""

import importlib
import os
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

from .native_theme_files import _canonical, theme_output_paths, validate_theme_name, write_theme_files


class ProtectedThemeCollision(PermissionError):
    """A matching built-in or extension preset cannot be overwritten."""

    def __init__(self, paths):
        self.paths = tuple(Path(path) for path in paths)
        super().__init__("Protected native theme collision: " + ", ".join(map(str, self.paths)))


def _blender_modules():
    return {
        "bpy": importlib.import_module("bpy"),
        "preset": importlib.import_module("bl_operators.presets"),
        "menu": importlib.import_module("bpy.types").USERPREF_MT_interface_theme_presets,
        "xml": importlib.import_module("_rna_xml"),
    }


def _roots(context, modules):
    user_path = modules["bpy"].utils.user_resource("SCRIPTS", path="presets/interface_theme", create=False)
    user_root = Path(user_path).resolve() if user_path else None
    roots = tuple(Path(path).resolve() for path in modules["bpy"].utils.preset_paths("interface_theme"))
    return user_root, roots


def configured_libraries(context):
    return [(library.name, library.path) for library in context.preferences.filepaths.asset_libraries]


def _normalized(name, modules):
    return validate_theme_name(name, modules["preset"].AddPresetBase.as_filename(name))


def _read(path):
    try:
        return path.read_bytes()
    except FileNotFoundError:
        return None


def _casefold_matches(directories, stem):
    matches = []
    for directory in directories:
        if not directory.is_dir():
            continue
        for path in directory.rglob("*"):
            if not path.is_file() or path.suffix.casefold() != ".xml":
                continue
            if path.stem.casefold() == stem.casefold():
                matches.append(_canonical(path))
    return tuple(dict.fromkeys(matches))


def plan_native_theme(context, name, library_path):
    """Return {'paths': tuple, 'expected': dict}; expected maps old bytes or None.

    Only exact selected-library and user-preset files are writable. Any other
    casefold name match is protected. Planning performs no filesystem writes.
    """
    modules = _blender_modules()
    libraries = configured_libraries(context)
    selected = next((path for _, path in libraries if os.path.normcase(os.path.realpath(path)) == os.path.normcase(os.path.realpath(library_path))), None)
    if selected is None:
        raise ValueError(f"Selected asset library is no longer configured: {library_path}")
    root = Path(selected)
    if not root.is_dir():
        raise FileNotFoundError(f"Selected asset library is unavailable: {root}")
    if not os.access(root, os.W_OK):
        raise PermissionError(f"Selected asset library is not writable: {root}")
    preset_root, native_roots = _roots(context, modules)
    if preset_root is None:
        scripts = modules["bpy"].utils.user_resource("SCRIPTS", create=False)
        if not scripts:
            scripts = os.environ.get("BLENDER_USER_SCRIPTS") or str(
                Path(modules["bpy"].utils.resource_path("USER")) / "scripts")
        preset_root = Path(scripts) / "presets" / "interface_theme"
    stem = _normalized(name, modules)
    paths = theme_output_paths(root, preset_root, stem)
    writable = {path.resolve() for path in paths}
    library_matches = _casefold_matches((root / "themes",), stem)
    library_path_for_name = paths[0]
    if library_matches:
        library_path_for_name = library_matches[0]
        paths = tuple(dict.fromkeys((library_path_for_name, *library_matches[1:], *paths[1:])))
    writable.update(path.resolve() for path in paths if path.parent.resolve() == (root / "themes").resolve())
    protected = [path for path in _casefold_matches(native_roots, stem) if path not in writable]
    if protected:
        raise ProtectedThemeCollision(protected)
    expected = {path: _read(path) for path in paths}
    for directory in (root / "themes", preset_root):
        if directory.exists() and not directory.is_dir():
            raise NotADirectoryError(directory)
    return {"paths": paths, "expected": expected, "stem": stem}


def _serialize(context, modules):
    descriptor, filename = tempfile.mkstemp(suffix=".xml")
    os.close(descriptor)
    try:
        modules["xml"].xml_file_write(context, filename, modules["menu"].preset_xml_map)
        data = Path(filename).read_bytes()
        _validate_xml_bytes(data, modules)
        return data
    finally:
        Path(filename).unlink(missing_ok=True)


def _validate_xml_bytes(data, modules):
    upper = data.upper()
    if b"<!DOCTYPE" in upper or b"<!ENTITY" in upper:
        raise ValueError("Native theme XML document declarations are not allowed")
    try:
        root = ET.fromstring(data)
    except ET.ParseError as error:
        raise ValueError(f"Invalid native theme XML: {error}") from error
    if root.tag != "bpy" or len(root) != 2 or {child.tag for child in root} != {"Theme", "ThemeStyle"}:
        raise ValueError("Native theme XML must contain Theme and ThemeStyle roots")
    allowed = set(modules["menu"].preset_xml_secure_types)
    if any(node.tag[0].isupper() and node.tag not in allowed for node in root.iter() if node is not root):
        raise ValueError("Native theme XML contains a type outside Blender's secure allow-list")


def save_native_theme(context, name, library_path, *, expected):
    modules = _blender_modules()
    plan = plan_native_theme(context, name, library_path)
    if expected is None:
        raise ValueError("Explicit expected-byte map is required")
    paths = plan["paths"]
    library_theme_dir = Path(next(path for _, path in configured_libraries(context) if os.path.normcase(os.path.realpath(path)) == os.path.normcase(os.path.realpath(library_path)))).resolve() / "themes"
    user_resource = modules["bpy"].utils.user_resource("SCRIPTS", path="presets/interface_theme", create=True)
    user_theme_dir = Path(user_resource).resolve()
    if paths[-1].parent != user_theme_dir or library_theme_dir not in [path.parent.resolve() for path in paths]:
        raise FileExistsError("Native theme destinations changed since planning; confirm again")
    if set(expected) != set(plan["paths"]):
        raise ValueError("Expected-byte map must match planned theme paths")
    if any(_read(path) != expected[path] for path in paths):
        raise FileExistsError("Native theme destinations changed since planning; confirm again")
    data = _serialize(context, modules)
    for path in paths:
        if path.parent == library_theme_dir:
            path.parent.mkdir(exist_ok=True)
        elif not path.parent.is_dir():
            raise FileNotFoundError(f"Blender user theme preset directory is unavailable: {path.parent}")
    write_theme_files(data, paths, expected=expected)
    context.preferences.themes[0].filepath = str(paths[-1])
    return tuple(map(str, paths))


def export_native_theme(context, filepath, *, expected):
    modules = _blender_modules()
    path = _canonical(Path(filepath))
    user_root, preset_roots = _roots(context, modules)
    if any(root != user_root and path.is_relative_to(root) for root in preset_roots):
        raise ProtectedThemeCollision((path,))
    if path not in expected:
        raise ValueError("Expected-byte map must include export destination")
    data = _serialize(context, modules)
    if path.parent.exists() is False:
        raise FileNotFoundError(f"Output directory does not exist: {path.parent}")
    write_theme_files(data, (path,), expected=expected)


def _preset_roots(context, modules):
    _, preset_roots = _roots(context, modules)
    return preset_roots


def native_theme_presets():
    modules = _blender_modules()
    context = modules["bpy"].context
    roots = _preset_roots(context, modules)
    user_path = modules["bpy"].utils.user_resource("SCRIPTS", path="presets/interface_theme", create=False)
    user_root = Path(user_path).resolve() if user_path else None
    found = []
    seen = set()
    for root in roots:
        if not root.is_dir():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.casefold() != ".xml":
                continue
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            try:
                validate_native_preset(str(resolved))
            except (OSError, ValueError):
                continue
            found.append((path.stem, str(resolved), user_root is not None and resolved.parent.resolve() == user_root))
    return sorted(found, key=lambda item: (item[0].casefold(), item[1]))


def _resolved_preset(filepath, modules):
    path = Path(filepath).resolve(strict=True)
    context = modules["bpy"].context
    roots = tuple(root.resolve() for root in _preset_roots(context, modules) if root.exists())
    if not any(path.is_relative_to(root) for root in roots):
        raise ValueError(f"Theme preset is outside native preset roots: {path}")
    if path.suffix.casefold() != ".xml":
        raise ValueError(f"Not a native theme XML preset: {path}")
    return path


def validate_native_preset(filepath):
    modules = _blender_modules()
    path = _resolved_preset(filepath, modules)
    _validate_xml_bytes(path.read_bytes(), modules)


def _snapshot(context, modules):
    data = _serialize(context, modules)
    themes = context.preferences.themes
    return data, tuple(theme.filepath for theme in themes)


def _restore(context, modules, snapshot):
    data, filepaths = snapshot
    descriptor, filename = tempfile.mkstemp(suffix=".xml")
    os.close(descriptor)
    try:
        Path(filename).write_bytes(data)
        _execute_preset(modules, filename)
        if _serialize(context, modules) != data:
            raise RuntimeError("Restored native appearance does not match recovery snapshot")
        for theme, filepath in zip(context.preferences.themes, filepaths):
            theme.filepath = filepath
    except Exception as error:
        raise RuntimeError(f"Native recovery snapshot retained at: {filename}; {error}") from error
    else:
        Path(filename).unlink(missing_ok=True)


def apply_native_theme(context, filepath):
    modules = _blender_modules()
    path = _resolved_preset(filepath, modules)
    _validate_xml_bytes(path.read_bytes(), modules)
    snapshot = _snapshot(context, modules)
    try:
        _execute_preset(modules, str(path))
        if not any(theme.filepath == str(path) for theme in context.preferences.themes):
            raise RuntimeError("Blender did not update active theme preset metadata")
    except Exception as error:
        try:
            _restore(context, modules, snapshot)
        except Exception as rollback_error:
            raise RuntimeError(f"Native theme apply failed: {error}; rollback failed: {rollback_error}") from error
        raise RuntimeError(f"Native theme apply failed and prior appearance was restored: {error}") from error


def _execute_preset(modules, filepath):
    result = modules["bpy"].ops.script.execute_preset(filepath=filepath, menu_idname="USERPREF_MT_interface_theme_presets")
    if "CANCELLED" in result:
        raise RuntimeError("Blender cancelled native theme preset execution")
