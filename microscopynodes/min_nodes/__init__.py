print('importing min_nodes')
from .nodeScale import scale_node_group
from .nodesBoolmultiplex import axes_multiplexer_node_group
from .nodeCrosshatch import crosshatch_node_group
from .nodeGridVerts import grid_verts_node_group
from .nodeScaleBox import scalebox_node_group
from .nodeBoundedMapRange import bounded_map_range_node_group
from .nodeSliceCube import slice_cube_node_group

from . import shader_nodes
from .shader_nodes import MIN_add_shader_node_menu


CLASSES =shader_nodes.CLASSES