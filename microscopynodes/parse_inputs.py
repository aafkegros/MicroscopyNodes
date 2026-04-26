import bpy
import numpy as np
from pathlib import Path

from .ui import preferences
from .handle_blender_structs import *
from .file_to_array import selected_array_option, channel_data
from .ui.preferences import addon_preferences
from .handle_blender_structs.props import min_keys

from typing import List
from .data_model import DatasetModel, ChannelModel

def parse_blender_ui():
    scn = bpy.context.scene
    if scn.MiN_reload is None:
        scn.MiN_update_data = True
        scn.MiN_update_settings = True

    import_scale = addon_preferences(bpy.context).import_scale
    channels = parse_channellist()
    output_unit = parse_output_unit(import_scale)
    explicit_scale = parse_explicit_scale(import_scale)
    relative_loc = parse_relative_loc()
    name = Path(scn.MiN_input_file).name

    # Build DatasetModel
    scene_model = DatasetModel(
        name=name,
        channels=channels,
        output_unit = output_unit,
        explicit_scale=explicit_scale,
        relative_loc = relative_loc,

        update_settings=scn.MiN_update_settings,
        update_data=scn.MiN_update_data,
        previous_holder_to_update = scn.MiN_reload,
        start_frame = scn.MiN_load_start_frame,
        end_frame = scn.MiN_load_end_frame,
    )
    return scene_model

# ----------------------------------------------------------------
# --- Channel Model Construction --------------------------------
# ----------------------------------------------------------------

def parse_channellist() -> List[ChannelModel]:
    channel_models = []
    scn = bpy.context.scene
    import_scale = addon_preferences(bpy.context).import_scale
    for ch_desc in bpy.context.scene.MiN_channelList:
        channel_settings = {
            "ix":                   ch_desc.ix,
            "name":                 ch_desc.name,
            
            "visible_as": {
                                    min_keys.VOLUME: ch_desc.volume,
                                    min_keys.SURFACE: ch_desc.surface,
                                    min_keys.LABELMASK: ch_desc.labelmask,
            },
            "emission":             ch_desc.emission,

            "surf_resolution":      addon_preferences(bpy.context).surf_resolution,

            "cmap":                 parse_cmap(ch_desc.cmap, ch_desc.single_color)[0],
            "cmap_is_linear":       parse_cmap(ch_desc.cmap, ch_desc.single_color)[1],
        }

        data = channel_data(channel_settings['ix'], bpy.context.scene.MiN_axes_order)

        channel_settings.update(
            {
            "data":                 data,
            # "data_shape":           data.shape, Consider doing this later for data optional
            "source":               scn.MiN_input_file,
            "dataset_resolution":   selected_array_option().identifier,

            "cache_path":           get_cache_dir(),
            "axes_order":           scn.MiN_axes_order.replace("c", ""),
            "unit":                 parse_unit(bpy.context.scene.MiN_unit),
            "affine":               parse_pixel_size(import_scale),
            "frame_start":          scn.MiN_load_start_frame,
            "frame_end":            scn.MiN_load_end_frame,
            }
        )
        channel_models.append(ChannelModel(**channel_settings))
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
    pixel_size = np.array([bpy.context.scene.MiN_xy_size,bpy.context.scene.MiN_xy_size,bpy.context.scene.MiN_z_size])
    if not bpy.context.scene.MiN_pixel_sizes_are_rescaled: 
        pixel_size *= selected_array_option().scale() 
    if world_scale == "DEFAULT": # This  is a bit hacky, may deprecate this later
        xy_size = pixel_size[0] if pixel_size[0] != 0 else 1.0
        anisotropy = np.array([1.0, 1.0, pixel_size[2] / xy_size], dtype=float)
        return np.diag([*anisotropy, 1]).tolist()
    return  np.diag([*pixel_size, 1]).tolist()


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

def parse_output_unit(world_scale):
    if world_scale == "MOLECULAR_NODES":
        return 1e-7
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


def parse_cmap(name, single_color):
    from .min_nodes.shader_nodes import get_lut
    return get_lut(name, single_color)
