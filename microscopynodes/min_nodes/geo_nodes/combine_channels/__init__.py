import bpy

from .nodeIterateOverGrids import (
    IterateOverGrids,
    iterate_over_grids_node_group,
)
from .nodeIterateOverMeshes import (
    IterateOverMeshes,
    iterate_over_meshes_node_group,
)
from .nodeJoinMicroscopyGridsAndMeshes import (
    join_microscopy_grids_and_meshes_node_group,
)


NODE_GROUPS = {
    "Iterate Over Grids": iterate_over_grids_node_group,
    "Iterate Over Meshes": iterate_over_meshes_node_group,
    "Join Microscopy Grids and Meshes": join_microscopy_grids_and_meshes_node_group,
}


def draw_node_menu(self, context):
    for node_name in NODE_GROUPS:
        operator = self.layout.operator(
            "microscopynodes.add_geometry_node_group",
            text=node_name,
        )
        operator.node_name = node_name


class MIN_MT_COMBINE_CHANNELS_ADD(bpy.types.Menu):
    bl_idname = "MIN_MT_COMBINE_CHANNELS_ADD"
    bl_label = "Combine Channels"

    def draw(self, context):
        draw_node_menu(self, context)


CLASSES = [MIN_MT_COMBINE_CHANNELS_ADD]
