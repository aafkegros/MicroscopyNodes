import bpy
from bpy.types import Context, Operator

from bpy.props import (StringProperty, FloatProperty,
                        PointerProperty, IntProperty,
                        BoolProperty, EnumProperty
                        )
# from .nodeCmap import cmap_node

# adapted from Molecular Nodes
class MIN_OT_Add_Cmap_Node_Group(Operator):
    bl_idname = "microscopynodes.add_lut"
    bl_label = "Add Shader Node Group"

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



def _add_cmap(cmap_name, context, show_options=False, material="default"):
    """
    Add a node group to the node tree and set the values.

    intended to be called upon button press in the node tree, and not for use in general scripting
    """

    # actually invoke the operator to add a node to the current node tree
    # use_transform=True ensures it appears where the user's mouse is and is currently
    # being moved so the user can place it where they wish
    bpy.ops.node.add_node(
        "INVOKE_DEFAULT", type="ShaderNodeGroup", use_transform=True
    )
    node = context.active_node
    # node.node_tree = cmap_node(cmap_name)
    node.width = 200
    node.show_options = show_options
    node.label = f"Apply {cmap_name.capitalize()}  LUT"
    node.name = cmap_name


CLASSES = [MIN_OT_Add_Cmap_Node_Group]