import bpy

from .nodeProjectGridToMesh import project_grid_to_mesh_node_group
from .nodeSampleGridOnMesh import sample_grid_on_mesh_node_group


NODE_GROUPS = {
    "Sample Grid on Mesh": sample_grid_on_mesh_node_group,
    "Project Grid to Mesh": project_grid_to_mesh_node_group,
}


class MIN_MT_PROJECT_ADD(bpy.types.Menu):
    bl_idname = "MIN_MT_PROJECT_ADD"
    bl_label = "Project"

    def draw(self, context):
        for node_name in NODE_GROUPS:
            operator = self.layout.operator(
                "microscopynodes.add_geometry_node_group",
                text=node_name,
            )
            operator.node_name = node_name


CLASSES = [MIN_MT_PROJECT_ADD]
