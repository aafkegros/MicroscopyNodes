import bpy
from bpy.props import (StringProperty, FloatProperty,
                        PointerProperty, IntProperty,
                        BoolProperty, EnumProperty
                        )

import platform
import tempfile

from .min_keys import min_keys
from .units import register_import_scale_property, update_import_scale


def update_load_with_mask(scene, context):
    if scene.MiN_load_with_mask:
        scene.MiN_update_settings = False


def register_scene_props():
    bpy.types.Scene.MiN_remake = bpy.props.BoolProperty(
    name = "MiN_remake", 
    description = "Force remaking vdb files",
    default = False
    )

    register_import_scale_property(bpy.types.Scene)
    bpy.types.Scene.MiN_import_loc = EnumProperty(
        name="Import location",
        items=[
            ("XY_CENTER", "XY Center", "Center volume in XY", "", 0),
            ("XYZ_CENTER", "XYZ Center", "Center volume in XYZ", "", 1),
            ("ZERO", "Origin", "Volume origin at world origin", "", 2),
        ],
        description="Defines the coordinate translation after import",
        default="XY_CENTER",
        update=update_import_scale,
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

    bpy.types.Scene.MiN_overwrite_background_color = bpy.props.BoolProperty(
    name = "On load: overwrite background color",
    description = "Sets background to white if any non-emissive channels are loaded - sets to black if only emissive channels are loaded",
    default = True
)

    bpy.types.Scene.MiN_overwrite_render_settings = bpy.props.BoolProperty(
    name = "On load: overwrite render settings",
    description = "Sets render settings to Microscopy Nodes defaults, to ensure relatively responsive large volume rendering.",
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
        ], 
        description= "Unit of pixel sizes",
        default="MICROMETER",
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

    bpy.types.WindowManager.MiN_load_running = BoolProperty(
        name="",
        default=False,
        options={'HIDDEN', 'SKIP_SAVE'},
    )

    bpy.types.WindowManager.MiN_cancel_load_requested = BoolProperty(
        name="",
        default=False,
        options={'HIDDEN', 'SKIP_SAVE'},
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

    bpy.types.Scene.MiN_load_with_mask = BoolProperty(
        name = "",
        description = "Reload only volume voxels remaining after spatial masking, such as the slice cube. Useful for loading a selected region of datasets larger than RAM. Shader visibility is ignored; label masks and surfaces are not yet supported",
        default = False,
        update = update_load_with_mask,
    )

    bpy.types.Scene.MiN_progress_str = bpy.props.StringProperty(
    name = "",
    description = "current process in load",
    default="",
)


def unregister_scene_props():
    for prop in (
        "MiN_remake",
        "MiN_import_scale",
        "MiN_import_loc",
        "MiN_load_start_frame",
        "MiN_load_end_frame",
        "MiN_overwrite_background_color",
        "MiN_overwrite_render_settings",
        "MiN_xy_size",
        "MiN_z_size",
        "MiN_unit",
        "MiN_ch_names",
        "MiN_ch_index",
        "MiN_enable_ui",
        "MiN_update_data",
        "MiN_update_settings",
        "MiN_load_with_mask",
        "MiN_progress_str",
    ):
        try:
            delattr(bpy.types.Scene, prop)
        except AttributeError:
            pass
    for prop in ("MiN_load_running", "MiN_cancel_load_requested"):
        try:
            delattr(bpy.types.WindowManager, prop)
        except AttributeError:
            pass
