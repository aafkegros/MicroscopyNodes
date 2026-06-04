import bpy
from bpy.props import (StringProperty, FloatProperty,
                        PointerProperty, IntProperty,
                        BoolProperty, EnumProperty
                        )

import platform
import tempfile

from .min_keys import min_keys
from .units import register_import_scale_property


def update_load_with_mask(self, context):
    from ..load import Dataset
    from .dependent_props import valid_reload_object

    reload_object = getattr(self, "MiN_reload", None)
    if not valid_reload_object(reload_object, scene=self):
        return

    dataset = Dataset(holder=reload_object)
    if self.MiN_load_with_mask and dataset.volume is not None:
        dataset.volume.infer_visibility()


def register_scene_props():
    bpy.types.Scene.MiN_remake = bpy.props.BoolProperty(
    name = "MiN_remake", 
    description = "Force remaking vdb files",
    default = False
    )

    register_import_scale_property(bpy.types.Scene)

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
    name = "Overwrite background color", 
    description = "Sets background to white if any non-emissive channels are loaded - sets to black if only emissive channels are loaded",
    default = True
)

    bpy.types.Scene.MiN_overwrite_render_settings = bpy.props.BoolProperty(
    name = "Overwrite render settings", 
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

    bpy.types.Scene.MiN_load_with_mask = BoolProperty(
        name = "",
        description = "Only reload 'visible' data - not masked by slice cube or other masking. Use this to select a region of bigger-than-RAM data.",
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
        "MiN_load_finished",
        "MiN_update_data",
        "MiN_update_settings",
        "MiN_load_with_mask",
        "MiN_progress_str",
    ):
        try:
            delattr(bpy.types.Scene, prop)
        except AttributeError:
            pass
