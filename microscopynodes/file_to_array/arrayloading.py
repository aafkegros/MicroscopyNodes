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

    def unpack_array(self, input_file, axes_order):
        # dask array makes sure lazy actions actually get performed lazily
        chunks = ['auto' if dim in 'xyz' else 1 for dim in axes_order] # time and channels are always loadable as separate chunks as they go to separate vdbs
        imgdata = da.from_array(self.load_array(input_file), chunks=chunks)

        if len(axes_order) != len(imgdata.shape):
            raise ValueError("axes_order length does not match data shape: " + str(imgdata.shape))

        size_px = np.array([imgdata.shape[axes_order.find(dim)] if dim in axes_order else 0 for dim in 'xyz'])

        ch_arrays = []
        for channel in bpy.context.scene.MiN_channelList:
            ch_arrays.append({k:v for k,v in channel.items()}) # take over settings from UI
            ch_arrays[-1]['data'] = np.take(imgdata, indices=channel.ix, axis=axes_order.find('c')) if 'c' in axes_order else imgdata
            ch_arrays[-1]['identifier'] = f"ch_id{channel['ix']}" # right now, reloadable identity is only channel number
        return ch_arrays, size_px



