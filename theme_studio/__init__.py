"""
Theme Studio development addon; imports Blender UI only on registration.
"""

from importlib import import_module

bl_info = {
    "name": "Theme Studio",
    "author": "Theme Studio",
    "version": (0, 4, 0),
    "blender": (5, 2, 1),
    "location": "3D View > Sidebar > Theme Studio",
    "description": "Customize Blender colors with linked, reversible edits",
    "category": "Interface",
    "doc_url": "https://github.com/charliepvc/blender-theme-studio",
    "tracker_url": "https://github.com/charliepvc/blender-theme-studio/issues",
}


def register():
    translations = import_module(f"{__name__}.translations")
    translations.register()
    try:
        import_module(f"{__name__}.ui").register()
    except Exception:
        translations.unregister()
        raise


def unregister():
    import_module(f"{__name__}.ui").unregister()
    import_module(f"{__name__}.translations").unregister()
