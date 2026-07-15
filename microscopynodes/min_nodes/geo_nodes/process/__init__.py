import bpy

from .nodeCustomConvolution import custom_convolution_node_group
from .nodeDifferenceOfBoxBlurs import difference_of_box_blurs_node_group
from .nodeEdgeBlobDetection import edge_blob_detection_node_group
from .nodeGradientMagnitude import gradient_magnitude_node_group
from .nodeSharpen import sharpen_node_group


NODE_GROUPS = {
    "Difference of Box Blurs": difference_of_box_blurs_node_group,
    "Sharpen": sharpen_node_group,
    "Gradient Magnitude": gradient_magnitude_node_group,
    "Edge/Blob Detection (LoBB)": edge_blob_detection_node_group,
    "Custom Convolution": custom_convolution_node_group,
}


class MIN_MT_PROCESS_ADD(bpy.types.Menu):
    bl_idname = "MIN_MT_PROCESS_ADD"
    bl_label = "Process"

    def draw(self, context):
        operator = self.layout.operator(
            "node.add_node",
            text="Box Blur",
        )
        operator.type = "GeometryNodeGridMean"
        operator.use_transform = True
        for node_name in NODE_GROUPS:
            operator = self.layout.operator(
                "microscopynodes.add_geometry_node_group",
                text=node_name,
            )
            operator.node_name = node_name


CLASSES = [MIN_MT_PROCESS_ADD]
