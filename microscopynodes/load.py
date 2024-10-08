import bpy
from pathlib import Path
import numpy as np

from .initial_global_settings import preset_environment
from .handle_blender_structs import *
from .handle_blender_structs import dependent_props
from .load_components import *
from .file_to_array import load_array, arr_shape

from mathutils import Matrix


def load_init():
    # all parameters initialized here are shared between threaded and blocking load functions
    check_input()
    axes_order = bpy.context.scene.MiN_axes_order
    pixel_size = np.array([bpy.context.scene.MiN_xy_size,bpy.context.scene.MiN_xy_size,bpy.context.scene.MiN_z_size])
    cache_dir = get_cache_subdir()

    ch_dicts = parse_channellist(bpy.context.scene.MiN_channelList)
    size_px = np.array([arr_shape()[axes_order.find(dim)] if dim in axes_order else 0 for dim in 'xyz'])
    size_px = tuple([max(ax, 1) for ax in size_px])

    if bpy.context.scene.MiN_reload is None:
        bpy.context.scene.MiN_update_data = True
        bpy.context.scene.MiN_update_settings = True
    return ch_dicts, (axes_order,  pixel_size, size_px), cache_dir

def parse_channellist(channellist):
    # initializes ch_dicts, which holds data and metadata, such as user settings, per channel
    ch_dicts = []
    for channel in bpy.context.scene.MiN_channelList:
        ch_dicts.append({k:v for k,v in channel.items()}) # take over settings from UI
        for key in min_keys: # rename ui-keys to enum for which objects to load
            if key.name.lower() in ch_dicts[-1]:
                ch_dicts[-1][key] = ch_dicts[-1][key.name.lower()]
        ch_dicts[-1]['identifier'] = f"ch_id{channel['ix']}" # reload-identity
        ch_dicts[-1]['data'] = None
        ch_dicts[-1]['collections'] = {}
        ch_dicts[-1]['metadata'] = {}
        ch_dicts[-1]['local_files'] = {}
    return ch_dicts

def load_threaded(params):
    if not bpy.context.scene.MiN_update_data:
        return params

    ch_dicts, (axes_order, pixel_size, size_px), cache_dir = params

    log('Loading file')
    load_array(bpy.context.scene.MiN_input_file, axes_order, ch_dicts) # unpacks into ch_dicts
    axes_order = axes_order.replace('c', "") # channels are separated
    
    for ch in ch_dicts:
        if ch[min_keys.VOLUME] or ch[min_keys.SURFACE]:
            ch["local_files"][min_keys.VOLUME] = VolumeIO().export_ch(ch, cache_dir, bpy.context.scene.MiN_remake,  axes_order)


    progress = 'Loading objects to Blender'
    if any([ch['surface'] for ch in ch_dicts]):
        progress = 'Meshing surfaces, ' + progress.lower()
    if any([ch['labelmask'] for ch in ch_dicts]):
        progress = 'Making labelmasks, ' + progress.lower()
    log(progress)
    return params

