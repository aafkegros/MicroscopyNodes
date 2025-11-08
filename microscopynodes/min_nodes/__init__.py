from .nodeScale import scale_node_group
from .nodesBoolmultiplex import axes_multiplexer_node_group
from .nodeCrosshatch import crosshatch_node_group
from .nodeGridVerts import grid_verts_node_group
from .nodeScaleBox import scalebox_node_group
from .nodeSliceCube import slice_cube_node_group

from . import shader_nodes
from pathlib import Path

MIN_DATA_FILE = Path(__file__).resolve().parent / "min_nodes.blend"

CLASSES =shader_nodes.CLASSES