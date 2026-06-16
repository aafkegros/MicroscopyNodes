import bpy

from .nodeMeshRegionprops import mesh_regionprops_node_group
from .nodeProjectGridToMesh import project_grid_to_mesh_node_group
from .nodeSampleGridOnMesh import sample_grid_on_mesh_node_group


NODE_GROUPS = {
    "Sample Grid on Mesh": sample_grid_on_mesh_node_group,
    "Project Grid to Mesh": project_grid_to_mesh_node_group,
    "Mesh Regionprops": mesh_regionprops_node_group,
}


class MIN_MT_MEASURE_ADD(bpy.types.Menu):
    bl_idname = "MIN_MT_MEASURE_ADD"
    bl_label = "Measure"

    def draw(self, context):
        for node_name in NODE_GROUPS:
            operator = self.layout.operator(
                "microscopynodes.add_geometry_node_group",
                text=node_name,
            )
            operator.node_name = node_name
        operator = self.layout.operator(
            "node.add_node",
            text="Attribute Statistic",
        )
        operator.type = "GeometryNodeAttributeStatistic"
        operator.use_transform = True


CLASSES = [MIN_MT_MEASURE_ADD]
