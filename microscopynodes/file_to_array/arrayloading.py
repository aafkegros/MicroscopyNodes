import bpy
from pathlib import Path
import numpy as np
import dask.array as da
from copy import deepcopy


class ArrayLoader():
    # the suffixes of the file path
    suffix = [None]

    # callback functions
    def check_path(self):
        return Path(bpy.context.scene.MiN_input_file).suffix in self.suffixes

    def change_path(self, context): 
        # only called if check_path == True
        self.set_unit_and_axes_order(bpy.context.scene.MiN_input_file)
        self.reset_options(bpy.context.scene.MiN_input_file)
        return

    def reset_options(self, context):
        bpy.context.scene.MiN_array_options.clear()
        self.fill_array_options(bpy.context.scene.MiN_input_file) 
        self._add_generated_scales() # workaround for 4 GiB limit
        self._set_ui()
        bpy.context.scene.MiN_selected_array_option = len(bpy.context.scene.MiN_array_options) - 1
        return


    # -- abstract methods to implement in subclass -- 

    def set_unit_and_axes_order(self, input_file):
        # sets bpy.context.scene.MiN_axes_order and bpy.context.scene.MiN_unit
        return

    def fill_array_options(self, input_file):
        # uses self.add_option() to fill out a list of all native arrays
        return

    def load_array(self, input_file, array_option):
        # gets the array data from the option
        return 


    # -- default methods --

    def _set_unit(self, unit_str):
        try: 
            bpy.context.scene.MiN_unit = parse_unit(unit_str)
        except:
            print('did not parse unit')
            bpy.context.scene.property_unset("MiN_unit")
        
    def _set_axes_order(self, axes_order):
        try: 
            bpy.context.scene.MiN_axes_order = axes_order
        except:
            print('did not parse axis order')
            bpy.context.scene.property_unset("MiN_axes_order")
        
    def shape(self):
        return selected_array_scale().shape()
        
    def size_bytes(self, level, exclude_dims=''):
        estimated_max_size = 1
        for dim in level.shape():
            estimated_max_size *= dim
        for dim in exclude_dims:
            estimated_max_size / level.len_axis(dim)
        return estimated_max_size *4 # vdb's are 32 bit floats == 4 byte per voxel
    
    def size_gibibytes(self, level, exclude_dims=''):
        return self.size_bytes(level, exclude_dims) /  2**30

    def _add_generated_scales(self):
        # this is a workaround for blender/blender#136263 - scales over 4 GiB give issues in Eevee and Viewport
        # takes the last named scale and generates smaller scales - these will be downscaled by Microscopy Nodes
        smallest = bpy.context.scene.MiN_array_options[-1] # guaranteed to be last in zarr/tif
        gib_full = self.size_gibibytes(smallest, exclude_dims='t')
        if gib_full > 4 and smallest.len_axis('c') > 1:
            gib_one_c = self.size_gibibytes(smallest, exclude_dims='ct') 
            scale_option = self.add_option(copy_from = smallest)
            self._resize(scale_option, 3.99/gib_one_c)
        if gib_full > 4:
            scale_option = self.add_option(copy_from = smallest)
            self._resize(scale_option, 3.99/gib_full)
        return
    
    def _resize(self, option, scaling_factor):
        # resizes the description of the scale only - resizing of array is called in unpack_array
        option.is_rescaled = True
        scaling_factor = scaling_factor ** (1/3)
        print(scaling_factor, " scaling factor")
        newshape = []
        for dim, axislen in zip(bpy.context.scene.MiN_axes_order, option.shape()):
            if dim in 'xyz':
                newshape.append(int(axislen * scaling_factor))
            else:
                newshape.append(axislen)
        option.set_shape(newshape)

    def _set_ui(self):
        for option in bpy.context.scene.MiN_array_options:
            option.ui_text = f"{option.shape()}, up to {human_size(self.size_bytes(option))}"
            if len(option['path']) > 0:
                option.ui_text =  f"{scale['path']}: {option.ui_text}"
            
            if option.is_rescaled:
                option.description = "Downscaled volume. "
            else:
                option.description = "Native volume. "

            if self.size_gibibytes(option, exclude_dims='t') < 4:
                option.icon = 'OUTLINER_OB_VOLUME'
                option.description += "Full array can easily fit into Blender"
            elif self.size_gibibytes(option, exclude_dims='ct') < 4:
                option.icon = 'VOLUME_DATA'
                option.description += "One volume channel possible at this scale in Eevee and Viewport (limited to 4 GiB per timepoint)"
            else:
                option.icon = 'WARNING_LARGE'
                option.description += "This scale will only work in Cycles render mode - may cause freezing in other modes."
            print(option.icon)
        return


    def unpack_array(self, input_file, axes_order, ch_dicts):
        # this makes the array a dictionary of single channels, as Mi Nodes has a relatively single-channel data model
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

    def add_option(self, xy_size=1.0, z_size=1.0, shape=(1,1,1), copy_from=None, path="", store="", ch_names=""):
        level = bpy.context.scene.MiN_array_options.add()
        if copy_from is not None:
            for key in copy_from.keys():
                setattr(level, key, getattr(copy_from, key))
            level.identifier = len(bpy.context.scene.MiN_array_options)
            return level
        # make sure keys exist
        level.identifier = len(bpy.context.scene.MiN_array_options)
        level.xy_size = xy_size
        level.z_size = xy_size
        level.set_shape(shape)
        
        level.path = path
        level.store = store
        level.ch_names = ch_names

        level.is_rescaled = False
        level.icon = ""
        level.ui_text = ""
        level.description = ""
        return level

    def parse_unit(self, unit_str):
        if unit_str in ['A', 'Å', '\\u00C5','ANGSTROM', 'ÅNGSTROM','ÅNGSTRÖM', 'Ångstrom','angstrom','ångström','ångstrom']:
            return "ANGSTROM"
        elif unit_str in ['nm', 'nanometer', 'NM', 'NANOMETER']:
            return "NANOMETER"
        elif unit_str in ['\\u00B5m', 'micron', 'micrometer', 'microns', 'um', 'µm', 'MICROMETER']:
            return "MICROMETER"
        elif unit_str in ['mm', 'millimeter', 'MM', 'MILLIMETER']:
            return "MILLIMETER"
        elif unit_str in ['m', 'meter', 'M', 'METER']:
            return "METER"
        return "AU"

    # for level in bpy.context.scene.MiN_array_options:
    #     if level.identifier == bpy.context.scene.MiN_selected_scale:
    #         return level


        
def human_size(bytes, units=[' bytes', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB', 'EiB']):
    return f"{bytes:.2f} {units[0]}" if bytes < 1024 else human_size(bytes / 1024, units[1:])
