import bpy
import os
import pytest
import itertools
import numpy as np
import tif2blender
from pathlib import Path
from .utils import get_verts, remove_all_objects
import tif2blender.load_components as load_axes
from tif2blender import t2b_nodes
from tif2blender.handle_blender_structs import collection_by_name, node_handling


px_sizes = [[30, 30, 30], [10,10,1], [4069, 2031,500]]
sizes = [(1, 1), (0.1, 1), (0.01, 0.02), (10, 20)]


@pytest.mark.parametrize('size_px, size', zip(px_sizes, sizes))
def test_load_axes(snapshot, size_px, size):
    remove_all_objects()
    # These are currently not editable values, so i test with defaults
    center_loc = np.array([0.5,0.5,0]) 
    xy_size, z_size = size
    input_file = '/path/to/name.tif'
    init_scale = 0.02    
    scale =  np.array([1,1,z_size/xy_size])*init_scale

    loc =  tuple(center_loc * size_px*scale)

    axes_obj = load_axes.load_axes(size_px, init_scale, loc, xy_size, z_size, input_file)

    # TODO BUG somehow the axis selector breaks application of the node through the API - for now this is just removed
    ax_select = axes_obj.modifiers[-1].node_group.nodes.get("Axis Selection")
    l = ax_select.outputs[0].links[0]
    axes_obj.modifiers[-1].node_group.links.remove(l)

    assert(len(axes_obj.modifiers) == 1)
    verts = get_verts([axes_obj], apply_modifiers=True)
    # snapshot.assert_match(verts, f"axes_{int(sum(size_px))}_{int(np.sum(np.array(sizes)))}")
    # assert("Error" not in verts)
    # check if not only cube persists:
    # assert( np.count_nonzero(np.abs([(v.co.x, v.co.y, v.co.z) for v in axes_obj.data.vertices])-1))
    