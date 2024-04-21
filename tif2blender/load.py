import bpy
from bpy.props import (StringProperty, FloatProperty,
                        PointerProperty, IntProperty
                        )

import subprocess
from pathlib import Path
import os
import pip
import numpy as np

from mathutils import Color
from . import t2b_nodes
from .initial_global_settings import * 
from .initial_node_settings import * 
from .load_labelmask import load_labelmask
from .collection_handling import *


def changePathTif(self, context):
    # infers metadata, resets to default if not found
    # the raise gets handled upstream, so only prints to cli, somehow.
    try: 
        import tifffile
        with tifffile.TiffFile(context.scene.path_tif) as ifstif:
            try:
                context.scene.axes_order = ifstif.series[0].axes.lower().replace('s', 'c')
            except Exception as e:
                print(e)
                context.scene.property_unset("axes_order")
            try:
                context.scene.xy_size = ifstif.pages[0].tags['XResolution'].value[1]/ifstif.pages[0].tags['XResolution'].value[0]
            except Exception as e:
                print(e)
                context.scene.property_unset("xy_size")
            try:
                context.scene.z_size = dict(ifstif.imagej_metadata)['spacing']
            except Exception as e:
                print(e)
                context.scene.property_unset("z_size")
            # if this gets improved in bpy: set max of maskchannel selector
    except Exception as e:
        context.scene.property_unset("axes_order")
        context.scene.property_unset("xy_size")
        context.scene.property_unset("z_size")
        raise
    return

bpy.types.Scene.TL_remake = bpy.props.BoolProperty(
    name = "TL_remake", 
    description = "Force remaking vdb files",
    default = False
    )

bpy.types.Scene.TL_preset_environment = bpy.props.BoolProperty(
    name = "TL_preset_environment", 
    description = "Set environment variables",
    default = True
    )

bpy.types.Scene.TL_otsu = bpy.props.BoolProperty(
    name = "TL_otsu", 
    description = "Otsu on load (slow for big data)",
    default = True
    )

bpy.types.Scene.path_tif = StringProperty(
        name="",
        description="tif file",
        update=changePathTif,
        options = {'TEXTEDIT_UPDATE'},
        default="",
        maxlen=1024,
        subtype='FILE_PATH')

bpy.types.Scene.T2B_cache_dir = StringProperty(
        description = 'Location to cache VDB and ABC files',
    options = {'TEXTEDIT_UPDATE'},
    default = str(Path('~', '.tif2blender').expanduser()),
    subtype = 'FILE_PATH'
    )

bpy.types.Scene.axes_order = StringProperty(
        name="",
        description="axes order (only z is used currently)",
        default="zyx",
        maxlen=6)
    
bpy.types.Scene.xy_size = FloatProperty(
        name="",
        description="xy physical pixel size in micrometer",
        default=1.0)
    
bpy.types.Scene.z_size = FloatProperty(
        name="",
        description="z physical pixel size in micrometer",
        default=1.0)

bpy.types.Scene.T2B_mask_channels = StringProperty(
        name="",
        description="channels with an integer label mask",
        )


# note that this will write a dynamically linked vdb file, so rerunning the script on a file with the same name
# in the same folder, but with different data, will change the previously loaded data.

