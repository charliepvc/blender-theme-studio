"""
Theme Studio development addon; imports Blender UI only on registration.
"""

from importlib import import_module

bl_info = {
    "name": "Theme Studio",
    "author": "Theme Studio",
    "version": (0, 4, 0),
    "blender": (5, 2, 1),
    "location": "Vista 3D > Barra laterale > Theme Studio",
    "description": "Personalizza i colori di Blender con modifiche collegate e reversibili",
    "category": "Interface",
    "doc_url": "https://github.com/charliepvc/blender-theme-studio",
    "tracker_url": "https://github.com/charliepvc/blender-theme-studio/issues",
}


def register():
    import_module(f"{__name__}.ui").register()


def unregister():
    import_module(f"{__name__}.ui").unregister()
