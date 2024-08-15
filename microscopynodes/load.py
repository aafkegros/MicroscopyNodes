import bpy
from pathlib import Path
import numpy as np

from .initial_global_settings import preset_environment, preset_em_environment
from .handle_blender_structs import *
from .load_components import *

from mathutils import Matrix


def load():
    # Handle all globals to be scoped after this - axes order in particular gets internally changed sometimes 
    input_file = bpy.context.scene.MiN_input_file
    axes_order = bpy.context.scene.MiN_axes_order
    remake = bpy.context.scene.MiN_remake
    xy_size = bpy.context.scene.MiN_xy_size
    z_size = bpy.context.scene.MiN_z_size
    cache_dir = Path(bpy.context.scene.MiN_cache_dir) / Path(input_file).stem
    mask_channels = bpy.context.scene.MiN_mask_channels
    surfaces = bpy.context.scene.MiN_Surface
    emission = bpy.context.scene.MiN_Emission

    if bpy.context.scene.MiN_preset_environment:
        preset_environment()    
        if not emission:
            preset_em_environment()
    
    if xy_size <= 0  or z_size <= 0:
        raise ValueError("cannot do zero-size pixels")

    cache_dir.mkdir(parents=True, exist_ok=True)
    
    base_coll = collection_by_name('Microscopy Nodes', supercollections=[])
    collection_activate(*base_coll)
    collection_by_name('cache',supercollections=[])
    cache_coll = collection_by_name(Path(input_file).stem, supercollections=['cache'], duplicate=True)
    
    volume_arrays, mask_arrays, size_px, axes_order = load_array(input_file, axes_order, mask_channels)

    to_be_parented = []

    center_loc = np.array([0.5,0.5,0]) # offset of center (center in x, y, z of obj)
    init_scale = 0.02
    scale =  np.array([1,1,z_size/xy_size])*init_scale
    loc =  tuple(center_loc * size_px*scale)

    if len(volume_arrays) > 0:
        #TODO check remake
        volume_inputs, bbox_px = arrays_to_vdb_files(volume_arrays, axes_order, remake, cache_dir)
        vol_obj, volume_inputs = load_volume(volume_inputs, bbox_px, scale, cache_coll, base_coll, emission)
        for volume_input in volume_inputs.values():
            to_be_parented.extend([vol for vol in volume_input['collection'].all_objects])
        to_be_parented.extend([vol_obj])
        if surfaces:
            surf_obj = load_surfaces(volume_inputs, scale, cache_coll, base_coll)
            to_be_parented.extend([surf_obj])
    

    if len(mask_arrays) > 0:
        mask_obj, mask_colls = load_labelmask(mask_arrays, scale, cache_coll, base_coll, cache_dir, remake, axes_order)
        [to_be_parented.extend([mask for mask in mask_coll.all_objects])for mask_coll in mask_colls]
        to_be_parented.extend([mask_obj])

    slicecube = load_slice_cube(to_be_parented, size_px, scale)
    to_be_parented.append(slicecube)

    axes_obj = load_axes(size_px, init_scale, loc, xy_size, z_size, input_file)
    to_be_parented.append(axes_obj)

    container = init_container(to_be_parented ,location=loc, name=Path(input_file).stem)
    collection_deactivate_by_name('cache')
    axes_obj.select_set(True)
    return



