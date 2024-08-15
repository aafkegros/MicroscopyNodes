import bpy
from bpy.props import (StringProperty, FloatProperty,
                        PointerProperty, IntProperty
                        )

from .file_to_array import change_path, change_zarr_level
from pathlib import Path

bpy.types.Scene.MiN_remake = bpy.props.BoolProperty(
    name = "MiN_remake", 
    description = "Force remaking vdb files",
    default = False
    )

bpy.types.Scene.MiN_preset_environment = bpy.props.BoolProperty(
    name = "MiN_preset_environment", 
    description = "Set environment variables",
    default = True
    )

bpy.types.Scene.MiN_Emission = bpy.props.BoolProperty(
    name = "MiN_Emission", 
    description = "Volumes emit light, instead of absorbing light",
    default = True
    )

bpy.types.Scene.MiN_Surface = bpy.props.BoolProperty(
    name = "MiN_surface", 
    description = "Load isosurface object",
    default = True
    )

bpy.types.Scene.MiN_input_file = StringProperty(
        name="",
        description="tif file",
        update= change_path,
        options = {'TEXTEDIT_UPDATE'},
        default="",
        maxlen=1024,
        subtype='DIR_PATH')

bpy.types.Scene.MiN_cache_dir = StringProperty(
        description = 'Location to store VDB and ABC files, any image data will get RESAVED into blender formats here',
    options = {'TEXTEDIT_UPDATE'},
    default = str(Path('~', '.microscopynodes').expanduser()),
    subtype = 'FILE_PATH'
    )

bpy.types.Scene.MiN_axes_order = StringProperty(
        name="",
        description="axes order (only z is used currently)",
        default="zyx",
        maxlen=6)
    
bpy.types.Scene.MiN_xy_size = FloatProperty(
        name="",
        description="xy physical pixel size in micrometer",
        default=1.0)
    
bpy.types.Scene.MiN_z_size = FloatProperty(
        name="",
        description="z physical pixel size in micrometer",
        default=1.0)

bpy.types.Scene.MiN_mask_channels = StringProperty(
        name="",
        description="channels with an integer label mask",
        )

bpy.types.Scene.MiN_selected_zarr_level = StringProperty(
        name="",
        description="Selected zarr level/dataset",
        update= change_zarr_level,
        default= "Zarr Level"
        )

