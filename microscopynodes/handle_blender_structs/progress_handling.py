import bpy

def log(string):
    bpy.context.scene.MiN_progress_str = string
    return None
