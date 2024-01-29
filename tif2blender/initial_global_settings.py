import bpy

def preset_environment():
    bpy.context.scene.eevee.volumetric_tile_size = '2'
    bpy.context.scene.cycles.preview_samples = 32
    bpy.context.scene.cycles.samples = 64
    bpy.context.scene.view_settings.view_transform = 'Standard'
    bpy.context.scene.eevee.volumetric_end = 500
    bpy.context.scene.eevee.taa_samples = 64

    # bpy.context.space_data.shading.use_scene_world = True

    try:
        bpy.data.worlds["World"].node_tree.nodes["Background"].inputs[0].default_value = (0, 0, 0, 1)
    except:
        pass
    return


