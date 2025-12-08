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

    channels = parse_channellist()
    output_unit = parse_output_unit(addon_preferences(bpy.context).import_scale)
    relative_loc = parse_relative_loc()
    name = Path(scn.MiN_input_file).name

    # Build DatasetModel
    scene_model = DatasetModel(
        name=name,
        channels=channels,
        output_unit = output_unit,
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
            "affine":               parse_pixel_size(),
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


def parse_pixel_size():
    pixel_size = np.array([bpy.context.scene.MiN_xy_size,bpy.context.scene.MiN_xy_size,bpy.context.scene.MiN_z_size])
    if not bpy.context.scene.MiN_pixel_sizes_are_rescaled: 
        pixel_size *= selected_array_option().scale() 
    return  np.diag([*pixel_size, 1]).tolist()

# def parse_size_px():
#     size_px = np.array([selected_array_option().shape()[axes_order.find(dim)] if dim in axes_order else 0 for dim in 'xyz'])
#     size_px = tuple([max(ax, 1) for ax in size_px])
#     return size_px

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

# def parse_scale(size_px, pixel_size):
#     scale = None
#     world_scale = addon_preferences(bpy.context).import_scale

#     isotropic = np.array([1,1,pixel_size[-1]/pixel_size[0]]) 
#     if world_scale == "DEFAULT" or bpy.context.scene.MiN_unit == 'AU': # cm / px
#         scale = isotropic*0.01
    
#     if world_scale == "MOLECULAR_NODES" and bpy.context.scene.MiN_unit != 'AU': # cm / nm
#         physical_size = parse_unit(bpy.context.scene.MiN_unit) * pixel_size
#         scale = physical_size / 1e-7
#     if "_SCALE" in world_scale and bpy.context.scene.MiN_unit != 'AU': # m / unit
#         physical_size = parse_unit(bpy.context.scene.MiN_unit) * pixel_size
#         scale = physical_size / parse_unit(world_scale.removesuffix("_SCALE")) 

#     # # TODO do this with databpy in the respective objects
#     # if objs[min_keys.AXES] is not None:
#     #     old_size_px, old_scale = get_previous_scale(objs[min_keys.AXES], size_px)
#     #     if bpy.context.scene.MiN_update_data and not bpy.context.scene.MiN_update_settings:
#     #         scale = (np.array(old_size_px) / np.array(size_px)) * old_scale
#     #     scale_factor = (np.array(size_px) / np.array(old_size_px)) * (scale / old_scale)
#     return scale
    

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

    # if name.lower() == "single_color":
    #     lut = [[*single_color,1]]
    #     linear = True
    # else:
    #     lut = cmap.Colormap(name.lower()).lut(min(len(cmap.Colormap(name.lower()).lut()), 32))
    #     linear = (cmap.Colormap(name.lower()).interpolation == 'linear')
    # return lut, linear

# def get_previous_scale(axes_obj, size_px):
#     try:
#         mod = get_min_gn(axes_obj)
#         nodes = mod.node_group.nodes
#         old_size_px = nodes['[Microscopy Nodes size_px]'].vector
#         old_scale = nodes['[Microscopy Nodes scale]'].vector
#         return old_size_px, old_scale
#     except KeyError as e:
#         print(e)
#         pass


# def parse_reload(container_obj):
#     objs = {}
#     for key in min_keys:
#         objs[key] = None
#         if container_obj is not None:
#             for child in container_obj.children:
#                 if get_min_gn(child) is not None and key.name.lower() in get_min_gn(child).name:
#                     objs[key] = child

#     return objs

