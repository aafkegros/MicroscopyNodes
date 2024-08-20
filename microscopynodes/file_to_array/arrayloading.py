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

    def unpack_array(self, input_file, axes_order, mask_channels_str):
        # dask array makes sure lazy actions actually get performed lazily
        chunks = ['auto' if dim in 'xyz' else 1 for dim in axes_order] # time and channels are always loadable as separate chunks as they go to separate vdbs
        imgdata = da.from_array(self.load_array(input_file), chunks=chunks)

        if len(axes_order) != len(imgdata.shape):
            raise ValueError("axes_order length does not match data shape: " + str(imgdata.shape))

        size_px = np.array([imgdata.shape[axes_order.find(dim)] if dim in axes_order else 0 for dim in 'xyz'])

        mask_channels = []
        if mask_channels_str != '':
            try:
                mask_channels = [int(ch.strip()) for ch in mask_channels_str.split(',') if '-' not in ch]
            except:
                raise ValueError("could not interpret maskchannels")
            if max(mask_channels) >= imgdata.shape[axes_order.find('c')]:
                raise ValueError(f"mask channel is too high, max is {imgdata.shape[axes_order.find('c')]-1}, it starts counting at 0" )
        
        ch_arrays = {}
        ch_array =  {'data': None, 'volume' : True, 'mask':False}
        if 'c' in axes_order:
            for ch in range(imgdata.shape[axes_order.find('c')]):
                ch_arrays[ch] = deepcopy(ch_array)
                ch_arrays[ch]['data'] = np.take(imgdata, indices=ch, axis=axes_order.find('c'))
        else:
            ch_arrays[0] = deepcopy(ch_array)
            ch_arrays[0]['data'] = imgdata
        axes_order = axes_order.replace("c","") 
        
        for ch in ch_arrays: 
            if ch in mask_channels:
                # this is a bit double because i want to extend the per-channel choices later
                ch_arrays[ch]['mask'] = True
                ch_arrays[ch]['volume'] = False

        return ch_arrays, size_px



