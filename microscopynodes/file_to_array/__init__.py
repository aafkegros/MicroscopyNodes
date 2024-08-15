from .tif import TifLoader
from . import zarr
from .zarr import ZarrLoader, ZarrLevelsGroup, change_zarr_level

CLASSES = zarr.CLASSES

def change_path(self, context):
    for Loader in [TifLoader, ZarrLoader]:
        loader = Loader()
        if loader.checkPath():
            loader.changePath(context)

def load_array(input_file, axes_order, mask_channels_str):
    for Loader in [TifLoader, ZarrLoader]:
        loader = Loader()
        if loader.checkPath():
            return loader.unpack_array(input_file, axes_order, mask_channels_str)