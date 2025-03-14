import bpy
from pathlib import Path
import numpy as np
import dask.array as da
from copy import deepcopy

class ArrayLoader():
    suffix = None

    def checkPath(self):
        return Path(bpy.context.scene.MiN_input_file).suffix in self.suffixes

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

        channels = imgdata.shape[axes_order.find('c')] if 'c' in axes_order else 1
        ix = 0
        for ch in ch_dicts:
            if ch['data'] is None:
                ch['data'] = np.take(imgdata, indices=ix, axis=axes_order.find('c')) if 'c' in axes_order else imgdata
                ix += 1
            if np.issubdtype(ch['data'].dtype,np.floating):
                ch['max_val'] = np.max(ch['data'])
            if ix >= channels:
                break
        return 

    def parse_unit(self, unit_str):
        if unit_str in ['A', 'Å', '\\u00C5','ANGSTROM', 'ÅNGSTROM','ÅNGSTRÖM', 'Ångstrom','angstrom','ångström','ångstrom']:
            return "ANGSTROM"
        elif unit_str in ['nm', 'nanometer', 'NM', 'NANOMETER']:
            return "NANOMETER"
        elif unit_str in ['\\u00B5m', 'micron', 'micrometer', 'microns', 'um', 'µm']:
            return "MICROMETER"
        elif unit_str in ['mm', 'millimeter', 'MM', 'MILLIMETER']:
            return "MILLIMETER"
        elif unit_str in ['m', 'meter', 'M', 'METER']:
            return "METER"
        return "PIXEL"


        


