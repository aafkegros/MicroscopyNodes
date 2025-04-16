from .tif import TifLoader
from .zarr import ZarrLoader
from .arrayoptions import ArrayOption, get_array_options, selected_array_option
from ..handle_blender_structs.progress_handling import log
import bpy
CLASSES = [ArrayOption]
LOADERS = [TifLoader, ZarrLoader]

def get_loader():
    for Loader in LOADERS:
        loader = Loader()
        if loader.check_path():
            return loader
    return None

def change_path(self, context):
    bpy.context.scene.MiN_channel_nr = 0
    bpy.context.scene.MiN_enable_ui = False
    context.scene.property_unset("MiN_xy_size")
    context.scene.property_unset("MiN_z_size")
    context.scene.property_unset("MiN_axes_order")
    context.scene.property_unset("MiN_load_start_frame")
    context.scene.property_unset("MiN_load_end_frame")
    context.scene.property_unset("MiN_selected_array_option")
    context.scene.property_unset("MiN_ch_names")
    context.scene.MiN_array_options.clear()
    log("")
    context.scene.property_unset("MiN_reload")
    if get_loader() is not None:
        get_loader().change_path(context)
        bpy.context.scene.MiN_enable_ui = True
        return
    
    

def change_array_option(self, context):
    if context.scene.MiN_channel_nr != selected_array_option().len_axis('c'):
        context.scene.MiN_channel_nr = selected_array_option().len_axis('c')
    if bpy.context.scene.MiN_load_end_frame > selected_array_option().len_axis('t')-1:
        bpy.context.scene.MiN_load_end_frame = selected_array_option().len_axis('t')-1
    level = selected_array_option()
    
    context.scene.MiN_xy_size = level['xy_size']
    context.scene.MiN_z_size = level['z_size']
    if bpy.context.scene.MiN_pixel_sizes_are_rescaled:
        bpy.context.scene.MiN_xy_size *= level.scale()[0]
        bpy.context.scene.MiN_z_size *= level.scale()[2]

    # if level.ch_names != "":
    #     for ix, ch in enumerate(context.scene.MiN_channelList):
    #         ch['name'] = channels[ix]
    # channels = level.ch_names.split("|")
    # if context.scene.MiN_channel_nr != len(channels) or context.scene.MiN_axes_order != level['axes_order']: # this updates n channels and resets names
    #     context.scene.MiN_axes_order = level['axes_order']
    #     context.scene.MiN_channel_nr = len(channels)
    #     for ix, ch in enumerate(context.scene.MiN_channelList):
    #         if channels[ix] != "":
    #             ch['name'] = channels[ix]
    return
def load_array(ch_dicts):
    get_loader().unpack_array(ch_dicts)

def change_channel_ax(self, context):
    get_loader().reset_options(context.scene.MiN_input_file)

def arr_shape():
    selected_array_option().shape()