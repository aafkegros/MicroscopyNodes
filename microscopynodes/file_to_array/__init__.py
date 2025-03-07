from .tif import TifLoader
from . import zarr
from .zarr import ZarrLoader, ZarrLevelsGroup, change_zarr_level
from ..handle_blender_structs.progress_handling import log
import bpy

CLASSES = zarr.CLASSES

def change_path(self, context):
    log("")
    context.scene.property_unset("MiN_reload")
    for Loader in [TifLoader, ZarrLoader]:
        
        loader = Loader()
        if loader.checkPath():
            loader.changePath(context)
            bpy.context.scene.MiN_enable_ui = True
            if 't' in bpy.context.scene.MiN_axes_order:
                bpy.context.scene.MiN_load_end_frame = arr_shape()[bpy.context.scene.MiN_axes_order.find('t')]-1
            return
    bpy.context.scene.MiN_channel_nr = 0
    bpy.context.scene.MiN_enable_ui = False
    context.scene.property_unset("MiN_xy_size")
    context.scene.property_unset("MiN_z_size")
    context.scene.property_unset("MiN_axes_order")
    context.scene.property_unset("MiN_load_start_frame")
    context.scene.property_unset("MiN_load_end_frame")


def load_array(input_file, axes_order, ch_dicts):
    for Loader in [TifLoader, ZarrLoader]:
        loader = Loader()
        if loader.checkPath():
            return loader.unpack_array(input_file, axes_order, ch_dicts)

def change_channel_ax(self, context):
    if 'c' in bpy.context.scene.MiN_axes_order:
        bpy.context.scene.MiN_channel_nr = arr_shape()[bpy.context.scene.MiN_axes_order.find('c')]
    else:
        bpy.context.scene.MiN_channel_nr = 1

def arr_shape():
    for Loader in [TifLoader, ZarrLoader]:
        loader = Loader()
        if loader.checkPath():
            return loader.shape()