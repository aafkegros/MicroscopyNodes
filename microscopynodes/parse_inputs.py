import bpy
import numpy as np
import tempfile
from pathlib import Path

from .handle_blender_structs.dependent_props import ensure_valid_reload_object
from .file_to_array import selected_array_option, channel_data_model
from .ui.preferences import addon_preferences

from typing import List
from .data_model import DatasetModel, ChannelModel

def parse_blender_ui():
    scn = bpy.context.scene
    ensure_valid_reload_object(scn)
    if scn.MiN_reload is None:
        scn.MiN_update_data = True
        scn.MiN_update_settings = True

    channels = parse_channellist()
    relative_loc = parse_relative_loc()
    name = Path(scn.MiN_input_file).name

    # Build DatasetModel
    scene_model = DatasetModel(
        name=name,
        channels=channels,
        relative_loc = relative_loc,
    )
    return scene_model


def ensure_visibility_mask_to_channel_data(dataset, dataset_model):
    dataset.ensure_visibility_mask()
    mask_indices = np.asarray(dataset.visibility.read_points(), dtype=float)
    mask_voxel_size = tuple(float(value) for value in dataset.visibility.read_voxel_extents())
    for channel in dataset_model.channels:
        channel.data.mask_indices = mask_indices
        channel.data.mask_voxel_size = mask_voxel_size

# ----------------------------------------------------------------
# --- Channel Model Construction --------------------------------
# ----------------------------------------------------------------

def parse_channellist() -> List[ChannelModel]:
    channel_models = []
    scn = bpy.context.scene
    shared_data = {
        "unit": scn.MiN_unit,
        "affine": parse_pixel_size(),
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


def parse_pixel_size():
    pixel_size = parse_pixel_size_values()
    return  np.diag([*pixel_size, 1]).tolist()

def parse_pixel_size_values():
    pixel_size = np.array([bpy.context.scene.MiN_xy_size,bpy.context.scene.MiN_xy_size,bpy.context.scene.MiN_z_size])
    if not bpy.context.scene.MiN_pixel_sizes_are_rescaled:
        pixel_size *= selected_array_option().scale()
    return pixel_size


def parse_relative_loc():
    prefloc = addon_preferences(bpy.context).import_loc
    if prefloc == "XY_CENTER":
        return [-0.5,-0.5,0] 
    if prefloc == "XYZ_CENTER":
        return [-0.5,-0.5,-0.5] 
    if prefloc == "ZERO":
        return [0, 0, 0] 
