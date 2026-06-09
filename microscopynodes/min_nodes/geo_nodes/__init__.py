from .nodeCrosshatch import crosshatch_node_group
from .import_microscopy_meshes import import_microscopy_meshes_node_group
from .import_microscopy_volume import import_microscopy_volume_node_group
from .nodeMicroscopyGridToPoints import microscopy_grid_to_points_node_group
from .nodeHolderBundleInputs import holder_bundle_inputs_node_group
from .annotation import grid_verts_node_group, scale_node_group, scalebox_node_group
from . import annotation
from . import combine_channels
from . import masking
from . import ops
import bpy


ADD_MENU_NODE_GROUPS = [
    "Microscopy Grid to Points",
]


class MIN_MT_GEOMETRY_NODES_ADD(bpy.types.Menu):
    bl_idname = "MIN_MT_GEOMETRY_NODES_ADD"
    bl_label = "Microscopy Nodes"

    def draw(self, context):
        layout = self.layout
        layout.menu(
            "MIN_MT_COMBINE_CHANNELS_ADD",
            text="Combine Channels",
            icon="MOD_ARRAY",
        )
        layout.menu(
            "MIN_MT_MASKING_ADD",
            text="Masking",
            icon="MOD_MASK",
        )
        layout.menu(
            "MIN_MT_ANNOTATION_ADD",
            text="Annotation",
            icon="FONT_DATA",
        )
        layout.menu(
            "MIN_MT_CMAP_ADD",
            text="LUTs",
            icon="COLOR",
        )
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
        self.layout.menu(
            "MIN_MT_GEOMETRY_NODES_ADD",
            text="Microscopy Nodes",
            icon="VOLUME_DATA",
        )


NODE_GROUPS = {
    "crosshatch": crosshatch_node_group,
    "Import Microscopy Meshes": import_microscopy_meshes_node_group,
    "Import Microscopy Volume": import_microscopy_volume_node_group,
    "Microscopy Grid to Points": microscopy_grid_to_points_node_group,
    **annotation.NODE_GROUPS,
    **combine_channels.NODE_GROUPS,
    **masking.NODE_GROUPS,
}

CLASSES = [
    MIN_MT_GEOMETRY_NODES_ADD,
] + annotation.CLASSES + combine_channels.CLASSES + masking.CLASSES + ops.CLASSES


def geometry_node_group(name):
    builder = NODE_GROUPS.get(name)
    if builder is None:
        return None
    return builder()
