import bpy

from .nodeMaskGrid import mask_grid_node_group
from .nodeMaskMesh import mask_mesh_node_group


NODE_GROUPS = {
    "Mask Grid": mask_grid_node_group,
    "Mask Mesh": mask_mesh_node_group,
}


def draw_node_menu(self, context):
    for node_name in NODE_GROUPS:
        operator = self.layout.operator(
            "microscopynodes.add_geometry_node_group",
            text=node_name,
        )
        operator.node_name = node_name


class MIN_MT_MASKING_ADD(bpy.types.Menu):
    bl_idname = "MIN_MT_MASKING_ADD"
    bl_label = "Masking"

    def draw(self, context):
        draw_node_menu(self, context)


CLASSES = [MIN_MT_MASKING_ADD]
