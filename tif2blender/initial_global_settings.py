import bpy

def preset_environment():
    bpy.context.scene.eevee.volumetric_tile_size = '2'
    bpy.context.scene.cycles.preview_samples = 4
    bpy.context.scene.cycles.samples = 64
    bpy.context.scene.view_settings.view_transform = 'Standard'
    bpy.context.scene.eevee.volumetric_end = 300
    bpy.context.scene.eevee.taa_samples = 64

    
    bpy.context.scene.render.engine = 'CYCLES'
    bpy.context.scene.cycles.transparent_max_bounces = 40 # less slicing artefacts
    bpy.context.scene.cycles.volume_max_steps = 16 # less time to render


    return


