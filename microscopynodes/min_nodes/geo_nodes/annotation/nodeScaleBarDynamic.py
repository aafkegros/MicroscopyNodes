import bpy
from nodebpy import TreeBuilder, geometry as g
from nodebpy.builder import CustomGeometryGroup
from nodebpy.types import InputObject

from .nodeScaleBarRigid import ScaleBarRigid
from ..nodeHolderBundleInputs import HolderBundleInputs


GROUP_NAME = "Scale Bar (dynamic)"

UNIT_EXPONENTS = (-10.0, -9.0, -9.0, -9.0, -6.0, -6.0, -6.0, -3.0, -2.0, -1.0, 0.0)
UNIT_NAMES = ("Å", "nm", "nm", "nm", "µm", "µm", "µm", "mm", "cm", "dm", "m")


class ScaleBarDynamic(CustomGeometryGroup):
    _name = GROUP_NAME

    def __init__(self, holder: InputObject = None):
        super().__init__(Holder=holder)

    def _build_group(self, tree):
        _build_scale_bar_dynamic(tree)


def _build_scale_bar_dynamic(tree):
    holder = tree.inputs.object("Holder")
    mesh = tree.outputs.geometry("Mesh")

    holder_inputs = HolderBundleInputs(holder=holder)
    for output in holder_inputs.node.outputs:
        if output.name != "Scene Output Scale":
            output.hide = True

    self_scale = g.ObjectInfo(
        object=g.SelfObject().o.self_object,
    ).o.scale
    object_scale = g.SeparateXYZ(vector=self_scale)
    scale_x = object_scale.o.x
    physical_width = holder_inputs.o.scene_output_scale * scale_x
    physical_exponent = g.Math(
        value=physical_width,
        value_001=10.0,
        operation="LOGARITHM",
    ).o.value
    unit_index = g.Math(
        value=physical_exponent,
        operation="FLOOR",
    ).o.value + 10.0
    unit_index = g.Math(
        value=g.Math(
            value=unit_index,
            value_001=0.0,
            operation="MAXIMUM",
        ).o.value,
        value_001=10.0,
        operation="MINIMUM",
    ).o.value

    unit_exponent = g.IndexSwitch.float(
        index=unit_index,
        items=UNIT_EXPONENTS,
    ).o.output
    length = g.Math(
        value=10.0,
        value_001=physical_exponent - unit_exponent,
        operation="POWER",
    ).o.value

    rigid = ScaleBarRigid(
        holder=holder,
        length=length,
        size=object_scale.o.y,
        decimals=1,
    )
    unit_switch = g.IndexSwitch.menu(index=unit_index)
    for _ in UNIT_NAMES:
        unit_switch.node.index_switch_items.new()
    tree.tree.links.new(unit_switch.node.outputs["Output"], rigid.node.inputs["Unit"])
    for socket, unit_name in zip(unit_switch.node.inputs[1:], UNIT_NAMES):
        socket.default_value = unit_name

    rigid.o.mesh >> mesh


def scale_bar_dynamic_node_group():
    node_group = bpy.data.node_groups.get(GROUP_NAME)
    if node_group is not None:
        return node_group

    with TreeBuilder.geometry(GROUP_NAME) as tree:
        _build_scale_bar_dynamic(tree)

    return tree.tree
