"""Blender-facing helpers.

Import helper modules directly instead of using this package as a barrel.
Keeping package import lightweight makes circular imports much easier to spot
and avoids loading UI, node, and object code from unrelated constants imports.
"""
