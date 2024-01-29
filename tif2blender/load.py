import bpy
from bpy.props import (StringProperty, FloatProperty,
                        PointerProperty
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
# from .nodes.nodeScale import scale_node_group
# from .nodes.nodesBoolmultiplex import axes_multiplexer_node_group
# from .nodes.nodeCrosshatch import crosshatch_node_group

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
        (tif.parents[0] / f"blender_volumes/{identifier}/").mkdir(exist_ok=True,parents=True)
        fname = str(tif.parents[0] / f"blender_volumes/{identifier}/{tif.stem}t_{t_ix}.vdb")
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
                vdb.write(fname, grids=grids)
    directory = str(tif.parents[0] / f"blender_volumes/{identifier}")
    return directory, timefiles
    # bpy.ops.object.volume_import(filepath=fname,directory=str(tif.parents[0] / f"blender_volumes/{identifier}"), files=timefiles,use_sequence_detection=True , align='WORLD', location=(0, 0, 0))
    # return bpy.context.view_layer.objects.active

def unpack_tif(input_file, axes_order, test=False, maskchannel=None):
    import tifffile
    with tifffile.TiffFile(input_file) as ifstif:
        imgdata = ifstif.asarray()

    if len(axes_order) != len(imgdata.shape):
        raise ValueError("axes_order length does not match data shape: " + str(imgdata.shape))

    imgdata = imgdata.astype(np.float32)
    # normalize entire space per axis

    mask_array = None
    if maskchannel != None:
        mask_array = imgdata.take(indices=maskchannel, axis=axes_order.find('c'))
        imgdata = np.delete(imgdata, maskchannel, axis=axes_order.find('c'))

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
    return vdb_files, bbox_px, size_px, otsus

# currently not easily testable
def import_volumes(vdb_files, scale, bbox_px):
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
        for dim in range(3):
            vol.lock_location[dim] = True
            vol.lock_rotation[dim] = True
            vol.lock_scale[dim] = True
        volumes.append(vol)
    return volumes


def load_mask(array, xy_sc):
    return


def load(input_file, xy_scale, z_scale, axes_order):
    
    if bpy.context.scene.TL_preset_environment:
        preset_environment()
            
    tif = Path(input_file)

    vdb_files, bbox_px, size_px, otsus = unpack_tif(input_file, axes_order)

    init_scale = 0.02
    scale =  np.array([1,1,z_scale/xy_scale])*init_scale

    volumes = import_volumes(vdb_files, scale, bbox_px)

    # recenter x, y, keep z at bottom
    center = np.array([0.5,0.5,0]) * size_px
    container = bpy.ops.mesh.primitive_cube_add(location=tuple(center*scale))

    container = bpy.context.view_layer.objects.active
    container = init_container(container, volumes, size_px, tif, xy_scale, z_scale, axes_order, init_scale)

    add_init_material(str(tif.name), volumes, otsus, axes_order)
    return



