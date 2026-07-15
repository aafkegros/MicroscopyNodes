import bpy
from nodebpy import TreeBuilder, geometry as g
from nodebpy.builder import CustomGeometryGroup
from nodebpy.types import InputFloat, InputInteger, InputMenu


GROUP_NAME = "Sharpen"


class Sharpen(CustomGeometryGroup):
    _name = GROUP_NAME

    def __init__(
        self,
        grid: InputFloat = 0.0,
        mode: InputMenu = "LoBB",
        strength: InputFloat = 1.0,
        width: InputInteger = 1,
        iterations: InputInteger = 1,
    ):
        super().__init__(
            Grid=grid,
            Mode=mode,
            Strength=strength,
            Width=width,
            Iterations=iterations,
        )

    def _build_group(self, tree):
        _build_sharpen(tree)


def _build_sharpen(tree):
    tree._arrange = "simple"
    tree.tree.description = "Sharpen a float grid using LoBB or an unsharp mask"

    grid = tree.inputs.float(
        "Grid",
        description="Float grid to sharpen",
        hide_value=True,
        structure_type="GRID",
    )
    mode = tree.inputs.menu(
        "Mode",
        default_value="LoBB",
        description="Choose the detail signal used for sharpening",
        expanded=True,
        optional_label=True,
    )
    strength = tree.inputs.float(
        "Strength",
        default_value=1.0,
        description="Amount of sharpening applied",
        min_value=0.0,
    )
    width = tree.inputs.integer(
        "Width",
        default_value=1,
        description="Box blur radius used by both sharpening modes",
        min_value=1,
    )
    iterations = tree.inputs.integer(
        "Iterations",
        default_value=1,
        description="Number of box blur passes used by both sharpening modes",
        min_value=1,
    )
    output = tree.outputs.float(
        "Grid",
        description="Sharpened float grid",
        structure_type="GRID",
    )

    blurred = g.GridMean.float(
        grid=grid,
        width=width,
        iterations=iterations,
    ).o.grid
    lobb = g.GridLaplacian(grid=blurred).o.laplacian
    lobb_sharpen = grid - strength * lobb
    unsharp_mask = grid + strength * (grid - blurred)
    g.MenuSwitch.float(
        menu=mode,
        items={
            "LoBB": lobb_sharpen,
            "Unsharp Mask": unsharp_mask,
        },
    ).o.output >> output


def sharpen_node_group():
    node_group = bpy.data.node_groups.get(GROUP_NAME)
    if node_group is not None:
        return node_group

    with TreeBuilder.geometry(GROUP_NAME, arrange="simple") as tree:
        _build_sharpen(tree)

    return tree.tree
