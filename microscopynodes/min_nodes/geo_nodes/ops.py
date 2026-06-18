import bpy
from bpy.props import StringProperty
from bpy.types import Operator


def _object_parent_holder(context):
    from ...handle_blender_structs.dependent_props import poll_holder

    obj = getattr(context, "object", None) or getattr(
        context.view_layer.objects, "active", None
    )
    parent = getattr(obj, "parent", None)
    if parent is not None and poll_holder(context.scene, parent):
        return parent
    return None


def _set_holder_input(context, holder_input):
    parent_holder = _object_parent_holder(context)
    if parent_holder is not None:
        holder_input.default_value = parent_holder
        holder_input.hide = True
        return

    if context.scene.MiN_reload is not None:
        holder_input.default_value = context.scene.MiN_reload


class MIN_OT_Add_Geometry_Node_Group(Operator):
    """Add Microscopy Nodes geometry node group."""

    bl_idname = "microscopynodes.add_geometry_node_group"
    bl_label = "Add Microscopy Nodes Geometry Node"
    bl_options = {"REGISTER", "UNDO"}

    node_name: StringProperty(name="Node", default="", subtype="NONE")  # type: ignore

    def execute(self, context):
        from . import geometry_node_group

        node_group = geometry_node_group(self.node_name)
        if node_group is None:
            self.report({"ERROR"}, message=f"Unknown Microscopy Nodes group: {self.node_name}")
            return {"CANCELLED"}

        try:
            bpy.ops.node.add_node(
                "INVOKE_DEFAULT", type="GeometryNodeGroup", use_transform=True
            )
            node = context.active_node
            if node is None:
                raise RuntimeError("No active node created")
            node.node_tree = node_group
            holder_input = node.inputs.get("Holder")
            if holder_input is not None:
                _set_holder_input(context, holder_input)
            if node_group.name == "Mask Grid":
                node.width = node_group.default_group_node_width
            node.show_options = False
            node.name = node_group.name
        except (AttributeError, RuntimeError, TypeError):
            self.report(
                {"ERROR"},
                message="Failed to add node. Ensure you are in a geometry node tree.",
            )
            return {"CANCELLED"}

        return {"FINISHED"}


CLASSES = [MIN_OT_Add_Geometry_Node_Group]
