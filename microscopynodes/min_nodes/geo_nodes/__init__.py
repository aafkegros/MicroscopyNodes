from .nodeCrosshatch import crosshatch_node_group
from .nodeGridVerts import grid_verts_node_group
from .import_microscopy_meshes import import_microscopy_meshes_node_group
from .import_microscopy_volume import import_microscopy_volume_node_group
from .join_grids import join_grids_node_group
from .nodeScale import scale_node_group
from .nodeScaleBox import scalebox_node_group


NODE_GROUPS = {
    "crosshatch": crosshatch_node_group,
    "Import Microscopy Meshes": import_microscopy_meshes_node_group,
    "Import Microscopy Volume": import_microscopy_volume_node_group,
    "Join Grids": join_grids_node_group,
    "Scale bars": scale_node_group,
    "_grid_verts": grid_verts_node_group,
    "_scalebox": scalebox_node_group,
}


def geometry_node_group(name):
    builder = NODE_GROUPS.get(name)
    if builder is None:
        return None
    return builder()
