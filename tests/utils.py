from microscopynodes.handle_blender_structs import *
from microscopynodes.file_to_array import *
from microscopynodes.load_components import *
import microscopynodes

import bpy
import numpy as np
import os
import pytest
import tifffile
import platform
import imageio.v3 as iio


test_folder = Path(os.path.join(os.path.dirname(os.path.realpath(__file__)), "test_data"))
microscopynodes._test_register()

def len_axis(dim, axes_order, shape):
        if dim in axes_order:
            return shape[axes_order.find(dim)]
        return 1

def take_index(imgdata, indices, dim, axes_order):
    if dim in axes_order:
        return np.take(imgdata, indices=indices, axis=axes_order.find(dim))
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
    bpy.ops.wm.read_factory_settings(use_empty=True)

    if arrtype is None:
        arrtype = '5D_5cube'
    
    path = test_folder / f'{arrtype}.tif'
    path, arr, axes_order = make_tif(path, arrtype)

    bpy.context.scene.MiN_selected_cache_option = "Path"
    bpy.context.scene.MiN_explicit_cache_dir = str(test_folder)
    bpy.context.scene.MiN_cache_dir = str(test_folder)
    
    bpy.context.scene.MiN_input_file = str(path)
    # assert(arr_shape() == arr.shape)
    assert(len(bpy.context.scene.MiN_channelList) == len_axis('c', axes_order, arr.shape))
    return

def do_load():
    params = microscopynodes.load.load_init()
    # if platform.system() == 'Linux':
        # bpy.context.scene.MiN_remake = True
    params = microscopynodes.load.load_threaded(params)
    microscopynodes.load.load_blocking(params)
    return params[0]


def check_channels(ch_dicts, test_render=True):
    img1 = None
    objs = microscopynodes.load.parse_reload(bpy.data.objects[str(Path(bpy.context.scene.MiN_input_file).stem)])
    if test_render:
        img1 = quick_render('1')
        objs[min_keys.AXES].hide_render = True
        img2 = quick_render('2')
        objs[min_keys.AXES].hide_render = False
        assert(not np.array_equal(img1, img2))

    for ch in ch_dicts:
        for min_type in [min_keys.SURFACE, min_keys.VOLUME, min_keys.LABELMASK]:
            if ch[min_type]:
                if objs[min_type] is None:
                    raise ValueError(f"{min_type} not in objs, while setting is {ch[min_type]}")
                ch_obj = ChannelObjectFactory(min_type, objs[min_type])
                assert(ch_obj.ch_present(ch))
                if test_render:
                    socket = get_socket(ch_obj.node_group, ch, min_type="SWITCH")
                    img1 = quick_render('1')
                    ch_obj.gn_mod[socket.identifier] = False
                    img2 = quick_render('2')
                    ch_obj.gn_mod[socket.identifier] = True
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
    os.remove(output_file)
    return data