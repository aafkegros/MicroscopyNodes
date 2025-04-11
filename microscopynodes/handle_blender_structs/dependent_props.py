print('importing for dependent props')
import bpy
from bpy.props import (StringProperty, FloatProperty,
                        PointerProperty, IntProperty,
                        BoolProperty, EnumProperty
                        )

# update functions are defined locally
from ..file_to_array import change_path, change_channel_ax, change_array_option, get_array_options
from ..ui.channel_list import set_channels

import functools
from operator import attrgetter
import tempfile
from pathlib import Path

print('registering dependent props')



bpy.types.Scene.MiN_input_file = StringProperty(
        name="",
        description="image path, either to tif file, zarr root folder or zarr URL",
        update= change_path,
        options = {'TEXTEDIT_UPDATE'},
        default="",
        maxlen=1024,
        )

bpy.types.Scene.MiN_axes_order = StringProperty(
        name="",
        description="axes order (out of tzcyx)",
        default="",
        update=change_channel_ax,
        maxlen=6)

bpy.types.Scene.MiN_selected_array_option = EnumProperty(
        name="",
        description="Select the imported array or transform",
        items= get_array_options,
        update= change_array_option
        )

bpy.types.Scene.MiN_channel_nr = IntProperty(
        name = "", 
        default = 0,
        update = set_channels,
        )

def poll_empty(self, object):
    from ..load_components.load_generic import get_min_gn
    if object.type != 'EMPTY':
        return False
    if any([get_min_gn(child) != None for child in object.children]):
        return True
    return False

bpy.types.Scene.MiN_reload = PointerProperty(
        name = "", 
        description = "Reload data of Microscopy Nodes object.\nCan be used to replace deleted (temp) files, change resolution, or channel settings.\nUsage: Point to previously loaded microscopy data.",
        type=bpy.types.Object,
        poll=poll_empty,
        )
        