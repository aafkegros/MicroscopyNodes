import bpy
from nodebpy import TreeBuilder, geometry as g
from nodebpy.builder import CustomGeometryGroup
from nodebpy.types import InputFloat


GROUP_NAME = "Gradient Magnitude"


class GradientMagnitude(CustomGeometryGroup):
    _name = GROUP_NAME

    def __init__(self, grid: InputFloat = 0.0):
        super().__init__(Grid=grid)

    def _build_group(self, tree):
        _build_gradient_magnitude(tree)


def _build_gradient_magnitude(tree):
    tree._arrange = "simple"
    tree.tree.description = "Measure local edge strength from the grid gradient"

    grid = tree.inputs.float(
        "Grid",
        description="Float grid in which to measure edge strength",
        hide_value=True,
        structure_type="GRID",
    )
    output = tree.outputs.float(
        "Grid",
        description="Magnitude of the grid gradient",
        structure_type="GRID",
    )

    gradient = g.GridGradient(grid=grid).o.gradient
    g.VectorMath.length(vector=gradient).o.value >> output


def gradient_magnitude_node_group():
    node_group = bpy.data.node_groups.get(GROUP_NAME)
    if node_group is not None:
        return node_group

    with TreeBuilder.geometry(GROUP_NAME, arrange="simple") as tree:
        _build_gradient_magnitude(tree)

    return tree.tree