def make_vdb(imgdata, x_ix, y_ix, z_ix, axes_order_in, tif, test=False):
    if test: 
        # pyopenvdb is not available outside of blender; for tests tifs are written
        # moving writing to a separate function would induce a very high RAM cost
        import tifffile
    else:
        import pyopenvdb as vdb

    
    axes_order = axes_order_in
    if axes_order.find('c') == -1:
        imgdata =  np.expand_dims(imgdata, axis=-1)
        axes_order = axes_order + "c"
    if axes_order.find('t') == -1:
        imgdata =  np.expand_dims(imgdata, axis=-1)
        axes_order = axes_order + "t"
    
    timefiles = []

    for t_ix, t in enumerate(range(imgdata.shape[axes_order.find('t')])):
        identifier = "x"+str(x_ix)+"y"+str(y_ix)+"z"+str(z_ix)
        (Path(bpy.context.scene.T2B_cache_dir)/f"{identifier}").mkdir(exist_ok=True,parents=True)
        fname = (Path(bpy.context.scene.T2B_cache_dir)/f"{identifier}"/f"{tif.stem}t_{t_ix}.vdb")
        entry = {"name":f"{tif.stem}t_{t_ix}.vdb"}
        timefiles.append(entry)
        if (not os.path.isfile(fname)) or bpy.context.scene.TL_remake:
            frame = imgdata.take(indices=t,axis=axes_order.find('t'))
            channels = []
            for ch in range(imgdata.shape[axes_order.find('c')]):
                frame_axes = axes_order.replace("t","")
                chdata = frame.take(indices=ch,axis=frame_axes.find('c'))
                slice_axes = frame_axes.replace("c","")
                chdata = np.moveaxis(chdata, [slice_axes.find('x'),slice_axes.find('y'),slice_axes.find('z')],[0,1,2]).copy()
                channels.append(chdata)
            if test: 
                tifffile.imwrite(fname[:-4]+".tif", np.array(channels).astype(np.uint8) ,metadata={"axes":'cxyz'},photometric='minisblack', planarconfig='separate')
            else:
                grids = []
                for ch, chdata in enumerate(channels):
                    grid = vdb.FloatGrid()
                    grid.name = "channel " + str(ch)
                    grid.copyFromArray(chdata)
                    grids.append(grid)
                vdb.write(str(fname), grids=grids)
    directory = str(Path(bpy.context.scene.T2B_cache_dir)/f"{identifier}")
    return directory, timefiles


