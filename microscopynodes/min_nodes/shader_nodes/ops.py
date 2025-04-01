import bpy
from bpy.types import Context, Operator
from .handle_cmap import get_lut, set_color_ramp
from bpy.props import (StringProperty, FloatProperty,
                        PointerProperty, IntProperty,
                        BoolProperty, EnumProperty
                        )
# from .nodeCmap import cmap_node
class MIN_OT_Replace_LUT_Node_Group(Operator):
    """Replace LUT of color ramp"""
    bl_idname = "microscopynodes.replace_lut"
    bl_label = "Replace Lookup Table of Color Ramp node"

    bl_options = {"REGISTER", "UNDO"}
    cmap_name: StringProperty(  # type: ignore
        name="cmap", description="", default="", subtype="NONE", maxlen=0
    )
    description: StringProperty(name="Description")


    def execute(self, context):
        try:
            lut, linear = get_lut(self.cmap_name, (1,1,1))
            set_color_ramp(context.selected_nodes[0], lut, linear, self.cmap_name)
        except RuntimeError:
            self.report(
                {"ERROR"},
                message="Failed to replace lut. ",
            )
            return {"CANCELLED"}
        return {"FINISHED"}

class MIN_OT_Add_LUT_Node_Group(Operator):
    """Add color ramp with LUT"""
    bl_idname = "microscopynodes.add_lut"
    bl_label = "Add Color Ramp with LUT Node"

    bl_options = {"REGISTER", "UNDO"}
    cmap_name: StringProperty(  # type: ignore
        name="cmap", description="", default="", subtype="NONE", maxlen=0
    )
    description: StringProperty(name="Description")

    @classmethod
    def description(cls, context, properties):
        return properties.node_description

    def execute(self, context):
        try:
            # nodes.append(self.node_name, link=self.node_link)
            _add_cmap(self.cmap_name, context)  # , label=self.node_label)
        except RuntimeError:
            self.report(
                {"ERROR"},
                message="Failed to add node. Ensure you are not in edit mode.",
            )
            return {"CANCELLED"}
        return {"FINISHED"}


class MIN_OT_Reverse_LUT_Node_Group(Operator):
    """Reverse positions of LUT (duplicate of the arrow menu next to the ramp)"""
    bl_idname = "microscopynodes.reverse_lut"
    bl_label = "Reverse order of color ramp positions"

    bl_options = {"REGISTER", "UNDO"}
    cmap_name: StringProperty(  # type: ignore
        name="cmap", description="", default="", subtype="NONE", maxlen=0
    )

    def execute(self, context):
        try:
            color_ramp = context.selected_nodes[0].color_ramp
            left, right = 0, len(color_ramp.elements) - 1
            elements = [(float(el.position), list(el.color)) for el in color_ramp.elements]
            for stop in range(len(color_ramp.elements) -1):
                color_ramp.elements.remove(color_ramp.elements[0] )
            for ix, el in enumerate(elements):
                if len(color_ramp.elements) <= ix:
                    color_ramp.elements.new(0.01)
                color_ramp.elements[0].color = el[1]
                color_ramp.elements[0].position = abs(1 - el[0])
        except RuntimeError:
            self.report(
                {"ERROR"},
                message="Failed to reverse LUT, use the menu on the node itself!",
            )
            return {"CANCELLED"}
        return {"FINISHED"}



def _add_cmap(cmap_name, context, show_options=False, material="default"):
    """
    Add a node group to the node tree and set the values.

    intended to be called upon button press in the node tree, and not for use in general scripting
    """

    # actually invoke the operator to add a node to the current node tree
    # use_transform=True ensures it appears where the user's mouse is and is currently
    # being moved so the user can place it where they wish
    bpy.ops.node.add_node(
        "INVOKE_DEFAULT", type="ShaderNodeValToRGB", use_transform=True
    )
    node = context.active_node
    node.outputs[1].hide = True
    lut, linear = get_lut(cmap_name, (1,1,1))
    set_color_ramp(node, lut, linear, cmap_name)
    node.width = 300


CLASSES = [MIN_OT_Add_LUT_Node_Group, MIN_OT_Replace_LUT_Node_Group, MIN_OT_Reverse_LUT_Node_Group]