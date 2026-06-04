import os
os.environ["MIN_TEST"] = "1"
import bpy

from microscopynodes.file_to_array import *
from microscopynodes.handle_blender_structs.min_keys import min_keys
from microscopynodes.handle_blender_structs.node_handling import get_socket
import microscopynodes
from microscopynodes.ui.preferences import addon_preferences

import numpy as np
import pytest
import tifffile
import platform
import imageio.v3 as iio
from mathutils import Vector
from pathlib import Path
import dask.array as da

test_folder = Path(os.path.join(os.path.dirname(os.path.realpath(__file__)), "tmp_test_data"))
test_folder.mkdir(exist_ok=True)

print('imported utils')

def len_axis(dim, axes_order, shape):
        if dim in axes_order:
            return shape[axes_order.find(dim)]
        return 1

def take_index(imgdata, indices, dim, axes_order):
    if dim in axes_order:
        return da.take(imgdata, indices=indices, axis=axes_order.find(dim))
    return imgdata

def make_tif(path, arrtype):
    axes = "TZCYX"
    if arrtype == '5D_5cube':
        arr = np.ones((5,5,5,5,5), dtype=np.uint16)
    if arrtype == '2D_5x10':
        arr = np.ones((5,10), dtype=np.uint16)
        axes = "YX"
    if arrtype == '5D_nonrect':
        shape = [i for i in range(2,7)]
        arr = np.ones(tuple(shape), dtype=np.uint16)
    if arrtype == '3D_sparse_value':
        arr = np.zeros((24, 24, 24), dtype=np.uint16)
        arr[8:16, 9:15, 10:14] = 1
        axes = "ZYX"
    
    if arrtype != '3D_sparse_value':
        shape = arr.shape
        arr = arr.flatten()
        for ix in range(len(arr)):
            arr[ix] = ix % 12 # don't let values get too big, as all should be handlable as labelmask
        arr = arr.reshape(shape)
    # if not Path(path).exists():
    tifffile.imwrite(path, arr,metadata={"axes": axes}, imagej=True)
    return path, arr, axes.lower()
    



def prep_load(arrtype=None):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    microscopynodes._test_register()

    prefs = addon_preferences(bpy.context)
    bpy.context.scene.MiN_import_scale = "AUTO_SCALE"
    bpy.context.scene.MiN_import_loc = "XY_CENTER"
    prefs.surf_resolution = "0"
    prefs.invert_color = False
    prefs.cache_option = "TEMPORARY"
    prefs.cache_path = str(test_folder)
    if len(prefs.channels) == 0:
        prefs.set_channels(bpy.context)

    if arrtype is None:
        arrtype = '5D_5cube'
    
    path = test_folder / f'{arrtype}.tif'
    path, arr, axes_order = make_tif(path, arrtype)

    bpy.context.scene.MiN_input_file = str(path)
    bpy.context.scene.MiN_unit = "MICROMETER"
    # assert(arr_shape() == arr.shape)
    assert(len(bpy.context.scene.MiN_channelList) == len_axis('c', axes_order, arr.shape))
    return

def do_load():
    dataset_model = microscopynodes.parse_inputs.parse_blender_ui()
    microscopynodes.load.Scene.from_blender_ui()
    dataset = microscopynodes.load.Dataset(holder=bpy.context.scene.MiN_reload)
    dataset.set_state(
        dataset_model,
        update_data=bpy.context.scene.MiN_update_data,
        update_settings=bpy.context.scene.MiN_update_settings,
    )
    return dataset_model


