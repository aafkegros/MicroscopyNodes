import bpy
from nodebpy import TreeBuilder, geometry as g
from nodebpy.builder import CustomGeometryGroup
from nodebpy.types import InputFloat, InputMatrix


GROUP_NAME = "Custom Convolution"
OFFSETS = tuple(
    (x, y, z)
    for z in (-1, 0, 1)
    for y in (-1, 0, 1)
    for x in (-1, 0, 1)
)


class CustomConvolution(CustomGeometryGroup):
    _name = GROUP_NAME

    def __init__(
        self,
        grid: InputFloat = 0.0,
        kernel_z_minus_1: InputMatrix = None,
        kernel_z_0: InputMatrix = None,
        kernel_z_plus_1: InputMatrix = None,
    ):
        super().__init__(
            Grid=grid,
            **{
                "Kernel Z -1": kernel_z_minus_1,
                "Kernel Z 0": kernel_z_0,
                "Kernel Z +1": kernel_z_plus_1,
            },
        )

    def _build_group(self, tree):
        _build_custom_convolution(tree)


def convolve_grid(grid, weights):
    position = g.Position().o.position
    transform = g.GridInfo.float(grid=grid).o.transform
    value = 0.0
    for offset in OFFSETS:
        world_offset = g.TransformDirection(
            direction=offset,
            transform=transform,
        ).o.direction
        sample = g.SampleGrid.float(
            grid=grid,
            position=position + world_offset,
            interpolation="Nearest Neighbor",
        ).o.value
        value = value + sample * weights[offset]

    convolution = g.FieldToGrid.float(
        topology=grid,
        items={"Grid": value},
    )
    return convolution.node.outputs["Grid"]


def convolve_axis(grid, axis, weights):
    position = g.Position().o.position
    transform = g.GridInfo.float(grid=grid).o.transform
    value = 0.0
    for coordinate, weight in zip((-1, 0, 1), weights):
        offset = [0, 0, 0]
        offset[axis] = coordinate
        world_offset = g.TransformDirection(
            direction=tuple(offset),
            transform=transform,
        ).o.direction
        sample = g.SampleGrid.float(
            grid=grid,
            position=position + world_offset,
            interpolation="Nearest Neighbor",
        ).o.value
        value = value + sample * weight

    convolution = g.FieldToGrid.float(
        topology=grid,
        items={"Grid": value},
    )
    return convolution.node.outputs["Grid"]


def matrix_weights(matrix, z):
    separated = g.SeparateMatrix(matrix=matrix)
    return {
        (x, y, z): separated.node.outputs[
            f"Column {x + 2} Row {y + 2}"
        ]
        for y in (-1, 0, 1)
        for x in (-1, 0, 1)
    }


def _build_custom_convolution(tree):
    tree._arrange = "simple"
    tree.tree.description = (
        "Apply a custom 3 by 3 by 3 convolution kernel to a float grid"
    )

    grid = tree.inputs.float(
        "Grid",
        description="Float grid to convolve",
        hide_value=True,
        structure_type="GRID",
    )
    kernel_z_minus_1 = tree.inputs.matrix(
        "Kernel Z -1",
        description=(
            "Kernel weights for Z offset -1; only the upper-left 3 by 3 is used"
        ),
    )
    kernel_z_0 = tree.inputs.matrix(
        "Kernel Z 0",
        description=(
            "Kernel weights for Z offset 0; only the upper-left 3 by 3 is used"
        ),
    )
    kernel_z_plus_1 = tree.inputs.matrix(
        "Kernel Z +1",
        description=(
            "Kernel weights for Z offset +1; only the upper-left 3 by 3 is used"
        ),
    )
    output = tree.outputs.float(
        "Grid",
        description="Convolved float grid",
        structure_type="GRID",
    )

    weights = {
        **matrix_weights(kernel_z_minus_1, -1),
        **matrix_weights(kernel_z_0, 0),
        **matrix_weights(kernel_z_plus_1, 1),
    }
    tree.tree.links.new(convolve_grid(grid, weights), output.socket)


def custom_convolution_node_group():
    node_group = bpy.data.node_groups.get(GROUP_NAME)
    if node_group is not None:
        return node_group

    with TreeBuilder.geometry(GROUP_NAME, arrange="simple") as tree:
        _build_custom_convolution(tree)

    return tree.tree
