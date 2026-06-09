import bpy
from nodebpy import TreeBuilder, geometry as g
from nodebpy.builder import CustomGeometryGroup
from nodebpy.types import InputFloat, InputInteger, InputMenu, InputObject

from ..nodeHolderBundleInputs import HolderBundleInputs


GROUP_NAME = "Time Annotation"

TIME_UNITS = ("frame", "ns", "µs", "ms", "s", "min", "hour", "day", "month")
SECONDS_PER_UNIT = (1.0, 1e-9, 1e-6, 0.001, 1.0, 60.0, 3600.0, 86400.0, 2629800.0)


class TimeAnnotation(CustomGeometryGroup):
    _name = GROUP_NAME

    def __init__(
        self,
        holder: InputObject = None,
        frame_period: InputFloat = 1.0,
        input_unit: InputMenu = "frame",
        output_unit: InputMenu = "frame",
        decimals: InputInteger = 0,
        size: InputFloat = 1.0,
    ):
        super().__init__(
            Holder=holder,
            **{
                "Frame Period": frame_period,
                "Input Unit": input_unit,
                "Output Unit": output_unit,
            },
            Decimals=decimals,
            Size=size,
        )

    def _build_group(self, tree):
        _build_time_annotation(tree)


def _build_time_annotation(tree):
    tree._arrange = "simple"

    holder = tree.inputs.object("Holder")
    frame_period = tree.inputs.float(
        "Frame Period",
        default_value=1.0,
        min_value=0.0,
    )
    input_unit = tree.inputs.menu(
        "Input Unit",
        default_value="frame",
        optional_label=True,
    )
    output_unit = tree.inputs.menu(
        "Output Unit",
        default_value="frame",
        optional_label=True,
    )
    decimals = tree.inputs.integer("Decimals", default_value=0, min_value=0)
    size = tree.inputs.float("Size", default_value=1.0, min_value=0.0)
    mesh = tree.outputs.geometry("Mesh")

    holder_inputs = HolderBundleInputs(holder=holder)
    for output in holder_inputs.node.outputs:
        if output.name != "Frame":
            output.hide = True

    unit_indices = {name: index for index, name in enumerate(TIME_UNITS)}
    input_unit_index = g.MenuSwitch.integer(
        menu=input_unit,
        items=unit_indices,
    ).o.output
    output_unit_index = g.MenuSwitch.integer(
        menu=output_unit,
        items=unit_indices,
    ).o.output

    input_unit_scale = g.IndexSwitch.float(
        index=input_unit_index,
        items=SECONDS_PER_UNIT,
    ).o.output
    frame_period_seconds = frame_period * input_unit_scale
    output_unit_scale = g.IndexSwitch.float(
        index=output_unit_index,
        items=(frame_period_seconds, *SECONDS_PER_UNIT[1:]),
    ).o.output
    output_unit_label = g.IndexSwitch.string(
        index=output_unit_index,
        items=TIME_UNITS,
    ).o.output

    converted_frame = holder_inputs.o.frame * frame_period_seconds / output_unit_scale
    value = g.ValueToString(
        value=converted_frame,
        decimals=decimals,
    ).o.string
    text = g.JoinStrings(strings=(value, output_unit_label), delimiter=" ").o.string
    curves = g.StringToCurves(string=text, size=size).o.curve_instances
    g.FillCurve(curve=curves).o.mesh >> mesh
    tree.arrange()


def time_annotation_node_group():
    node_group = bpy.data.node_groups.get(GROUP_NAME)
    if node_group is not None:
        return node_group

    with TreeBuilder.geometry(GROUP_NAME, arrange="simple") as tree:
        _build_time_annotation(tree)

    return tree.tree
