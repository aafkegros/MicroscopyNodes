import bpy
from pathlib import Path
import numpy as np

from .initial_global_settings import preset_environment, preset_em_environment
from .handle_blender_structs import *
from .load_components import *
from .file_to_array import load_array
from .ui.props import update_cache_dir

from mathutils import Matrix

def load():
    """
    Main loading function of Microscopy Nodes, handles all input parameters, 
    then loads or updates all objects. 
    """
    # --- Handle input ---
    prev_active_obj = bpy.context.active_object
    check_input()
    
    axes_order = bpy.context.scene.MiN_axes_order
    remake = bpy.context.scene.MiN_remake
    pixel_size = np.array([bpy.context.scene.MiN_xy_size,bpy.context.scene.MiN_xy_size,bpy.context.scene.MiN_z_size])
    input_file = bpy.context.scene.MiN_input_file
    fname = Path(input_file).stem
    
    cache_dir = get_cache_subdir()
    preset_env() 
    base_coll, cache_coll = min_base_colls(fname, bpy.context.scene.MiN_reload)    
    
    holders = parse_reload(bpy.context.scene.MiN_reload)
    ch_dicts = parse_channellist(bpy.context.scene.MiN_channelList)

    size_px = load_array(input_file, axes_order, ch_dicts) # unpacks into ch_dicts
    axes_order = axes_order.replace('c', "") # channels are separated

    # --- Load components ---

    to_be_parented = []
    
    axes_obj, scale = load_axes(size_px, pixel_size, axes_obj=holders['axes'])
    to_be_parented.append(axes_obj)
    
    ch_dicts, bbox_px = arrays_to_vdb_files(ch_dicts, axes_order, remake, cache_dir)
    vol_obj = load_volume(ch_dicts, bbox_px, scale, cache_coll, base_coll, vol_obj=holders['volume'])
    to_be_parented = update_parent(to_be_parented, vol_obj, ch_dicts)

    # surfaces load volume collections
    surf_obj = load_surfaces(ch_dicts, scale, cache_coll, base_coll, surf_obj=holders['surface'])
    to_be_parented.append(surf_obj)
    
    mask_obj = load_labelmask(ch_dicts, scale, cache_coll, base_coll, cache_dir, remake, axes_order, mask_obj=holders['masks'])
    to_be_parented = update_parent(to_be_parented, mask_obj, ch_dicts)

    # slices all objects in to_be_parented but axes
    slicecube = load_slice_cube(to_be_parented, size_px, scale, slicecube=holders['slicecube'])
    to_be_parented.append(slicecube)

    loc = np.array(size_px) * np.array([0.5,0.5,0]) * scale * -1
    container_obj = init_container(to_be_parented ,loc=loc, name=fname, container_obj=holders['container'])
    collection_deactivate_by_name('cache')

    if prev_active_obj is not None:
        prev_active_obj.select_set(True)
        bpy.context.view_layer.objects.active = prev_active_obj
    # after first load this should not be used again, to prevent overwriting user values
    bpy.context.scene.MiN_preset_environment = False
    return

def update_parent(to_be_parented, obj, ch_dicts):
    for ch in ch_dicts:
        if ch['collection'] is not None:
            to_be_parented.extend([coll_obj for coll_obj in ch['collection'].all_objects])
    to_be_parented.extend([obj])
    return to_be_parented

def get_cache_subdir():
    update_cache_dir(None, bpy.context.scene) # make sure 'With Project is at current fname'
    if bpy.context.scene.MiN_cache_dir == '':
        raise ValueError("Empty data directory - please save the project first before using With Project saving.") 
    # create folder for this dataset with filename/(zarr_level/)
    cache_dir = Path(bpy.context.scene.MiN_cache_dir) / Path(bpy.context.scene.MiN_input_file).stem 
    if  bpy.context.scene.MiN_selected_zarr_level != "":
        cache_dir = cache_dir / bpy.context.scene.MiN_selected_zarr_level.split(":")[0]
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir

def preset_env():
    if bpy.context.scene.MiN_preset_environment:
        preset_environment()    
        if not any((ch.emission and ch.volume) for ch in bpy.context.scene.MiN_channelList):
            preset_em_environment()
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
    holders = {'axes':None,'volume':None,'surface':None,'masks':None, 'slicecube':None, 'container':container_obj}
    if container_obj is None:
        return holders
    for child in container_obj.children:
        mod = get_min_gn(child)
        if mod is not None:
            for holdername in holders:
                if holdername in mod.name:
                    holders[holdername] = child
    return holders

def parse_channellist(channellist):
    ch_dicts = []
    for channel in bpy.context.scene.MiN_channelList:
        ch_dicts.append({k:v for k,v in channel.items()}) # take over settings from UI
        ch_dicts[-1]['identifier'] = f"ch_id{channel['ix']}" # reload-identity
        ch_dicts[-1]['data'] = None
        ch_dicts[-1]['collection'] = None
        ch_dicts[-1]['material'] = None
    return ch_dicts

def min_base_colls(fname, min_reload):
    # make or get collections
    base_coll = collection_by_name('Microscopy Nodes', supercollections=[])
    collection_activate(*base_coll)
    collection_by_name('cache',supercollections=[])
    cache_coll = collection_by_name(fname, supercollections=['cache'], duplicate=(min_reload is None))
    collection_activate(*base_coll)
    return base_coll, cache_coll