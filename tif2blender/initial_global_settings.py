import bpy

def preset_environment():
    bpy.context.scene.eevee.volumetric_tile_size = '2'
    bpy.context.scene.cycles.preview_samples = 8
    bpy.context.scene.cycles.samples = 64
    bpy.context.scene.view_settings.view_transform = 'Standard'
    bpy.context.scene.eevee.volumetric_end = 300
    bpy.context.scene.eevee.taa_samples = 64

    
    bpy.context.scene.render.engine = 'CYCLES'
    bpy.context.scene.cycles.transparent_max_bounces = 40 # less slicing artefacts
    bpy.context.scene.cycles.volume_max_steps = 16 # less time to render
    bpy.context.scene.cycles.use_denoising = False # this will introduce noise, but at least also not remove data-noise

    try:
        bpy.data.worlds["World"].node_tree.nodes["Background"].inputs[0].default_value = (0.5, 0.5, 0.5, 1)
    except:
        pass

    return

def preset_em_environment():
    try:
        bpy.data.worlds["World"].node_tree.nodes["Background"].inputs[0].default_value = (1, 1, 1, 1)
    except:
        pass
    return


