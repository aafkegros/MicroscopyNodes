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
    # Handle all globals to be scoped after this file and array loading - axes order, cache_dir get internally changed in this function.
    axes_order = bpy.context.scene.MiN_axes_order
    remake = bpy.context.scene.MiN_remake
    xy_size = bpy.context.scene.MiN_xy_size
    z_size = bpy.context.scene.MiN_z_size
    input_file = bpy.context.scene.MiN_input_file
    
    # using context.scene, parse and set env variable
    check_input()
    cache_dir = get_cache_subdir()
    preset_env() 
    
    holders = parse_reload(bpy.context.scene.MiN_reload)
    
    # make and get collections
    base_coll = collection_by_name('Microscopy Nodes', supercollections=[])
    collection_activate(*base_coll)
    collection_by_name('cache',supercollections=[])
    cache_coll = collection_by_name(Path(input_file).stem, supercollections=['cache'], duplicate=(bpy.context.scene.MiN_reload is None))

    # loading array uses some global bpy.context.scene params, notably channelList
    ch_dicts, size_px = load_array(input_file, axes_order) 
    axes_order = axes_order.replace('c', "") # channels are separated

    to_be_parented = []

    # if holders['container'] is not None:
    #     loc = holders['container'].location
    #     loc, scale = update_axes()
    # else:
    #     loc, scale = 
    center_loc = np.array([0.5,0.5,0]) # offset of center (center in x, y, z of obj)
    init_scale = 0.02
    scale =  np.array([1,1,z_size/xy_size])*init_scale
    loc =  tuple(center_loc * size_px*scale)

    ch_dicts, bbox_px = arrays_to_vdb_files(ch_dicts, axes_order, remake, cache_dir)
    vol_obj = load_volume(ch_dicts, bbox_px, scale, cache_coll, base_coll, vol_obj=holders['volume'])
    to_be_parented = update_parent(to_be_parented, vol_obj, ch_dicts)

    # surfaces load volume collections
    surf_obj = load_surfaces(ch_dicts, scale, cache_coll, base_coll, surf_obj=holders['surface'])
    to_be_parented.append(surf_obj)
    
    mask_obj = load_labelmask(ch_dicts, scale, cache_coll, base_coll, cache_dir, remake, axes_order, mask_obj=holders['masks'])
    to_be_parented = update_parent(to_be_parented, mask_obj, ch_dicts)
 
    slicecube = load_slice_cube(to_be_parented, size_px, scale, slicecube=holders['slicecube'])
    axes_obj = load_axes(size_px, init_scale, loc, xy_size, z_size, input_file, axes_obj=holders['axes'])
    to_be_parented.extend([slicecube, axes_obj])

    container_obj = init_container(to_be_parented , name=Path(input_file).stem, container_obj=holders['container'])
    collection_deactivate_by_name('cache')
    axes_obj.select_set(True)

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