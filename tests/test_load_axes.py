import bpy
import os
import pytest
import itertools
import numpy as np
import tif2blender
from pathlib import Path
from .utils import get_verts, remove_all_objects
import json
import tif2blender.load_components as load_axes
import shutil
import hashlib
from tif2blender.handle_blender_structs import collection_by_name


px_sizes = [np.array([2048, 2048, 50]), np.array([10,10,1]), np.array([4069, 2031,500])]
sizes = [(1, 1), (0.1, 1), (0.01, 0.02), (10, 20)]
@pytest.mark.parametrize('size_px', px_sizes)
@pytest.mark.parametrize('size', sizes)
def test_load_axes(snapshot, size_px, size):
    remove_all_objects
    # These are currently not editable values, so i test with defaults
    center_loc = np.array([0.5,0.5,0]) 

    xy_size, z_size = size
    init_scale = 0.02    
    scale =  np.array([1,1,z_size/xy_size])*init_scale

    loc =  tuple(center_loc * size_px*scale)
    input_file = '/path/to/name.tif'
    print(size_px, init_scale, loc, xy_size, z_size, input_file)
    axes_obj = load_axes.load_axes(size_px, init_scale, loc, xy_size, z_size, input_file)

    assert(len(axes_obj.modifiers) == 1)
    node_group = axes_obj.modifiers[-1].node_group
    nodes = node_group.nodes
    links = node_group.links   

    print([node for node in nodes])

    verts = get_verts([axes_obj], apply_modifiers=True)
    snapshot.assert_match(verts, f"axes_{sum(size_px)}_{np.sum(np.array(sizes))} ")
    assert("Error" not in verts)
    # check if only cube persists:
    assert( np.count_nonzero(np.abs([(v.co.x, v.co.y, v.co.z) for v in axes_obj.data.vertices])-1)!=0)
    
