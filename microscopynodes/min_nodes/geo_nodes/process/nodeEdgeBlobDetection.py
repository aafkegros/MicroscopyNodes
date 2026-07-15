import bpy
from nodebpy import TreeBuilder, geometry as g
from nodebpy.builder import CustomGeometryGroup
from nodebpy.types import InputFloat, InputInteger


GROUP_NAME = "Edge/Blob Detection (LoBB)"


class EdgeBlobDetection(CustomGeometryGroup):
    _name = GROUP_NAME

    def __init__(
        self,
        grid: InputFloat = 0.0,
        width: InputInteger = 1,
        iterations: InputInteger = 1,
    ):
        super().__init__(Grid=grid, Width=width, Iterations=iterations)

    def _build_group(self, tree):
        _build_edge_blob_detection(tree)


def _build_edge_blob_detection(tree):
    tree._arrange = "simple"
    tree.tree.description = (
        "Detect edges and blobs using the Laplacian of a box-blurred grid"
    )

    grid = tree.inputs.float(
        "Grid",
        description="Float grid in which to detect edges and blobs",
        hide_value=True,
        structure_type="GRID",
    )
    width = tree.inputs.integer(
        "Width",
        default_value=1,
        description="Box blur radius in voxels",
        min_value=1,
    )
    iterations = tree.inputs.integer(
        "Iterations",
        default_value=1,
        description="Number of box blur passes applied before the Laplacian",
        min_value=1,
    )
    output = tree.outputs.float(
        "Grid",
        description="Laplacian response of the blurred grid",
        structure_type="GRID",
    )

    blurred = g.GridMean.float(
        grid=grid,
        width=width,
        iterations=iterations,
    ).o.grid
    g.GridLaplacian(grid=blurred).o.laplacian >> output


def edge_blob_detection_node_group():
    node_group = bpy.data.node_groups.get(GROUP_NAME)
    if node_group is not None:
        return node_group

    with TreeBuilder.geometry(GROUP_NAME, arrange="simple") as tree:
        _build_edge_blob_detection(tree)

    return tree.tree
