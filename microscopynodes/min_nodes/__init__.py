from .nodeScale import scale_node_group
from .nodeCrosshatch import crosshatch_node_group
from .nodeGridVerts import grid_verts_node_group
from .nodeScaleBox import scalebox_node_group
from .nodeSliceCube import slice_cube_node_group
from .geo_nodes import geometry_node_group

from . import shader_nodes

CLASSES =shader_nodes.CLASSES


def node_group(name):
    group = geometry_node_group(name)
    if group is not None:
        return group
    return shader_nodes.shader_node_group(name)
