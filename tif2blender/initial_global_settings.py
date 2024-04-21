import bpy

def preset_environment():
    bpy.context.scene.eevee.volumetric_tile_size = '2'
    bpy.context.scene.cycles.preview_samples = 32
    bpy.context.scene.cycles.samples = 64
    bpy.context.scene.view_settings.view_transform = 'Standard'
    bpy.context.scene.eevee.volumetric_end = 300
    bpy.context.scene.eevee.taa_samples = 64
    return


