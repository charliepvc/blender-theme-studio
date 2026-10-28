"""Narrow Blender RNA adapter. No operators, UI, timers or preference saves."""

from __future__ import annotations

import threading

from .core import ValidationError


class BlenderBackend:
    def __init__(self, registry):
        self._main_thread()
        import bpy

        self._bpy = bpy
        self.registry = registry
        if bpy.app.build_hash.decode() != registry.build_hash:
            raise ValidationError("This Blender build has not been verified against the bundled catalog")
        for path, spec in registry.fields.items():
            owner_path, identifier = path.rsplit(".", 1)
            try:
                owner = bpy.context.path_resolve(owner_path)
                prop = owner.bl_rna.properties[identifier]
            except (ValueError, KeyError, AttributeError) as exc:
                raise ValidationError(f"Catalog field unavailable: {path}") from exc
            if prop.type != spec.kind or getattr(prop, "array_length", 0) != spec.length:
                raise ValidationError(f"Catalog type mismatch: {path}")
            if prop.is_readonly and spec.editable:
                raise ValidationError(f"Catalog field is read-only: {path}")
            if spec.kind in {"FLOAT", "INT"}:
                if prop.subtype != spec.subtype or prop.hard_min != spec.minimum or prop.hard_max != spec.maximum:
                    raise ValidationError(f"Catalog numeric metadata mismatch: {path}")
            if spec.kind == "ENUM" and tuple(item.identifier for item in prop.enum_items) != tuple(spec.choices):
                raise ValidationError(f"Catalog enum mismatch: {path}")

    @staticmethod
    def _main_thread():
        if threading.current_thread() is not threading.main_thread():
            raise RuntimeError("Blender RNA must only be accessed from the main thread")

    @property
    def session_key(self):
        self._main_thread()
        # Different adapter instances must not permit concurrent theme sessions.
        return ("blender-preferences", self._bpy.context.preferences.as_pointer())

    def read(self, path):
        self._main_thread()
        if path not in self.registry.fields:
            raise ValidationError("Path is not in the verified theme catalog")
        value = self._bpy.context.path_resolve(path)
        if self.registry.fields[path].length:
            value = list(value)
        return self.registry.fields[path].validate(value)

    def write(self, path, value):
        self._main_thread()
        value = self.registry.validate({path: value}, allow_metadata=True)[path]
        owner_path, identifier = path.rsplit(".", 1)
        setattr(self._bpy.context.path_resolve(owner_path), identifier, value)

    def get_auto_save(self):
        self._main_thread()
        return self._bpy.context.preferences.use_preferences_save

    def set_auto_save(self, value):
        self._main_thread()
        if type(value) is not bool:
            raise ValidationError("Auto-save state must be boolean")
        self._bpy.context.preferences.use_preferences_save = value
