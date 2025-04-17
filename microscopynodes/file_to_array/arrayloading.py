import bpy
from pathlib import Path
import numpy as np
import dask.array as da
from .arrayoptions import copy_array_option, selected_array_option
from ..handle_blender_structs import len_axis

MAX_BLENDER_SIZE_GIB = 4

class ArrayLoader():
    # the suffixes of the file path
    suffix = [None]

    # callback functions
    def check_path(self):
        return Path(bpy.context.scene.MiN_input_file).suffix in self.suffixes

    def change_path(self, context): 
        # only called if check_path == True
        self.set_file_globals(bpy.context.scene.MiN_input_file)
        self.reset_options(bpy.context.scene.MiN_input_file)
        return

    def reset_options(self, context):
        bpy.context.scene.MiN_array_options.clear()
        self.fill_array_options(bpy.context.scene.MiN_input_file) 
        self._add_generated_scales() # workaround for 4 GiB limit
        self._set_ui()
        self._write_ch_names_to_channels()
        bpy.context.scene.MiN_selected_array_option = str(len(bpy.context.scene.MiN_array_options) - 1)
        return


    # -- abstract methods to implement in subclass -- 

    def set_file_globals(self, input_file):
        # can set the following:
        self._set_axes_order("") # OBLIGATORY - takes a string of tcxyz in any order or subset of these
        self._set_unit("") # OPTIONAL - tries to parse unit string, defaults are "ANGSTROM", "NANOMETER", "MICROMETER", "MILLIMETER", "METER"
        self._set_ch_names([]) # OPTIONAL - sets a list of channel names from file
        return

    def fill_array_options(self, input_file):
        # uses add_array_option() to fill out a list of all native arrays
        return

    def load_array(self, input_file, array_option):
        # gets the array data from the selected option
        return 


    # -- default methods --

    def _set_unit(self, unit_str):
        try: 
            bpy.context.scene.MiN_unit = parse_unit(unit_str)
        except Exception as e:
            print(f'did not parse unit ({unit_str})', e)
            bpy.context.scene.property_unset("MiN_unit")
        
    def _set_axes_order(self, axes_order):
        try: 
            bpy.context.scene.MiN_axes_order = axes_order
        except:
            print('did not parse axis order')
            bpy.context.scene.property_unset("MiN_axes_order")
    
    def _set_ch_names(self, lst):
        try:
            bpy.context.scene.MiN_ch_names = "|".join([str(name) for name in lst])
        except:
            bpy.context.scene.property_unset('MiN_ch_names')
    
    def _write_ch_names_to_channels(self):
        # setting of channel list can only be done once n channels is known - which is inferred from array
        if bpy.context.scene.MiN_ch_names == "":
            return
        ch_names = bpy.context.scene.MiN_ch_names.split("|")
        for ix, ch in enumerate(bpy.context.scene.MiN_channelList):
            ch['name'] = ch_names[ix % len(ch_names)]
        return
        
    def shape(self):
        return selected_array_scale().shape()
        
    def _add_generated_scales(self):
        # this is a workaround for blender/blender#136263 - scales over 4 GiB give issues in Eevee and Viewport
        # takes the last named scale and generates smaller scales - these will be downscaled by Microscopy Nodes
        last_option = bpy.context.scene.MiN_array_options[-1] # guaranteed to be last in zarr/tif
        if last_option.size_gibibytes(exclude_dims='ct') > MAX_BLENDER_SIZE_GIB and last_option.len_axis('c') > 1:
            scale_option = copy_array_option(copy_from = last_option)
            while scale_option.size_gibibytes(exclude_dims='ct') > MAX_BLENDER_SIZE_GIB:
                scale_option.resize((2,2,1))
                if scale_option.size_gibibytes(exclude_dims='ct') > MAX_BLENDER_SIZE_GIB:
                    scale_option.resize((1,1,2))

        if last_option.size_gibibytes(exclude_dims='t') > MAX_BLENDER_SIZE_GIB:
            scale_option = copy_array_option(copy_from = last_option)
            while scale_option.size_gibibytes(exclude_dims='t') > MAX_BLENDER_SIZE_GIB:
                scale_option.resize((2,2,1))
                if scale_option.size_gibibytes(exclude_dims='t') > MAX_BLENDER_SIZE_GIB:
                    scale_option.resize((1,1,2))
        return
    

    def _set_ui(self):
        for option in bpy.context.scene.MiN_array_options:
            option.ui_text = f"{option.shape()}, up to {option.human_size()}"
            if len(option['path']) > 0:
                option.ui_text =  f"{option['path']}: {option.ui_text}"
            if option.is_rescaled:
                if option.scale()[2] == 1:
                    option.ui_text = f"{option.ui_text}, downscaled in XY"
                else:
                    option.ui_text = f"{option.ui_text}, downscaled in XYZ"

            if option.is_rescaled:
                option.description = "Downscaled volume. "
            else:
                option.description = "Native volume. "

            if option.size_gibibytes(exclude_dims='t') < MAX_BLENDER_SIZE_GIB:
                option.icon = 'VOLUME_DATA'
                option.description += "Full array can easily fit into Blender"
            elif option.size_gibibytes(exclude_dims='ct') < MAX_BLENDER_SIZE_GIB:
                option.icon = 'EVENT_ONEKEY'
                option.description += "One volume channel possible at this scale in Eevee and Viewport (limited to 4 GiB per timepoint)"
            else:
                option.icon = 'WARNING_LARGE'
                option.description += "This scale will only work in Cycles render mode - may cause freezing in other modes."
        return

    def unpack_array(self, ch_dicts):
        # this makes the array a dictionary of single channels, as Mi Nodes has a relatively single-channel data model
        # dask array makes sure lazy actions actually get performed lazily
        axes_order = bpy.context.scene.MiN_axes_order
        
        chunks = ['auto' if dim in 'xyz' else 1 for dim in axes_order] # time and channels are always loadable as separate chunks as they go to separate vdbs
        imgdata = da.from_array(self.load_array(bpy.context.scene.MiN_input_file, selected_array_option()), chunks=chunks) 
        
        if len(axes_order) != len(imgdata.shape):
            raise ValueError("axes_order length does not match data shape: " + str(imgdata.shape))

        if selected_array_option().is_rescaled:
            imgdata = map_resize(imgdata)
            imgdata = imgdata.compute_chunk_sizes()
        ix = 0
        for ix, ch in enumerate(ch_dicts):
            if ch['data'] is None:
                print(ix, axes_order.find('c'), axes_order.find('t'))
                ch['data'] = np.take(imgdata, indices=ix, axis=axes_order.find('c')) if 'c' in axes_order else imgdata
                if np.issubdtype(ch['data'].dtype,np.floating):
                    ch['max_val'] = np.max(ch['data'])
            if ix >= selected_array_option().len_axis('c'): 
                break
        return 

