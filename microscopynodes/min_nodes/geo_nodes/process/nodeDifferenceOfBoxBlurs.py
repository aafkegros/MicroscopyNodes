import bpy
from nodebpy import TreeBuilder, geometry as g
from nodebpy.builder import CustomGeometryGroup
from nodebpy.types import InputFloat, InputInteger


GROUP_NAME = "Difference of Box Blurs"


class DifferenceOfBoxBlurs(CustomGeometryGroup):
    _name = GROUP_NAME

    def __init__(
        self,
        grid: InputFloat = 0.0,
        fine_width: InputInteger = 1,
        coarse_width: InputInteger = 3,
        iterations: InputInteger = 1,
    ):
        super().__init__(
            Grid=grid,
            **{
                "Fine Width": fine_width,
                "Coarse Width": coarse_width,
                "Iterations": iterations,
            },
        )

    def _build_group(self, tree):
        _build_difference_of_box_blurs(tree)


def _build_difference_of_box_blurs(tree):
    tree._arrange = "simple"
    tree.tree.description = (
        "Highlight structures between two spatial scales by subtracting box blurs"
    )

    grid = tree.inputs.float(
        "Grid",
        description="Float grid to filter",
        hide_value=True,
        structure_type="GRID",
    )
    fine_width = tree.inputs.integer(
        "Fine Width",
        default_value=1,
        description="Radius of the smaller box blur",
        min_value=1,
    )
    coarse_width = tree.inputs.integer(
        "Coarse Width",
        default_value=3,
        description="Radius of the larger box blur",
        min_value=1,
    )
    iterations = tree.inputs.integer(
        "Iterations",
        default_value=1,
        description="Number of blur passes at both scales",
        min_value=1,
    )
    output = tree.outputs.float(
        "Grid",
        description="Fine-scale blur minus coarse-scale blur",
        structure_type="GRID",
    )

    fine = g.GridMean.float(
        grid=grid,
        width=fine_width,
        iterations=iterations,
    ).o.grid
    coarse = g.GridMean.float(
        grid=grid,
        width=coarse_width,
        iterations=iterations,
    ).o.grid
    (fine - coarse) >> output


def difference_of_box_blurs_node_group():
    node_group = bpy.data.node_groups.get(GROUP_NAME)
    if node_group is not None:
        return node_group

    with TreeBuilder.geometry(GROUP_NAME, arrange="simple") as tree:
        _build_difference_of_box_blurs(tree)

    return tree.tree
