import bpy
from nodebpy import TreeBuilder, geometry as g
from nodebpy.builder import CustomGeometryGroup
from nodebpy.types import InputFloat


GROUP_NAME = "Microscopy Grid to Points"


class MicroscopyGridToPoints(CustomGeometryGroup):
    _name = GROUP_NAME

    def __init__(self, grid: InputFloat = 0.0):
        super().__init__(Grid=grid)

    def _build_group(self, tree):
        _build_microscopy_grid_to_points(tree)


def _build_microscopy_grid_to_points(tree):
    tree.tree.show_modifier_manage_panel = True

    grid = tree.inputs.float("Grid", hide_value=True)
    geometry = tree.outputs.geometry("Geometry")

    points = g.GridToPoints.float(grid)
    delete = g.DeleteGeometry(
        geometry=points.o.points,
        selection=g.BooleanMath.l_or(
            points.o.is_tile,
            g.Math.less_than(points.o.value, 0.0001).o.value,
        ).o.boolean,
    )

    delete.o.geometry >> geometry


def microscopy_grid_to_points_node_group():
    node_group = bpy.data.node_groups.get(GROUP_NAME)
    if node_group:
        return node_group

    with TreeBuilder.geometry(GROUP_NAME) as tree:
        _build_microscopy_grid_to_points(tree)

    return tree.tree
