import bpy
from nodebpy import TreeBuilder, geometry as g
from nodebpy.builder import CustomGeometryGroup
from nodebpy.types import InputBundle

from ..combine_channels.nodeMaxOfGrids import MaxOfGrids


GROUP_NAME = "Active Grid Positions"


class ActiveGridPositions(CustomGeometryGroup):
    _name = GROUP_NAME

    def __init__(self, grid_bundle: InputBundle = None):
        super().__init__(**{"Grid Bundle": grid_bundle})

    def _build_group(self, tree):
        _build_active_grid_positions(tree)


def _build_active_grid_positions(tree):
    tree._arrange = "simple"

    tree.tree.show_modifier_manage_panel = True

    grid_bundle = tree.inputs.bundle("Grid Bundle")
    points_output = tree.outputs.geometry("Points")

    grid = MaxOfGrids(grid_bundle=grid_bundle).o.grid
    points = g.GridToPoints.float(grid)
    indices = g.CombineXYZ(
        x=points.o.x,
        y=points.o.y,
        z=points.o.z,
    ).o.vector
    points_with_indices = g.StoreNamedAttribute.point.vector(
        geometry=points.o.points,
        name="ix",
        value=indices,
    ).o.geometry
    points_with_values = g.StoreNamedAttribute.point.boolean(
        geometry=points_with_indices,
        name="value",
        value=points.o.value,
    ).o.geometry
    g.DeleteGeometry(
        geometry=points_with_values,
        selection=points.o.is_tile,
    ).o.geometry >> points_output


def active_grid_positions_node_group():
    node_group = bpy.data.node_groups.get(GROUP_NAME)
    if node_group:
        return node_group

    with TreeBuilder.geometry(GROUP_NAME, arrange="simple") as tree:
        _build_active_grid_positions(tree)

    return tree.tree
