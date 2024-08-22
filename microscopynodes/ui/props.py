import bpy
from bpy.props import (StringProperty, FloatProperty,
                        PointerProperty, IntProperty,
                        BoolProperty
                        )

from ..file_to_array import change_path, change_zarr_level
from .channel_list import set_channels
from pathlib import Path
import tempfile
import functools
from operator import attrgetter

# --- cache dir helpers

CACHE_LOCATIONS = {
    'Temporary' : {
        'icon' : 'FILE_HIDDEN',
        'cache_dir' : functools.partial(tempfile.gettempdir),
        'ui_element': functools.partial(lambda ui_layout : ui_layout.label(text ='Deleted files may need to be reloaded', icon="ERROR"))
    },
    'Path' : {
        'icon' : 'FILE_CACHE',
        'cache_dir' : functools.partial(attrgetter('context.scene.MiN_explicit_cache_dir'), bpy),
        'ui_element': functools.partial(lambda ui_layout : ui_layout.prop(bpy.context.scene, "MiN_explicit_cache_dir", text= 'Asset dir'))
    },
    'With Project' : {
        'icon' : 'FILE_BLEND',
        'cache_dir' : functools.partial(bpy.path.abspath, '//'),
        'ui_element' : functools.partial(lambda ui_layout: ui_layout.label(text ='Make sure the project is saved'))
    },
}
def update_cache_dir(self, context):
    bpy.context.scene.MiN_cache_dir = CACHE_LOCATIONS[bpy.context.scene.MiN_selected_cache_option]['cache_dir']()
    
# -- props --

bpy.types.Scene.MiN_remake = bpy.props.BoolProperty(
    name = "MiN_remake", 
    description = "Force remaking vdb files",
    default = False
    )

bpy.types.Scene.MiN_preset_environment = bpy.props.BoolProperty(
    name = "MiN_preset_environment", 
    description = "Set environment variables for easy initial rendering, useful for first load.\nWill overwrite previous settings",
    default = True
    )

bpy.types.Scene.MiN_input_file = StringProperty(
        name="",
        description="image path, either to tif file, zarr root folder or zarr URL",
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
        description="axes order (out of tzcyx)",
        default="",
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

bpy.types.Scene.MiN_reload_data_of = PointerProperty(
        name = "", 
        description = "Reload data of Microscopy Nodes object.\nCan be used to replace deleted (temp) files, change resolution, or channel settings.\nUsage: Point to previously loaded microscopy data.\nWarning: Will replace Geometry Nodes settings",
        type=bpy.types.Object
        )

bpy.types.Scene.MiN_ch_index = IntProperty(
        name = "", 
        )

bpy.types.Scene.MiN_channel_nr = IntProperty(
        name = "", 
        default = 0,
        update = set_channels,
        )

bpy.types.Scene.MiN_enable_ui = BoolProperty(
        name = "", 
        default = False,
    )