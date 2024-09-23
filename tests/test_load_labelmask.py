import bpy
import os
import pytest
import itertools
import numpy as np
import microscopynodes
from pathlib import Path
from .utils import get_verts
import json
import microscopynodes.load_components as load_labelmask
import shutil
import hashlib
from microscopynodes.handle_blender_structs import collection_by_name
from os.path import join, dirname, realpath
import dask.array as da

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

    return da.from_array(data.astype(int))

standard_orders = ['zyx', 'tzcyx', 'zcyx', 'xy']
test_folder = Path(join(dirname(realpath(__file__)), "test_data"))
# test_folder = Path(os.path.abspath(Path(__file__).parent / 'test_data'))


@pytest.mark.parametrize("axes_order", standard_orders)
@pytest.mark.parametrize('arrtype', ['nonrandom', 'nonsquare', 'single frame-channel', 'series'])
def test_io_labelmask(snapshot,axes_order, arrtype):
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
    # for c in range(channels):

    #     ch = {
    #         'data' : mask,
    #         'labelmask' : True,
    #         'ix':c,
    #         'surf_resolution': min(c,3)
    #     }
    #     load_labelmask.export_alembic_and_loc(ch, cache_dir, remake, axes_order)
    # snapshot.assert_match(str(data.compute()), f"data_{c}_{axes_order}_{arrtype}.json")
    
    for c in range(channels):
        if 'c' in axes_order:
            # print(data.shape,axes_order, channels, axes_order.find('c'), data.shape[axes_order.find('c')])
            mask =  np.take(data, indices=c,axis=axes_order.find('c'))
        else:
            mask = data
        ch = {
            'data' : mask,
            'labelmask' : True,
            'ix':c,
            'surf_resolution': min(c,3),
            'collection' : None,
            'name':'testfile'
        }
        load_labelmask.export_alembic_and_loc(ch, cache_dir, remake, axes_order)
        assert(Path(load_labelmask.jsonfname(cache_dir, c,  min(c,3))).exists())
        with open(load_labelmask.jsonfname(cache_dir, c,  min(c,3)), mode='r') as file: 
                fileContent = file.read()
        snapshot.assert_match(str(hashlib.md5(fileContent.encode('utf-8')).hexdigest()), f"locations_{c}_{axes_order}_{arrtype}.json")
        bpy.context.scene.frame_set(0)
        objs = load_labelmask.import_abc_and_loc(ch, np.array([0.02,0.02, 0.1]), cache_dir,is_sequence=('t' in axes_order))
        verts1= get_verts(objs, apply_modifiers=True)
        snapshot.assert_match(verts1, f"outmask_{c}_{axes_order}_{arrtype}_verts1.txt")
        if 't' in axes_order and mask.shape[axes_order.find('t')] > 1:
            objs2 = load_labelmask.import_abc_and_loc(ch, np.array([0.02,0.02, 0.1]), cache_dir,is_sequence=('t' in axes_order))
            bpy.context.scene.frame_set(1)
            verts2 = get_verts(objs2, apply_modifiers=True)
            snapshot.assert_match(verts2, f"outmask_{c}_{axes_order}_{arrtype}_verts2.txt")
            assert(verts1 != verts2)

    shutil.rmtree(cache_dir)
    return
