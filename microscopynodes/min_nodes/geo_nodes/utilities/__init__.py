import bpy

from .import_microscopy_meshes import import_microscopy_meshes_node_group
from .import_microscopy_volume import import_microscopy_volume_node_group
from .nodeActiveGridPositions import active_grid_positions_node_group
from .nodeExplodeInstances import explode_instances_node_group
from .nodeMicroscopyGridToPoints import microscopy_grid_to_points_node_group


NODE_GROUPS = {
    "Import Microscopy Meshes": import_microscopy_meshes_node_group,
    "Import Microscopy Volume": import_microscopy_volume_node_group,
    "Active Grid Positions": active_grid_positions_node_group,
    "Explode Instances": explode_instances_node_group,
    "Microscopy Grid to Points": microscopy_grid_to_points_node_group,
}

ADD_MENU_NODE_GROUPS = [
    "Import Microscopy Meshes",
    "Import Microscopy Volume",
    "Active Grid Positions",
    "Explode Instances",
]


class MIN_MT_UTILITIES_ADD(bpy.types.Menu):
    bl_idname = "MIN_MT_UTILITIES_ADD"
    bl_label = "Utilities"

    def draw(self, context):
        for node_name in ADD_MENU_NODE_GROUPS:
            operator = self.layout.operator(
                "microscopynodes.add_geometry_node_group",
                text=node_name,
            )
            operator.node_name = node_name


CLASSES = [MIN_MT_UTILITIES_ADD]
