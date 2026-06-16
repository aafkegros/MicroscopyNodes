import bpy
from nodebpy import TreeBuilder, geometry as g
from nodebpy.builder import CustomGeometryGroup
from nodebpy.types import InputFloat, InputInteger


GROUP_NAME = "Box Blur"


class BoxBlur(CustomGeometryGroup):
    _name = GROUP_NAME

    def __init__(
        self,
        grid: InputFloat = 0.0,
        width: InputInteger = 1,
        iterations: InputInteger = 1,
    ):
        super().__init__(Grid=grid, Width=width, Iterations=iterations)

    def _build_group(self, tree):
        _build_box_blur(tree)


def _build_box_blur(tree):
    tree._arrange = "simple"
    tree.tree.description = "Smooth a float grid with a box-shaped mean filter"

    grid = tree.inputs.float(
        "Grid",
        description="Float grid to blur",
        hide_value=True,
        structure_type="GRID",
    )
    width = tree.inputs.integer(
        "Width",
        default_value=1,
        description="Filter radius in voxels",
        min_value=1,
    )
    iterations = tree.inputs.integer(
        "Iterations",
        default_value=1,
        description="Number of times the blur is applied",
        min_value=1,
    )
    output = tree.outputs.float(
        "Grid",
        description="Blurred float grid",
        structure_type="GRID",
    )

    g.GridMean.float(
        grid=grid,
        width=width,
        iterations=iterations,
    ).o.grid >> output


def box_blur_node_group():
    node_group = bpy.data.node_groups.get(GROUP_NAME)
    if node_group is not None:
        return node_group

    with TreeBuilder.geometry(GROUP_NAME, arrange="simple") as tree:
        _build_box_blur(tree)

    return tree.tree
