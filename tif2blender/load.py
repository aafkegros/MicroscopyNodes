import bpy
from bpy.props import (StringProperty, FloatProperty,
                        PointerProperty, IntProperty
                        )
from pathlib import Path
import numpy as np

from .initial_global_settings import preset_environment, preset_em_environment
from .handle_blender_structs import *
from .load_components import *
from .unpack_tif import unpack_tif, changePathTif

from mathutils import Matrix

bpy.types.Scene.T2B_remake = bpy.props.BoolProperty(
    name = "TL_remake", 
    description = "Force remaking vdb files",
    default = False
    )

bpy.types.Scene.T2B_preset_environment = bpy.props.BoolProperty(
    name = "TL_preset_environment", 
    description = "Set environment variables",
    default = True
    )

bpy.types.Scene.T2B_Emission = bpy.props.BoolProperty(
    name = "TL_EM", 
    description = "Volumes emit light, instead of absorbing light",
    default = True
    )

bpy.types.Scene.T2B_Surface = bpy.props.BoolProperty(
    name = "TL_EM", 
    description = "Load isosurface object",
    default = True
    )

bpy.types.Scene.T2B_input_file = StringProperty(
        name="",
        description="tif file",
        update=changePathTif,
        options = {'TEXTEDIT_UPDATE'},
        default="",
        maxlen=1024,
        subtype='FILE_PATH')

bpy.types.Scene.T2B_cache_dir = StringProperty(
        description = 'Location to cache VDB and ABC files',
    options = {'TEXTEDIT_UPDATE'},
    default = str(Path('~', '.tif2blender').expanduser()),
    subtype = 'FILE_PATH'
    )

bpy.types.Scene.T2B_axes_order = StringProperty(
        name="",
        description="axes order (only z is used currently)",
        default="zyx",
        maxlen=6)
    
bpy.types.Scene.T2B_xy_size = FloatProperty(
        name="",
        description="xy physical pixel size in micrometer",
        default=1.0)
    
bpy.types.Scene.T2B_z_size = FloatProperty(
        name="",
        description="z physical pixel size in micrometer",
        default=1.0)


bpy.types.Scene.T2B_mask_channels = StringProperty(
        name="",
        description="channels with an integer label mask",
        )

def load():
    # Handle all globals to be scoped after this - axes order in particular gets internally changed sometimes 
    input_file = bpy.context.scene.T2B_input_file
    axes_order = bpy.context.scene.T2B_axes_order
    remake = bpy.context.scene.T2B_remake
    xy_size = bpy.context.scene.T2B_xy_size
    z_size = bpy.context.scene.T2B_z_size
    cache_dir = Path(bpy.context.scene.T2B_cache_dir) / Path(input_file).stem
    mask_channels = bpy.context.scene.T2B_mask_channels
    surfaces = bpy.context.scene.T2B_Surface
    emission = bpy.context.scene.T2B_Emission

    if bpy.context.scene.T2B_preset_environment:
        preset_environment()    
        if not emission:
            preset_em_environment()
    
    if xy_size <= 0  or z_size <= 0:
        raise ValueError("cannot do zero-size pixels")

    cache_dir.mkdir(parents=True, exist_ok=True)
    
    base_coll = collection_by_name('Collection')
    collection_activate(*base_coll)
    collection_by_name('cache')
    cache_coll = collection_by_name(Path(input_file).stem, supercollections=['cache'], duplicate=True)
    
    # pads axes order with 1-size elements for missing axes
    volume_arrays, mask_arrays, size_px, axes_order = unpack_tif(input_file, axes_order, mask_channels)

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



