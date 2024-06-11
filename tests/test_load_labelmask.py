import bpy
import os
import pytest
import itertools
import numpy as np
import tif2blender
from pathlib import Path
from .utils import get_verts
import json
import tif2blender.load_components as load_labelmask
import shutil
import hashlib
from tif2blender.handle_blender_structs import collection_by_name

def semi_random_data_labels(axes_order, arrtype):
    np.random.seed(11)
    shape = np.zeros(len(axes_order))  + 10

    if arrtype == 'nonsquare':
        shape = np.arange(len(axes_order)) + 2
    if 'c' in axes_order: # limit number of files
        shape[axes_order.find('c')] = 2
    if arrtype == 'single frame-channel':
        for dim in 'ct':
            if dim in axes_order:
                shape[axes_order.find(dim)] = 1
    shape = tuple(shape.astype(int))
    data = np.random.randint(low=0, high=5, size=shape)
    if arrtype == 'nonrandom':
        data = np.zeros(shape).flatten()
        for ix in range(len(data)):
            data[ix] = (ix//7) % 5 
        data= data.reshape(shape)

    return data.astype(int)

standard_orders = ['zyx', 'tzcyx', 'zcyx', 'xy']
test_folder = join(dirname(realpath(__file__)), "test_data")
# test_folder = Path(os.path.abspath(Path(__file__).parent / 'test_data'))


@pytest.mark.parametrize("axes_order", standard_orders)
@pytest.mark.parametrize('arrtype', ['nonrandom', 'nonsquare', 'single frame-channel', 'series'])
def test_export_labelmask(snapshot,axes_order, arrtype):
    np.random.seed(10)
    data = semi_random_data_labels(axes_order, arrtype)
    cache_dir = (test_folder / 'tmp' / f"{axes_order}_{arrtype}") 
    cache_dir.mkdir(exist_ok=True, parents=True)
    assert(cache_dir.exists())
    remake = True
    # load_labelmask(mask_arrays, scale, cache_coll, base_coll, cache_dir, remake, axes_order)
    channels = 1
    if 'c' in axes_order:
        channels = data.shape[axes_order.find('c')]
    timepoints = 1
    if 't' in axes_order:
        timepoints = data.shape[axes_order.find('t')]
    for c in range(channels):
        if 'c' in axes_order:
            # print(data.shape,axes_order, channels, axes_order.find('c'), data.shape[axes_order.find('c')])
            mask =  data.take(indices=c,axis=axes_order.find('c'))
        else:
            mask = data
            
        load_labelmask.export_alembic_and_loc(mask, c, cache_dir, remake, axes_order)
    snapshot.assert_match(str(data), f"data_{c}_{axes_order}_{arrtype}.json")
    
    for c in range(channels):
        assert(Path(load_labelmask.jsonfname(cache_dir, c)).exists())
        with open(load_labelmask.jsonfname(cache_dir, c), mode='r') as file: 
                fileContent = file.read()
        snapshot.assert_match(str(hashlib.md5(fileContent.encode('utf-8')).hexdigest()), f"locations_{c}_{axes_order}_{arrtype}.json")
        for t in range(timepoints):
            assert(Path(load_labelmask.abcfname(cache_dir, c, t)).exists())
            with open(load_labelmask.abcfname(cache_dir, c, t), mode='ab+') as file: 
                fileContent = file.read()
            snapshot.assert_match(str(hashlib.md5(fileContent).hexdigest()), f"outmask_{c}_{t}_{axes_order}_{arrtype}.txt")

    shutil.rmtree(cache_dir)
    return

foldernames = ['sequence',  'singleframe']    
scale = np.array([0.2, 0.2, 0.6])

@pytest.mark.parametrize("foldername", foldernames)
def test_import_abc(snapshot, foldername):
    maskchannel = 3 # hardcoded in data names
    cache_dir = test_folder / 'permanent_abcs' / foldername 
    objs, coll = load_labelmask.import_abc_and_loc(maskchannel, scale, cache_dir)
    verts = get_verts(objs, apply_modifiers=False)
    snapshot.assert_match(verts, f'abcload_{foldername}.txt')
    if foldername == 'sequence':
        bpy.context.scene.frame_set(2)
        verts2 = get_verts(objs, apply_modifiers=True)
        assert(verts != verts2)
        snapshot.assert_match(verts2, f'abcload_{foldername}_t2.txt')
    return



# def test_load_labelmask(snapshot):
#     axes_order ='tzcyx'
#     data = semi_random_data_labels(axes_order, 'nonrandom')
#     scale = np.array([0.1,0.2,0.3]) 
#     # TODO BUG find out why large sales give inconsistent snapshots
#     base_coll = collection_by_name('testbase')
#     cache_coll = collection_by_name('testcache')
#     cache_dir = (test_folder / 'tmp' / 'load_labelmask') 
#     cache_dir.mkdir(exist_ok=True, parents=True)
#     remake = False
#     channels = 1
#     if 'c' in axes_order:
#         channels = data.shape[axes_order.find('c')]

#     mask_arrays = {}
#     for ch in range(channels):
#         mask_arrays[ch] = {'data':data.take(indices=ch, axis=axes_order.find('c'))}
#     axes_order.replace('c', '')
#     mask_obj, mask_colls = load_labelmask.load_labelmask(mask_arrays, scale, cache_coll, base_coll, cache_dir, remake, axes_order)

#     objs = [obj for obj in mask_colls[0].all_objects]
    
#     assert(len(objs) == len(np.unique(data))-1)
#     assert(len(mask_obj.data.materials) == data.shape[axes_order.find('c')])

#     verts = get_verts(objs, apply_modifiers=False)
#     snapshot.assert_match(verts, f'maskload_1.txt')

#     shutil.rmtree(cache_dir)
#     cache_dir.mkdir(exist_ok=True, parents=True)
#     mask_obj, mask_colls = load_labelmask.load_labelmask(mask_arrays, scale, cache_coll, base_coll, cache_dir, remake, axes_order)
#     objs = [obj for obj in mask_colls[0].all_objects]

#     bpy.context.scene.frame_set(2)
#     verts2 = get_verts(objs, apply_modifiers=True)
#     assert(verts != verts2)
#     snapshot.assert_match(verts2, f'maskload_2.txt')
    
#     assert(objs[0].users_collection[0] in list(cache_coll[0].children))
#     assert(bpy.context.view_layer.active_layer_collection == base_coll[1])
#     bpy.context.scene.frame_set(0)
#     shutil.rmtree(cache_dir)
#     return    
