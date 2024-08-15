import bpy
from bpy.props import (StringProperty, FloatProperty,
                        PointerProperty, IntProperty
                        )

from .file_to_array import change_path, change_zarr_level
from pathlib import Path
import tempfile

# --- cache dir helpers

CACHE_LOCATIONS = {
    'Temporary' : {
        'icon' : 'FILE_HIDDEN',
        'cache_dir' : "tempfile.gettempdir()",
        'ui_element': "grid.label(text ='Deleted files may break your project', icon='SEQUENCE_COLOR_01')"
    },
    'Path' : {
        'icon' : 'FILE_CACHE',
        'cache_dir' : "bpy.context.scene.MiN_explicit_cache_dir",
        'ui_element': "grid.prop(bpy.context.scene, 'MiN_explicit_cache_dir', text= 'Asset dir')"
    },
    'With Project' : {
        'icon' : 'FILE_BLEND',
        'cache_dir' : "bpy.path.abspath('//')",
        'ui_element' : "grid.label(text ='Make sure the project is saved')"
    },
}
def update_cache_dir(self, context):
    bpy.context.scene.MiN_cache_dir = eval(CACHE_LOCATIONS[bpy.context.scene.MiN_selected_cache_option]['cache_dir'])
    

# -- props --

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
        )

bpy.types.Scene.MiN_explicit_cache_dir = StringProperty(
    description = 'Location to store VDB and ABC files, any image data will get RESAVED into blender formats here',
    options = {'TEXTEDIT_UPDATE'},
    default = str(Path('~', '.microscopynodes').expanduser()),
    subtype = 'DIR_PATH',
    update = update_cache_dir
    )

bpy.types.Scene.MiN_selected_cache_option = StringProperty(
        name="",
        description="Where VDB and ABC files are created",
        default= "Temporary",
        update= update_cache_dir
        )

bpy.types.Scene.MiN_cache_dir = StringProperty(
        name="MiN cache dir",
        description="Cache/asset location",
        default= tempfile.gettempdir()
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
        default= ""
        )