def load_blocking(params):
    ch_dicts, (axes_order, pixel_size, size_px), cache_dir = params
    base_coll, cache_coll = min_base_colls(Path(bpy.context.scene.MiN_input_file).stem[:50], bpy.context.scene.MiN_reload)    
    prev_active_obj = bpy.context.active_object
    input_file = bpy.context.scene.MiN_input_file
    update_settings = bpy.context.scene.MiN_update_settings
    update_data = bpy.context.scene.MiN_update_data

     # --- Load components ---
    container = bpy.context.scene.MiN_reload
    objs = parse_reload(container)
    if container is None:
        bpy.ops.object.empty_add(type="PLAIN_AXES")
        container = bpy.context.view_layer.objects.active
        container.name = Path(input_file).stem[:50]

    if bpy.context.scene.MiN_preset_environment:
        preset_env()    
    
    # label mask exporting is hard to move outside of blocking functions, as it uses the Blender abc export
    for ch in ch_dicts:
        if ch[min_keys.LABELMASK] and update_data:
            ch["local_files"][min_keys.LABELMASK] = LabelmaskIO().export_ch(ch, cache_dir,  bpy.context.scene.MiN_remake,  axes_order)
    
    axes_obj, scale = load_axes(size_px, pixel_size, axes_obj=objs[min_keys.AXES])
    axes_obj.parent = container
    slice_cube = load_slice_cube(size_px, scale, slicecube=objs[min_keys.SLICECUBE])
    slice_cube.parent = container
    
    for min_type in [min_keys.VOLUME, min_keys.SURFACE, min_keys.LABELMASK]:
        if not any([ch[min_type] for ch in ch_dicts]) and objs[min_type] is None:
            # don't create object if none exists or is required
            continue
        data_io = DataIOFactory(min_type)
        ch_obj = ChannelObjectFactory(min_type, objs[min_type])

        for ch in ch_dicts:
            if ch[min_type] and update_data:
                collection_activate(*cache_coll)
                ch['collections'][min_type], ch['metadata'][min_type] = data_io.import_data(ch, scale)
                collection_activate(*base_coll)
                ch_obj.update_ch_data(ch)
            if update_settings:
                ch_obj.update_ch_settings(ch)
            ch_obj.set_parent_and_slicer(container, slice_cube, ch)

    if bpy.context.scene.MiN_reload is None:
       container.location = np.array(size_px) * np.array([0.5,0.5,0]) * scale * -1
    
    # set default 
    collection_deactivate_by_name('cache')
    try:
        if prev_active_obj is not None:
            prev_active_obj.select_set(True)
            bpy.context.view_layer.objects.active = prev_active_obj
    except:
        pass
    # after first load this should not be used again, to prevent overwriting user values
    bpy.context.scene.MiN_preset_environment = False
    bpy.context.scene.MiN_enable_ui = True
    log('')
    return


def get_cache_subdir():
     # make sure 'With Project is at current fname'
    if bpy.context.scene.MiN_cache_dir == '':
        # from .handle_blender_structs.dependent_props import update_cache_dir
        # update_cache_dir(None, bpy.context.scene)
        if bpy.context.scene.MiN_cache_dir == '':
            raise ValueError("Empty data directory - please save the project first before using With Project saving.") 
    # create folder for this dataset with filename/(zarr_level/)
    cache_dir = Path(bpy.context.scene.MiN_cache_dir) / Path(bpy.context.scene.MiN_input_file).stem 
    if  bpy.context.scene.MiN_selected_zarr_level != "":
        cache_dir = cache_dir / bpy.context.scene.MiN_selected_zarr_level.split(":")[0]
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir

def preset_env():
    preset_environment()    
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

def check_input():
    if bpy.context.scene.MiN_xy_size <= 0  or bpy.context.scene.MiN_z_size <= 0:
        raise ValueError("cannot do zero-size pixels")
    # TODO change this to a callback function on change channel name instead
    ch_names = [ch["name"] for ch in bpy.context.scene.MiN_channelList]
    if len(set(ch_names)) < len(ch_names):
        raise ValueError("No duplicate channel names allowed")
    return

def parse_reload(container_obj):
    objs = {}
    for key in min_keys:
        objs[key] = None
        if container_obj is not None:
            for child in container_obj.children:
                if get_min_gn(child) is not None and key.name.lower() in get_min_gn(child).name:
                    objs[key] = child
    return objs

def min_base_colls(fname, min_reload):
    # make or get collections
    base_coll = collection_by_name('Microscopy Nodes', supercollections=[])
    collection_activate(*base_coll)
    collection_by_name('cache',supercollections=[])
    cache_coll = collection_by_name(fname, supercollections=['cache'], duplicate=(min_reload is None))
    collection_activate(*base_coll)
    return base_coll, cache_coll

