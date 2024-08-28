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
    # Handle all globals to be scoped after this - axes order in particular gets internally changed sometimes 
    axes_order = bpy.context.scene.MiN_axes_order
    remake = bpy.context.scene.MiN_remake
    xy_size = bpy.context.scene.MiN_xy_size
    z_size = bpy.context.scene.MiN_z_size

    if bpy.context.scene.MiN_cache_dir == '':
        raise ValueError("Empty data directory - please save the project first before using With Project saving.") 
    
    input_file = bpy.context.scene.MiN_input_file
    update_cache_dir(None, bpy.context.scene) # make sure 'With Project is at current fname'
    
    # create folder for this dataset with filename/(zarr_level/)
    cache_dir = Path(bpy.context.scene.MiN_cache_dir) / Path(input_file).stem 
    if  bpy.context.scene.MiN_selected_zarr_level != "":
        cache_dir = cache_dir / bpy.context.scene.MiN_selected_zarr_level.split(":")[0]
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    if bpy.context.scene.MiN_preset_environment:
        preset_environment()    
        if not any(ch.emission for ch in bpy.context.scene.MiN_channelList):
            preset_em_environment()
    
    if xy_size <= 0  or z_size <= 0:
        raise ValueError("cannot do zero-size pixels")

    # make and get collections
    base_coll = collection_by_name('Microscopy Nodes', supercollections=[])
    collection_activate(*base_coll)
    collection_by_name('cache',supercollections=[])
    cache_coll = collection_by_name(Path(input_file).stem, supercollections=['cache'], duplicate=True)
    
    # TODO change this to a callback function on change channel name instead
    ch_names = [ch["name"] for ch in bpy.context.scene.MiN_channelList]
    if len(set(ch_names)) < len(ch_names):
        raise ValueError("No duplicate channel names allowed")

    # loading array uses some global bpy.context.scene params
    ch_dicts, size_px = load_array(input_file, axes_order) 
    axes_order = axes_order.replace('c', "") # channels are separated

    to_be_parented = []

    center_loc = np.array([0.5,0.5,0]) # offset of center (center in x, y, z of obj)
    init_scale = 0.02
    scale =  np.array([1,1,z_size/xy_size])*init_scale
    loc =  tuple(center_loc * size_px*scale)

    ch_dicts, bbox_px = arrays_to_vdb_files(ch_dicts, axes_order, remake, cache_dir)
    vol_obj, ch_dicts = load_volume(ch_dicts, bbox_px, scale, cache_coll, base_coll)
    for ch in ch_dicts:
        if 'collection' in ch:
            to_be_parented.extend([vol for vol in ch['collection'].all_objects])
    to_be_parented.extend([vol_obj])

    surf_obj = load_surfaces(ch_dicts, scale, cache_coll, base_coll)
    to_be_parented.extend([surf_obj])
    
    # mask_obj, mask_colls = load_labelmask(ch_dicts, scale, cache_coll, base_coll, cache_dir, remake, axes_order)
    # [to_be_parented.extend([mask for mask in mask_coll.all_objects])for mask_coll in mask_colls]
    # to_be_parented.extend([mask_obj])

    slicecube = load_slice_cube(to_be_parented, size_px, scale)
    to_be_parented.append(slicecube)

    axes_obj = load_axes(size_px, init_scale, loc, xy_size, z_size, input_file)
    to_be_parented.append(axes_obj)

    container = init_container(to_be_parented ,location=loc, name=Path(input_file).stem)
    collection_deactivate_by_name('cache')
    axes_obj.select_set(True)

    # after first load this should not be used again, to prevent overwriting user values
    bpy.context.scene.MiN_preset_environment = False
    return



