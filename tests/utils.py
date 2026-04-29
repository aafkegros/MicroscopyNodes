import os
os.environ["MIN_TEST"] = "1"
import bpy
import json

from microscopynodes.handle_blender_structs import *
from microscopynodes.file_to_array import *
import microscopynodes

import numpy as np
import pytest
import tifffile
import platform
import imageio.v3 as iio
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
    
    shape = arr.shape
    arr = arr.flatten()
    for ix in range(len(arr)):
        arr[ix] = ix % 12 # don't let values get too big, as all should be handlable as labelmask
    arr = arr.reshape(shape) 
    # if not Path(path).exists():
    tifffile.imwrite(path, arr,metadata={"axes": axes}, imagej=True)
    return path, arr, axes.lower()
    



def prep_load(arrtype=None):
    # microscopynodes._test_register()
    bpy.ops.wm.read_factory_settings(use_empty=True)


    pref_template = str(Path(test_folder).parent / "test_preferences_template.json")
    with open(pref_template) as f: 
        prefdct = json.load(f)
    prefdct['cache_path'] = str(test_folder)
    pref_path = test_folder / 'pref.json'
    with open(pref_path, 'w') as f: 
        json.dump(prefdct, f)
    bpy.context.scene.MiN_json_preferences = str(pref_path)

    if arrtype is None:
        arrtype = '5D_5cube'
    
    path = test_folder / f'{arrtype}.tif'
    path, arr, axes_order = make_tif(path, arrtype)

    # bpy.context.scene.MiN_selected_cache_option = "Path"
    # bpy.context.scene.MiN_explicit_cache_dir = str(test_folder)
    # bpy.context.scene.MiN_cache_dir = str(test_folder)
    
    bpy.context.scene.MiN_input_file = str(path)
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
            if ch.visible_as.get(min_type, False):
                ch_obj = getattr(dataset, min_type.name.lower())
                if ch_obj is None:
                    raise ValueError(f"{min_type} not in dataset, while setting is {ch.visible_as[min_type]}")
                assert(ch_obj.ch_present(ch))
                socket = get_socket(ch_obj.node_group, ch, min_type="SWITCH")
                ch_obj.gn_mod[socket.identifier] = False
                toggled.append((ch_obj, socket.identifier))

    if test_render:
        for ch_obj, socket_identifier in toggled:
            img1 = quick_render('1')
            ch_obj.gn_mod[socket_identifier] = True
            img2 = quick_render('2')
            ch_obj.gn_mod[socket_identifier] = False
            if np.array_equal(img1, img2):
                raise ValueError(f"{socket_identifier}, ")
            assert(not np.array_equal(img1, img2))
                
                

def quick_render(name):
    bpy.context.scene.cycles.samples = 16
    # Set the output file path
    output_file = str(test_folder / f'tmp{name}.png')
    scn = bpy.context.scene

    cam1 = bpy.data.cameras.new("Camera 1")
    cam1.lens = 40

    cam_obj1 = bpy.data.objects.new("Camera 1", cam1)
    cam_obj1.location = (.1, .1, .2)
    cam_obj1.rotation_euler = (0.7, 0, 2.3)
    scn.collection.objects.link(cam_obj1)
    bpy.context.scene.camera = cam_obj1
    
    # Set the viewport resolution
    bpy.context.scene.render.resolution_x = 128
    bpy.context.scene.render.resolution_y = 128
    # Set the output format
    bpy.context.scene.render.image_settings.file_format = "PNG"

    # Render the viewport and save the result
    
    bpy.ops.render.render()
    bpy.data.images["Render Result"].save_render(output_file)
    data = np.array(iio.imread(output_file))
    # os.remove(output_file)
    return data
