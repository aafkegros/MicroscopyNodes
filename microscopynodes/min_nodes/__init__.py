from .geo_nodes import (
    crosshatch_node_group,
    grid_verts_node_group,
    scale_node_group,
    scalebox_node_group,
)
from .shader_nodes import slice_cube_node_group
from .geo_nodes import geometry_node_group

from . import shader_nodes
from . import geo_nodes

CLASSES = shader_nodes.CLASSES + geo_nodes.CLASSES


def node_group(name):
    group = geometry_node_group(name)
    if group is not None:
        return group
    return shader_nodes.shader_node_group(name)
