import bpy
from pathlib import Path
import numpy as np
import dask.array as da
from copy import deepcopy

class ArrayLoader():
    suffix = None

    def checkPath(self):
        return Path(bpy.context.scene.MiN_input_file).suffix == self.suffix

    def changePath(self, context):
        return

    def load_array(self, input_file):
        return 

    def shape(self):
        return

    def unpack_array(self, input_file, axes_order, ch_dicts):
        # dask array makes sure lazy actions actually get performed lazily
        chunks = ['auto' if dim in 'xyz' else 1 for dim in axes_order] # time and channels are always loadable as separate chunks as they go to separate vdbs
        imgdata = da.from_array(self.load_array(input_file), chunks=chunks)

        if len(axes_order) != len(imgdata.shape):
            raise ValueError("axes_order length does not match data shape: " + str(imgdata.shape))

        size_px = np.array([imgdata.shape[axes_order.find(dim)] if dim in axes_order else 0 for dim in 'xyz'])

        channels = imgdata.shape[axes_order.find('c')] if 'c' in axes_order else 1
        ix = 0
        for ch in ch_dicts:
            if ch['data'] is None:
                ch['data'] = np.take(imgdata, indices=ix, axis=axes_order.find('c')) if 'c' in axes_order else imgdata
                ix += 1
            if ix >= channels:
                break
        return size_px


        


