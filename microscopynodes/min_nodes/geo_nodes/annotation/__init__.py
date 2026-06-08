import bpy

from .nodeGridVerts import grid_verts_node_group
from .nodeScale import scale_node_group
from .nodeScaleBox import scalebox_node_group


NODE_GROUPS = {
    "Scale Grid": scale_node_group,
    "_grid_verts": grid_verts_node_group,
    "_scalebox": scalebox_node_group,
}


ADD_MENU_NODE_GROUPS = [
    "Scale Grid",
]


def draw_node_menu(self, context):
    for node_name in ADD_MENU_NODE_GROUPS:
        operator = self.layout.operator(
            "microscopynodes.add_geometry_node_group",
            text=node_name,
        )
        operator.node_name = node_name


class MIN_MT_ANNOTATION_ADD(bpy.types.Menu):
    bl_idname = "MIN_MT_ANNOTATION_ADD"
    bl_label = "Annotation"

    def draw(self, context):
        draw_node_menu(self, context)


CLASSES = [MIN_MT_ANNOTATION_ADD]
