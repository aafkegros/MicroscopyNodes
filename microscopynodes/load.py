import bpy
from pathlib import Path
import numpy as np

from .handle_blender_structs import *
from .handle_blender_structs import dependent_props
from .load_components import *
from .parse_inputs import *
from .file_to_array import load_array, arr_shape

from mathutils import Matrix


def load_threaded(params):
    try:
        scn = bpy.context.scene
        if not scn.MiN_update_data:
            return params

        ch_dicts, (axes_order, pixel_size, size_px), cache_dir = params

        log('Loading file')
        load_array(ch_dicts) # unpacks into ch_dicts
        axes_order = axes_order.replace('c', "") # channels are separated
        
        for ch in ch_dicts:
            if ch[min_keys.VOLUME] or ch[min_keys.SURFACE]:
                ch["local_files"][min_keys.VOLUME] = VolumeIO().export_ch(ch, cache_dir, scn.MiN_remake,  axes_order)


        progress = 'Loading objects to Blender'
        if any([ch['surface'] for ch in ch_dicts]):
            progress = 'Meshing surfaces, ' + progress.lower()
        if any([ch['labelmask'] for ch in ch_dicts]):
            progress = 'Making labelmasks, ' + progress.lower()
        log(progress)
    except Exception as e: # hacky way to track exceptions across threaded process
        params[0][0]['EXCEPTION'] = e
    return params

def load_blocking(params):
    # loads from the modal/threaded implementation
    ch_dicts, (axes_order, pixel_size, size_px), cache_dir = params
    prev_active_obj = bpy.context.active_object
    scn = bpy.context.scene

    # reads env variables
    base_coll, cache_coll = min_base_colls(Path(scn.MiN_input_file).stem[:50], scn.MiN_reload)    

    if scn.MiN_overwrite_background_color:
        set_background_color()
    if scn.MiN_overwrite_render_settings:
        set_render_settings()

    # --- Prepare  container ---
    container = scn.MiN_reload
    objs = parse_reload(container)

    # read preference variables - or in certain cases read from prev
    scale = parse_scale(size_px, pixel_size, objs) # reads from previous if only update data
    loc = parse_loc(scale, size_px, container)
    
    if container is None:
        bpy.ops.object.empty_add(type="PLAIN_AXES")
        container = bpy.context.view_layer.objects.active
        container.name = Path(scn.MiN_input_file).stem[:50]

    # -- export labelmask --
    # label mask exporting is hard to move outside of blocking functions, as it uses the Blender abc export
    for ch in ch_dicts:
        if ch[min_keys.LABELMASK] and scn.MiN_update_data:
            ch["local_files"][min_keys.LABELMASK] = LabelmaskIO().export_ch(ch, cache_dir,  scn.MiN_remake,  axes_order)
    
    # -- load components --
    axes_obj = load_axes(size_px, pixel_size, scale, axes_obj=objs[min_keys.AXES], container=container)
    slice_cube = load_slice_cube(size_px, scale, container, slicecube=objs[min_keys.SLICECUBE])
    
    for min_type in [min_keys.VOLUME, min_keys.SURFACE, min_keys.LABELMASK]:
        if not any([ch[min_type] for ch in ch_dicts]) and objs[min_type] is None:
            # don't create object if none exists or is required
            continue
        data_io = DataIOFactory(min_type)
        ch_obj = ChannelObjectFactory(min_type, objs[min_type])

        for ch in ch_dicts:
            if ch[min_type] and scn.MiN_update_data:
                collection_activate(*cache_coll)
                ch['collections'][min_type], ch['metadata'][min_type] = data_io.import_data(ch, scale)
                collection_activate(*base_coll)
                ch_obj.update_ch_data(ch)
            if scn.MiN_update_settings:
                ch_obj.update_ch_settings(ch)
            ch_obj.set_parent_and_slicer(container, slice_cube, ch)

    if scn.MiN_update_data:
        container.location = loc
    
    # -- wrap up --
    collection_deactivate_by_name('cache')

    if scn.frame_current < scn.MiN_load_start_frame or scn.frame_current > scn.MiN_load_end_frame:
        scn.frame_set(scn.MiN_load_start_frame)

    try:
        if prev_active_obj is not None:
            prev_active_obj.select_set(True)
            bpy.context.view_layer.objects.active = prev_active_obj
    except:
        pass
    # after first load this should not be used again, to prevent overwriting user values
    scn.MiN_reload = container
    scn.MiN_overwrite_render_settings = False
    scn.MiN_enable_ui = True
    log('')
    return



def set_background_color():
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
    return


def set_render_settings():
    bpy.context.scene.eevee.volumetric_tile_size = '1'
    bpy.context.scene.cycles.preview_samples = 8
    bpy.context.scene.cycles.samples = 64
    bpy.context.scene.view_settings.view_transform = 'Standard'
    bpy.context.scene.eevee.volumetric_end = 300
    bpy.context.scene.eevee.taa_samples = 64

    bpy.context.scene.render.engine = 'CYCLES'
    bpy.context.scene.cycles.transparent_max_bounces = 40 # less slicing artefacts
    bpy.context.scene.cycles.volume_bounces = 32
    bpy.context.scene.cycles.volume_max_steps = 16 # less time to render
    bpy.context.scene.cycles.use_denoising = False # this will introduce noise, but at least also not remove data-noise=
    return
