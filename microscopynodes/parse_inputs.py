import bpy
import numpy as np
import tempfile
from pathlib import Path

from .handle_blender_structs.dependent_props import ensure_valid_reload_object
from .file_to_array import selected_array_option, channel_data_model
from .ui.preferences import addon_preferences

from typing import List
from .data_model import DatasetModel, ChannelModel

IMPORT_SCALE_OUTPUT_UNITS = {
    "NANOMETER_SCALE": 1e-9,
    "NANOMETER_DECIMETER_SCALE": 1e-8,
    "NANOMETER_CENTIMETER_SCALE": 1e-7,
    "MICROMETER_SCALE": 1e-6,
    "MICROMETER_DECIMETER_SCALE": 1e-5,
    "MICROMETER_CENTIMETER_SCALE": 1e-4,
    "MILLIMETER_SCALE": 1e-3,
    "MILLIMETER_DECIMETER_SCALE": 1e-2,
    "MILLIMETER_CENTIMETER_SCALE": 1e-1,
    "METER_SCALE": 1.0,
    "METER_DECIMETER_SCALE": 1e1,
    "METER_CENTIMETER_SCALE": 1e2,
    "MOLECULAR_NODES": 1e-7,
}


def parse_blender_ui():
    scn = bpy.context.scene
    ensure_valid_reload_object(scn)
    if scn.MiN_reload is None:
        scn.MiN_update_data = True
        scn.MiN_update_settings = True

    import_scale = addon_preferences(bpy.context).import_scale
    channels = parse_channellist()
    output_unit = parse_output_unit(import_scale)
    explicit_scale = parse_explicit_scale(import_scale)
    axis_unit_scale = parse_axis_unit_scale(import_scale)
    relative_loc = parse_relative_loc()
    name = Path(scn.MiN_input_file).name

    # Build DatasetModel
    scene_model = DatasetModel(
        name=name,
        channels=channels,
        output_unit = output_unit,
        explicit_scale=explicit_scale,
        axis_unit_scale=axis_unit_scale,
        relative_loc = relative_loc,
    )
    return scene_model

# ----------------------------------------------------------------
# --- Channel Model Construction --------------------------------
# ----------------------------------------------------------------

def parse_channellist() -> List[ChannelModel]:
    channel_models = []
    scn = bpy.context.scene
    import_scale = addon_preferences(bpy.context).import_scale
    shared_data = {
        "unit": parse_unit(bpy.context.scene.MiN_unit),
        "affine": parse_pixel_size(import_scale),
        "frame_start": scn.MiN_load_start_frame,
        "frame_end": scn.MiN_load_end_frame,
    }
    for ch_desc in bpy.context.scene.MiN_channelList:
        viz = ch_desc.to_channelviz()
        channel_models.append(ChannelModel(
            cache_path=get_cache_dir(),
            data=channel_data_model(viz.ix, bpy.context.scene.MiN_axes_order, **shared_data),
            viz=viz,
        ))
    return channel_models



def get_cache_dir():
    if addon_preferences().cache_option == 'TEMPORARY':
        path = tempfile.gettempdir()
    if addon_preferences().cache_option == 'PATH':
        path = addon_preferences().cache_path
    if addon_preferences().cache_option == 'WITH_PROJECT':
        path = bpy.path.abspath('//')
    return str(Path(path) / hash_path(bpy.context.scene.MiN_input_file))

def hash_path(path):
    import hashlib
    h = hashlib.sha1(path.encode()).digest()
    return str(int.from_bytes(h[:4], "big") % 10**8)


# ----------------------------------------------------------------
# --- Parsing helpers --------------------------------------------
# ----------------------------------------------------------------


def parse_pixel_size(world_scale):
    pixel_size = parse_pixel_size_values()
    if world_scale == "DEFAULT": # This  is a bit hacky, may deprecate this later
        xy_size = pixel_size[0] if pixel_size[0] != 0 else 1.0
        anisotropy = np.array([1.0, 1.0, pixel_size[2] / xy_size], dtype=float)
        return np.diag([*anisotropy, 1]).tolist()
    return  np.diag([*pixel_size, 1]).tolist()

def parse_pixel_size_values():
    pixel_size = np.array([bpy.context.scene.MiN_xy_size,bpy.context.scene.MiN_xy_size,bpy.context.scene.MiN_z_size])
    if not bpy.context.scene.MiN_pixel_sizes_are_rescaled:
        pixel_size *= selected_array_option().scale()
    return pixel_size

def parse_axis_unit_scale(world_scale):
    if world_scale == "DEFAULT" and bpy.context.scene.MiN_unit != "AU":
        return float(parse_pixel_size_values()[0])
    return 1.0


def parse_unit(string):
    if string == "ANGSTROM":
        return 1e-10
    if string == "NANOMETER":
        return 1e-9
    if string == "MICROMETER":
        return 1e-6
    if string == "MILLIMETER":
        return 1e-3
    if string == "METER":
        return 1
    if string == "AU":
        return 1

def parse_output_unit(world_scale):
    if world_scale in IMPORT_SCALE_OUTPUT_UNITS:
        return IMPORT_SCALE_OUTPUT_UNITS[world_scale]
    if "_SCALE" not in world_scale:
        return 1e-2 # THIS DOESNT FULLY WORK RN
    return parse_unit(world_scale.removesuffix("_SCALE")) 


def parse_explicit_scale(world_scale):
    if world_scale == "DEFAULT":
        return 1e-2
    return None
    

def parse_relative_loc():
    prefloc = addon_preferences(bpy.context).import_loc
    if prefloc == "XY_CENTER":
        # return [-0.5,-0.5,0] * np.array(size_px) * scale 
        return [-0.5,-0.5,0] 
    if prefloc == "XYZ_CENTER":
        return [-0.5,-0.5,-0.5] 
    if prefloc == "ZERO":
        return [0, 0, 0] 
