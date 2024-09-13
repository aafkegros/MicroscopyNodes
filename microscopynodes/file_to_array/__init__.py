from .tif import TifLoader
from . import zarr
from .zarr import ZarrLoader, ZarrLevelsGroup, change_zarr_level
import bpy

CLASSES = zarr.CLASSES

def change_path(self, context):
    for Loader in [TifLoader, ZarrLoader]:
        loader = Loader()
        if loader.checkPath():
            loader.changePath(context)
            bpy.context.scene.MiN_enable_ui = True
            return
    bpy.context.scene.MiN_channel_nr = 0
    bpy.context.scene.MiN_enable_ui = False
    context.scene.property_unset("MiN_xy_size")
    context.scene.property_unset("MiN_z_size")
    context.scene.property_unset("MiN_axes_order")


def load_array(input_file, axes_order, ch_dicts):
    for Loader in [TifLoader, ZarrLoader]:
        loader = Loader()
        if loader.checkPath():
            return loader.unpack_array(input_file, axes_order, ch_dicts)

def change_channel_ax(self, context):
    bpy.context.scene.MiN_channel_nr = arr_shape()[bpy.context.scene.MiN_axes_order.find('c')]


def arr_shape():
    for Loader in [TifLoader, ZarrLoader]:
        loader = Loader()
        if loader.checkPath():
            return loader.shape()