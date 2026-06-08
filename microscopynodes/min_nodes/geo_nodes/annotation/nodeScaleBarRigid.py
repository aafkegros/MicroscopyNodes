import bpy
from nodebpy import TreeBuilder, geometry as g
from nodebpy.builder import CustomGeometryGroup
from nodebpy.types import InputFloat, InputInteger, InputMenu, InputObject

from ..nodeHolderBundleInputs import HolderBundleInputs


GROUP_NAME = "Scale Bar (Rigid)"

UNIT_NAMES = ("Å", "nm", "µm", "mm", "cm", "dm", "m")
UNIT_SCALES = (1e-10, 1e-9, 1e-6, 1e-3, 1e-2, 1e-1, 1.0)


class ScaleBarRigid(CustomGeometryGroup):
    _name = GROUP_NAME

    def __init__(
        self,
        object: InputObject = None,
        unit: InputMenu = None,
        length: InputFloat = 0.0,
        size: InputFloat = 0.0,
        decimals: InputInteger = 0,
    ):
        super().__init__(
            Object=object,
            Unit=unit,
            Length=length,
            Size=size,
            Decimals=decimals,
        )

    def _build_group(self, tree):
        _build_scale_bar_rigid(tree)


def _build_scale_bar_rigid(tree):
    holder = tree.inputs.object("Holder")
    unit = tree.inputs.menu("Unit", default_value="µm", optional_label=True)
    length = tree.inputs.float("Length", 1)
    size = tree.inputs.float("Size", 1)
    decimals = tree.inputs.integer("Decimals", 0, min_value=0)
    mesh = tree.outputs.geometry("Mesh")

    holder_inputs = HolderBundleInputs(holder=holder)
    for output in holder_inputs.node.outputs:
        if output.name != "Scene Output Scale":
            output.hide = True

    unit_index = g.MenuSwitch.integer(
        menu=unit,
        items={
            "Å": 0,
            "nm": 1,
            "µm": 2,
            "mm": 3,
            "cm": 4,
            "dm": 5,
            "m": 6,
            "Scene Unit": 0,
        },
    ).o.output
    unit_scale = g.IndexSwitch.float(
        index=unit_index,
        items=UNIT_SCALES,
    ).o.output
    unit_label = g.IndexSwitch.string(
        index=unit_index,
        items=UNIT_NAMES,
    ).o.output

    scene_length = g.Math(
        value=unit_scale,
        value_001=holder_inputs.o.scene_output_scale,
        operation="DIVIDE",
    ).o.value * length
    bar_size = g.CombineXYZ(x=scene_length, y=size, z=0.0).o.vector
    bar_offset = g.VectorMath(
        vector=bar_size,
        vector_001=(2.0, 2.0, 1.0),
        operation="DIVIDE",
    ).o.vector
    bar = g.SetPosition(
        geometry=g.Cube(size=bar_size).o.mesh,
        offset=bar_offset,
    ).o.geometry

    value = g.ValueToString(value=length, decimals=decimals).o.string
    label = g.JoinStrings(strings=(value, unit_label), delimiter=" ").o.string
    text_size = size * 10.0
    text = g.FillCurve(
        curve=g.StringToCurves(string=label, size=text_size).o.curve_instances,
    ).o.mesh
    text = g.SetPosition(
        geometry=text,
        offset=g.CombineXYZ(y=text_size / 3.0).o.vector,
    ).o.geometry

    geometry = g.JoinGeometry(geometry=(bar, text)).o.geometry
    object_scale = g.ObjectInfo(
        object=g.SelfObject().o.self_object,
    ).o.scale
    inverse_scale = g.VectorMath(
        vector=(1.0, 1.0, 1.0),
        vector_001=object_scale,
        operation="DIVIDE",
    ).o.vector
    camera_info = g.CameraInfo(
        camera=g.ActiveCamera().o.active_camera,
    )
    g.Warning.warning(
        show=g.BooleanMath.l_not(camera_info.o.is_orthographic).o.boolean,
        message="The Active Camera is not Orthographic. This may make the scale bar inaccurate. Consider using the Scale Grid instead.",
    )
    g.TransformGeometry(
        geometry=geometry,
        scale=inverse_scale,
    ).o.geometry >> mesh


def scale_bar_rigid_node_group():
    node_group = bpy.data.node_groups.get(GROUP_NAME)
    if node_group is not None:
        return node_group

    with TreeBuilder.geometry(GROUP_NAME) as tree:
        _build_scale_bar_rigid(tree)

    return tree.tree
