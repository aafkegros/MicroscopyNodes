import bpy
from pathlib import Path


_progress_path = None


def set_progress_path(path):
    global _progress_path
    _progress_path = Path(path) if path is not None else None

def log(string):
    if _progress_path is not None:
        temporary_path = _progress_path.with_suffix(".tmp")
        temporary_path.write_text(str(string), encoding="utf-8")
        temporary_path.replace(_progress_path)
        return None
    bpy.context.scene.MiN_progress_str = string
    return None


def clear_progress():
    bpy.context.scene.MiN_progress_str = ""
    return None