def parse_unit(unit_str):
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

def map_resize(dask_arr):
    import scipy.ndimage as ndi
    scale = np.array(dask_arr.shape)/np.array(selected_array_option().shape())
    return dask_arr.map_blocks(lambda block: ndi.zoom(block,1/scale, order=0))  
    # return resampled
    # Resize whole array in one go (requires rechunked single chunk array)
    # resampled = dask_arr.map_blocks(
    #     lambda block: skimage.transform.resize(block, output_shape, preserve_range=True, anti_aliasing=False),
    #     chunks=tuple(output_chunkshape),
    #     dtype=dask_arr.dtype
    # )
    # fullchunks = [selected_array_option().len_axis(dim) if dim in 'xyz' else 1 for dim in bpy.context.scene.MiN_axes_order]
    # print(bpy.context.scene.MiN_axes_order)
   
    # output_chunkshape = [output_axlen if dim in 'xyz' else 1 for dim, output_axlen in zip(bpy.context.scene.MiN_axes_order, output_shape)]
    # print(dask_arr, output_shape, fullchunks, output_chunkshape)
    # return dask
    # output_shape = [output_shape[axes_] if dim in 'xyz' else 1 for dim in bpy.context.scene.MiN_axes_order]
    # resampled = dask_arr.map_blocks(lambda block: skimage.transform.resize(block,output_shape, preserve_range=True), chunks)

    # return resampled