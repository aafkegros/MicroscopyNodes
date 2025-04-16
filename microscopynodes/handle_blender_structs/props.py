import bpy
from bpy.props import (StringProperty, FloatProperty,
                        PointerProperty, IntProperty,
                        BoolProperty, EnumProperty
                        )

import platform
from enum import Enum
import tempfile

class min_keys(Enum): 
    NONE = 0
    AXES = 1
    VOLUME = 2
    SURFACE = 3
    LABELMASK = 4
    SLICECUBE = 5


# # -- props --
## Names start with MiN for Microscopy Nodes (MN = Molecular Nodes)

bpy.types.Scene.MiN_remake = bpy.props.BoolProperty(
    name = "MiN_remake", 
    description = "Force remaking vdb files",
    default = False
    )

bpy.types.Scene.MiN_load_start_frame = bpy.props.IntProperty(
    name = "", 
    description = "First timeframe to be loaded",
    default = 0,
    min=0,
    soft_max=10000,
    )

bpy.types.Scene.MiN_load_end_frame = bpy.props.IntProperty(
    name = "", 
    description = "Last timeframe to be loaded.",
    default = 100,
    soft_max= 10000,
    min=0,
    )

bpy.types.Scene.MiN_preset_environment = bpy.props.BoolProperty(
    name = "Set environment variables", 
    description = "Set environment variables for easy initial rendering, useful for first load.\nWill overwrite previous settings",
    default = True
    )

bpy.types.Scene.MiN_xy_size = FloatProperty(
        name="",
        description="xy physical pixel size in micrometer (only 2 digits may show up, but it is accurate to 6 digits)",
        default=1.0)
    
bpy.types.Scene.MiN_z_size = FloatProperty(
        name="",
        description="z physical pixel size in micrometer (only 2 digits may show up, but it is accurate to 6 digits)",
        default=1.0)

bpy.types.Scene.MiN_unit = EnumProperty(
        name = '',
        items=[
            ("ANGSTROM", "Å","Ångström, 0.1 nanometer" ,"", 0),
            ("NANOMETER", "nm","Nanometer" ,"", 1),
            ("MICROMETER", "µm","Micrometer" ,"", 2),
            ("MILLIMETER", "mm","Millimeter" ,"", 3),
            ("METER", "m","Meter" ,"", 4),
            ("AU", "a.u.","Arbitrary units, used to calculate an isotropic pixel size in Z." ,"", 5),
        ], 
        description= "Unit of pixel sizes",
        default="AU",
    )

bpy.types.Scene.MiN_ch_names = StringProperty( # | separated list of channel names from file
    name = "", 
    )

# necessary to make uilist work
bpy.types.Scene.MiN_ch_index = IntProperty(
        name = "", 
        )

bpy.types.Scene.MiN_enable_ui = BoolProperty(
        name = "", 
        default = False,
    )

bpy.types.Scene.MiN_load_finished = BoolProperty(
        name = "", 
        default = False,
    )

bpy.types.Scene.MiN_update_data = BoolProperty(
        name = "",
        description = "Reload the data from local files if they exist, or make new local files",
        default = True,
    )

bpy.types.Scene.MiN_update_settings = BoolProperty(
        name = "",
        description = "Update microscopy nodes channel settings, reapplies import transforms, so will move your data.",
        default = True,
    )

bpy.types.Scene.MiN_chunk = BoolProperty(
        name = "Chunking",
        description = 'Loads volumes in chunks of axis < 2048 px if checked.\nUnchunked large volumes WILL crash MacOS-ARM Blender outside of Cycles.\nChunked volumes can cause Cycles rendering artefacts.\nChunking may be slightly more RAM/network-efficient.',
        default = False,
        ) 


bpy.types.Scene.MiN_progress_str = bpy.props.StringProperty(
    name = "",
    description = "current process in load",
    default="",
)

bpy.types.Scene.MiN_yaml_preferences = StringProperty(
    description = 'File path to a .yaml file that overrides the Microscopy Nodes preferences - use for bpy usage',
    default = "",
    subtype = 'FILE_PATH',
)