def check_channels(dataset_model, test_render=True):
    img1 = None
    holder = bpy.context.scene.MiN_reload
    dataset = microscopynodes.load.Dataset(holder=holder)
    if test_render:
        img1 = quick_render('1')
        dataset.axes.object.hide_render = True
        img2 = quick_render('2')
        dataset.axes.object.hide_render = False
        assert(not np.array_equal(img1, img2))

    toggled = []
    for ch in dataset_model.channels:
        for min_type in [min_keys.SURFACE, min_keys.VOLUME, min_keys.LABELMASK]:
            if getattr(ch.viz, min_type.name.lower(), False):
                ch_obj = getattr(dataset, min_type.name.lower())
                if ch_obj is None:
                    raise ValueError(f"{min_type} not in dataset, while setting is True")
                assert(ch_obj.ch_present(ch))
                socket = get_socket(ch_obj.node_group, ch, min_type="SWITCH")
                ch_obj.gn_mod[socket.identifier] = False
                toggled.append((ch_obj, socket.identifier))

    if test_render:
        for ch_obj, socket_identifier in toggled:
            ch_obj.gn_mod[socket_identifier] = False
        for ch_obj, socket_identifier in toggled:
            img1 = quick_render('1')
            ch_obj.gn_mod[socket_identifier] = True
            img2 = quick_render('2')
            ch_obj.gn_mod[socket_identifier] = False
            if np.array_equal(img1, img2):
                raise ValueError(f"tried to turn off {socket_identifier}, render did not change")
            assert(not np.array_equal(img1, img2))
                
                

def quick_render(name):
    # Set the output file path
    output_file = str(test_folder / f'tmp{name}.png')
    scn = bpy.context.scene
    if scn.render.engine == "CYCLES":
        scn.cycles.samples = 16

    cam_obj = bpy.data.objects.get("MiN Test Camera")
    if cam_obj is None:
        cam = bpy.data.cameras.new("MiN Test Camera")
        cam_obj = bpy.data.objects.new("MiN Test Camera", cam)
        scn.collection.objects.link(cam_obj)
    cam_obj.data.type = "ORTHO"
    cam_obj.data.clip_start = 1e-6
    cam_obj.data.clip_end = 10000.0

    holder = bpy.context.scene.MiN_reload
    mins, maxs = loaded_holder_bounds(holder)
    center = (mins + maxs) / 2.0
    extent = np.maximum(maxs - mins, 1e-6)
    ortho_size = max(float(extent[0]), float(extent[1])) * 1.1
    cam_obj.data.ortho_scale = max(ortho_size, 1e-3)
    cam_obj.location = (float(center[0]), float(center[1]), float(maxs[2] + max(extent[2], ortho_size, 1.0)))
    cam_obj.rotation_euler = (0.0, 0.0, 0.0)
    bpy.context.scene.camera = cam_obj
    
    # Set the viewport resolution
    bpy.context.scene.render.resolution_x = 128
    bpy.context.scene.render.resolution_y = 128
    # Set the output format
    bpy.context.scene.render.image_settings.file_format = "PNG"
    scn.cycles.seed = 0
    if hasattr(scn.cycles, "use_animated_seed"):
        scn.cycles.use_animated_seed = False

    # Render the viewport and save the result
    
    bpy.ops.render.render()
    bpy.data.images["Render Result"].save_render(output_file)
    data = np.array(iio.imread(output_file))
    # os.remove(output_file)
    return data


def loaded_holder_bounds(holder):
    if holder is None:
        return np.array([-0.5, -0.5, -0.5]), np.array([0.5, 0.5, 0.5])

    corners = []
    for child in holder.children:
        for corner in getattr(child, "bound_box", []):
            corners.append(np.array(child.matrix_world @ Vector(corner), dtype=float))

    if not corners:
        return np.array([-0.5, -0.5, -0.5]), np.array([0.5, 0.5, 0.5])

    corners = np.array(corners, dtype=float)
    return corners.min(axis=0), corners.max(axis=0)


def grayscale_histogram_distance(img1, img2, bins=32):
    gray1 = img1[..., :3].astype(np.float32).mean(axis=-1)
    gray2 = img2[..., :3].astype(np.float32).mean(axis=-1)
    hist1, _ = np.histogram(gray1, bins=bins, range=(0.0, 255.0))
    hist2, _ = np.histogram(gray2, bins=bins, range=(0.0, 255.0))
    hist1 = hist1 / max(hist1.sum(), 1)
    hist2 = hist2 / max(hist2.sum(), 1)
    return 0.5 * np.abs(hist1 - hist2).sum()
