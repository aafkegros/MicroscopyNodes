import bpy

def preset_environment():
    bgcol = (0.2,0.2,0.2, 1)
    emitting = [ch.emission for ch in bpy.context.scene.MiN_channelList if (ch.surface or ch.volume) or ch.labelmask]
    if all(emitting):
        bgcol = (0, 0, 0, 1)
    if all([(not emit) for emit in emitting]):
        bgcol = (1, 1, 1, 1)
    try:
        bpy.context.scene.world.node_tree.nodes["Background"].inputs[0].default_value = bgcol
    except:
        pass
    bpy.context.scene.eevee.volumetric_tile_size = '1'
    bpy.context.scene.cycles.preview_samples = 8
    bpy.context.scene.cycles.samples = 64
    bpy.context.scene.view_settings.view_transform = 'Standard'
    bpy.context.scene.eevee.volumetric_end = 300
    bpy.context.scene.eevee.taa_samples = 64

    bpy.context.scene.render.engine = 'CYCLES'
    bpy.context.scene.cycles.transparent_max_bounces = 40 # less slicing artefacts
    bpy.context.scene.cycles.volume_max_steps = 16 # less time to render
    bpy.context.scene.cycles.use_denoising = False # this will introduce noise, but at least also not remove data-noise=
    return


