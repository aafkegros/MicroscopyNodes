import bpy

def log(string):
    bpy.context.scene.MiN_progress_str = string
    return None


def clear_progress():
    bpy.context.scene.MiN_progress_str = ""
    return None
