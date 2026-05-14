from .nodeCrosshatch import crosshatch_node_group
from .nodeGridVerts import grid_verts_node_group
from .import_microscopy_meshes import import_microscopy_meshes_node_group
from .import_microscopy_volume import import_microscopy_volume_node_group
from .join_grids import join_grids_node_group
from .nodeMaskGrid import mask_grid_node_group
from .nodeMaskMesh import mask_mesh_node_group
from .nodeScale import scale_node_group
from .nodeScaleBox import scalebox_node_group
from . import ops
import bpy


ADD_MENU_NODE_GROUPS = [
    "Mask Grid",
    "Mask Mesh",
]


class MIN_MT_GEOMETRY_NODES_ADD(bpy.types.Menu):
    bl_idname = "MIN_MT_GEOMETRY_NODES_ADD"
    bl_label = "Microscopy Nodes"

    def draw(self, context):
        layout = self.layout
        for node_name in ADD_MENU_NODE_GROUPS:
            operator = layout.operator(
                "microscopynodes.add_geometry_node_group",
                text=node_name,
            )
            operator.node_name = node_name


def MIN_add_geometry_node_menu(self, context):
    area = getattr(context, "area", None)
    space = getattr(context, "space_data", None)
    area_ui_type = getattr(area, "ui_type", None)
    tree_type = getattr(space, "tree_type", None)

    if area_ui_type == "GeometryNodeTree" or tree_type == "GeometryNodeTree":
        self.layout.menu("MIN_MT_GEOMETRY_NODES_ADD", text="Microscopy Nodes")


NODE_GROUPS = {
    "crosshatch": crosshatch_node_group,
    "Import Microscopy Meshes": import_microscopy_meshes_node_group,
    "Import Microscopy Volume": import_microscopy_volume_node_group,
    "Join Grids": join_grids_node_group,
    "Mask Grid": mask_grid_node_group,
    "Mask Mesh": mask_mesh_node_group,
    "Scale bars": scale_node_group,
    "_grid_verts": grid_verts_node_group,
    "_scalebox": scalebox_node_group,
}

CLASSES = [MIN_MT_GEOMETRY_NODES_ADD] + ops.CLASSES


def geometry_node_group(name):
    builder = NODE_GROUPS.get(name)
    if builder is None:
        return None
    return builder()
