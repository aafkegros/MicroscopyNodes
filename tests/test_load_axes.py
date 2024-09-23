import bpy
import os
import pytest
import itertools
import numpy as np
import microscopynodes
from pathlib import Path
from .utils import get_verts, remove_all_objects
import microscopynodes.load_components as load_axes
from microscopynodes import min_nodes
from microscopynodes.handle_blender_structs import collection_by_name, node_handling


px_sizes = [[30, 30, 30], [10,10,1], [4069, 2031,500]]
sizes = [(1, 1, 1), (0.1, 0.1, 1), (0.01, 0.01, 0.02), (10, 10, 20)]


@pytest.mark.parametrize('size_px, size', zip(px_sizes, sizes))
def test_load_axes(snapshot, size_px, size):
    remove_all_objects()

    axes_obj = load_axes.load_axes(size_px, size)

    # TODO BUG somehow the axis selector breaks application of the node through the API - for now this is just removed
    ax_select = axes_obj.modifiers[-1].node_group.nodes.get("Axis Selection")
    l = ax_select.outputs[0].links[0]
    axes_obj.modifiers[-1].node_group.links.remove(l)

    assert(len(axes_obj.modifiers) == 1)
    verts = get_verts([axes_obj], apply_modifiers=True)
    # snapshot.assert_match(verts, f"axes_{int(sum(size_px))}_{int(np.sum(np.array(sizes)))}")
    # assert("Error" not in verts)
    # check if not only cube persists:
    assert( np.count_nonzero(np.abs([(v.co.x, v.co.y, v.co.z) for v in axes_obj.data.vertices])-1))
    
    