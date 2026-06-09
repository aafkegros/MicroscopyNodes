import bpy
from nodebpy import TreeBuilder, geometry as g
from nodebpy.builder import CustomGeometryGroup
from nodebpy.types import InputObject

GROUP_NAME = "Holder Bundle Inputs"

HOLDER_BUNDLE_ITEMS = (
    ("INT", "Frame"),
    ("VECTOR", "Dataset BBox Min"),
    ("VECTOR", "Dataset BBox Max"),
    ("VECTOR", "Dataset BBox Extents"),
    ("FLOAT", "Dataset Input Scale"),
    ("FLOAT", "Scene World Scale Base"),
    ("FLOAT", "Scene Output Scale"),
    ("VECTOR", "Scene Import Offset"),
    ("VECTOR", "Scene Import Transform"),
)


class HolderBundleInputs(CustomGeometryGroup):
    _name = GROUP_NAME

    def __init__(self, holder: InputObject = None):
        super().__init__(Holder=holder)

    def _build_group(self, tree):
        _build_holder_bundle_inputs(tree)


def _build_holder_bundle_inputs(tree):
    tree._arrange = "simple"

    tree.tree.show_modifier_manage_panel = True

    holder = tree.inputs.object("Holder")
    _new_bundle_outputs(tree)

    object_info = g.ObjectInfo(object=holder)
    bundle = g.GetGeometryBundle(geometry=object_info.o.geometry)
    separate = g.SeparateBundle(bundle=bundle.o.bundle, define_signature=True)

    for socket_type, name in HOLDER_BUNDLE_ITEMS:
        separate.node.bundle_items.new(socket_type, name)

    group_output = tree._output_node()
    for _, name in HOLDER_BUNDLE_ITEMS:
        tree.tree.links.new(separate.node.outputs[name], group_output.inputs[name])


def _new_bundle_outputs(tree):
    tree.outputs.integer("Frame")
    tree.outputs.vector("Dataset BBox Min")
    tree.outputs.vector("Dataset BBox Max")
    tree.outputs.vector("Dataset BBox Extents")
    tree.outputs.float("Dataset Input Scale")
    tree.outputs.float("Scene World Scale Base")
    tree.outputs.float("Scene Output Scale")
    tree.outputs.vector("Scene Import Offset")
    tree.outputs.vector("Scene Import Transform")


def holder_bundle_inputs_node_group():
    node_group = bpy.data.node_groups.get(GROUP_NAME)
    if node_group is not None:
        return node_group

    with TreeBuilder.geometry(GROUP_NAME, arrange="simple") as tree:
        _build_holder_bundle_inputs(tree)

    return tree.tree