def unpack_tif(input_file, axes_order, test=False):
    import tifffile
    with tifffile.TiffFile(input_file) as ifstif:
        imgdata = ifstif.asarray()

    if len(axes_order) != len(imgdata.shape):
        raise ValueError("axes_order length does not match data shape: " + str(imgdata.shape))

    mask_channels = []
    if bpy.context.scene.T2B_mask_channels != '':
        try:
            mask_channels = [int(ch.strip()) for ch in bpy.context.scene.T2B_mask_channels.split(',') if '-' not in ch]
            # mask_channels.extend([list(np.arange(int(ch.strip().split('-')[0]),int(ch.strip().split('-')[1]))) for ch in bpy.context.scene.T2B_mask_channels.split(',')if '-' in ch])
        except:
            raise ValueError("could not interpret maskchannels")
        if max(mask_channels) >= imgdata.shape[axes_order.find('c')]:
            raise ValueError(f"mask channel is too high, max is {imgdata.shape[axes_order.find('c')]-1}, it starts counting at 0" )
    

    
    mask_arrays = {}
    for ch in mask_channels:
        mask_arrays[ch] = imgdata.take(indices=ch, axis=axes_order.find('c'))
    imgdata = np.delete(imgdata, mask_channels, axis=axes_order.find('c'))
    
    # normalize values per channel
    imgdata = imgdata.astype(np.float32)
    if 'c' in axes_order:
        ch_first = np.moveaxis(imgdata, axes_order.find('c'), 0)
        for chix, chdata in enumerate(ch_first):
            ch_first[chix] /= np.max(chdata)
        channels = imgdata.shape[axes_order.find('c')]
    else:
        imgdata /= np.max(imgdata)
        channels = 1

    # 2048 is maximum grid size for Eevee rendering, so grids are split for multiple
    xyz = [axes_order.find('x'),axes_order.find('y'),axes_order.find('z')]
    n_splits = [(imgdata.shape[dim] // 2048)+ 1 for dim in xyz]
    # otsu compute in z MIP
    otsus = [0] * channels
    
    if bpy.context.scene.TL_otsu:
        for channel in range(channels):
            if channels > 1:
                im = imgdata.take(indices=channel, axis=axes_order.find('c'))
            else:
                im = imgdata
            ch_axes = axes_order.replace("c","")
            z_MIP = np.amax(im, axis = ch_axes.find('z'))
            threshold_range = np.linspace(0,1,101)
            criterias = [compute_otsu_criteria(z_MIP, th) for th in threshold_range]
            otsus[channel] = threshold_range[np.argmin(criterias)]

    # Loops over all axes and splits based on length
    # reassembles in negative coordinates, parents all to a parent at (half_x, half_y, bottom) that is then translated to (0,0,0)
    volumes =[]
    vdb_files = {}
    a_chunks = np.array_split(imgdata, n_splits[0], axis=axes_order.find('x'))
    for a_ix, a_chunk in enumerate(a_chunks):
        b_chunks = np.array_split(a_chunk, n_splits[1], axis=axes_order.find('y'))
        for b_ix, b_chunk in enumerate(b_chunks):
            c_chunks = np.array_split(b_chunk, n_splits[2], axis=axes_order.find('z'))
            for c_ix, c_chunk in enumerate(reversed(c_chunks)):
                directory, time_vdbs = make_vdb(c_chunk, a_ix, b_ix, c_ix, axes_order, Path(input_file), test=test)
                vdb_files[(a_ix,b_ix,c_ix)] = {"directory" : directory, "files": time_vdbs}
    size_px = np.array([imgdata.shape[xyz[0]], imgdata.shape[xyz[1]], imgdata.shape[xyz[2]]])
    bbox_px = size_px//np.array(n_splits)
    return vdb_files, bbox_px, size_px, otsus, mask_arrays

# currently not easily testable
def import_volumes(vdb_files, scale, bbox_px):
    if len(vdb_files) == 0:
        return [], []
    parentcoll, parentlcoll = get_current_collection()
    vol_collection, _ = make_subcollection('volumes')
    volumes = []
    # necessary to support multi-file import
    bpy.types.Scene.files: CollectionProperty(
        type=bpy.types.OperatorFileListElement,
        options={'HIDDEN', 'SKIP_SAVE'},
    )
    for pos, vdbs in vdb_files.items():
        fname = str(Path(vdbs['directory'])/Path(vdbs['files'][0]['name']))
        bpy.ops.object.volume_import(filepath=fname,directory=vdbs['directory'], files=vdbs['files'],use_sequence_detection=True , align='WORLD', location=(0, 0, 0))
        vol = bpy.context.view_layer.objects.active
        vol.scale = scale
        vol.location = tuple(np.array(pos) * bbox_px *scale)
        vol.data.frame_start = 0
        for dim in range(3):
            vol.lock_location[dim] = True
            vol.lock_rotation[dim] = True
            vol.lock_scale[dim] = True
        volumes.append(vol)
    
    collection_activate(parentcoll, parentlcoll)
    return volumes, [vol_collection]



def load(input_file, xy_scale, z_scale, axes_order):
    orig_cache = bpy.context.scene.T2B_cache_dir
    bpy.context.scene.T2B_cache_dir = str(Path(bpy.context.scene.T2B_cache_dir) / Path(input_file).stem)
    
    collection_by_name('cache')
    cache_coll, cache_lcoll = collection_by_name(Path(input_file).stem, supercollections=['cache'], duplicate=True)
    
    if bpy.context.scene.TL_preset_environment:
        preset_environment()
            
    tif = Path(input_file)

    center_loc = np.array([0.5,0.5,0]) # offset of center (center in x, y, z of obj)
    init_scale = 0.02
    scale =  np.array([1,1,z_scale/xy_scale])*init_scale

    vdb_files, bbox_px, size_px, otsus, mask_arrays = unpack_tif(input_file, axes_order)
    
    vol_obj = None
    if len(vdb_files) > 0:
        collection_activate(cache_coll,cache_lcoll)
        volumes, vcoll = import_volumes(vdb_files, scale, bbox_px)
        collection_by_name("Collection")
        vol_obj = init_holder('volume',vcoll, [volume_material(volumes, otsus, axes_order)])

    mask_obj = None
    if len(mask_arrays) > 0:
        collection_activate(cache_coll,cache_lcoll)
        masks, mask_colls, mask_shaders = load_labelmask(mask_arrays, scale)
        collection_by_name("Collection")
        mask_obj = init_holder('masks' ,mask_colls, mask_shaders)
    
    loc =  tuple(center_loc * size_px*scale)
    axes_obj = init_axes(size_px, Path(input_file), xy_scale, z_scale, axes_order, init_scale, loc)
    
    container = init_container([axes_obj, mask_obj, vol_obj],location=loc, name=tif.stem)
    collection_deactivate('cache')
    axes_obj.select_set(True)

    bpy.context.scene.T2B_cache_dir = orig_cache
    return



