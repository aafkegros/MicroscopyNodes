import bpy
from nodebpy import TreeBuilder, geometry as g
from nodebpy.builder import CustomGeometryGroup
from nodebpy.types import InputFloat, InputInteger, InputObject, InputString

from ..nodeHolderBundleInputs import HolderBundleInputs


GROUP_NAME = "Time Annotation"


class TimeAnnotation(CustomGeometryGroup):
    _name = GROUP_NAME

    def __init__(
        self,
        holder: InputObject = None,
        unit: InputString = "frames",
        conversion_factor: InputFloat = 1.0,
        decimals: InputInteger = 0,
        size: InputFloat = 1.0,
    ):
        super().__init__(
            Holder=holder,
            Unit=unit,
            **{"Conversion Factor": conversion_factor},
            Decimals=decimals,
            Size=size,
        )

    def _build_group(self, tree):
        _build_time_annotation(tree)


def _build_time_annotation(tree):
    holder = tree.inputs.object("Holder")
    unit = tree.inputs.string("Unit", default_value="frames")
    conversion_factor = tree.inputs.float(
        "Conversion Factor",
        default_value=1.0,
    )
    decimals = tree.inputs.integer("Decimals", default_value=0, min_value=0)
    size = tree.inputs.float("Size", default_value=1.0, min_value=0.0)
    mesh = tree.outputs.geometry("Mesh")

    holder_inputs = HolderBundleInputs(holder=holder)
    for output in holder_inputs.node.outputs:
        if output.name != "Frame":
            output.hide = True

    converted_frame = holder_inputs.o.frame * conversion_factor
    value = g.ValueToString(
        value=converted_frame,
        decimals=decimals,
    ).o.string
    text = g.JoinStrings(strings=(value, unit), delimiter=" ").o.string
    curves = g.StringToCurves(string=text, size=size).o.curve_instances
    g.FillCurve(curve=curves).o.mesh >> mesh


def time_annotation_node_group():
    node_group = bpy.data.node_groups.get(GROUP_NAME)
    if node_group is not None:
        return node_group

    with TreeBuilder.geometry(GROUP_NAME) as tree:
        _build_time_annotation(tree)

    return tree.tree
