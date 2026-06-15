import bpy
from nodebpy import TreeBuilder, geometry as g
from nodebpy.builder import CustomGeometryGroup
from nodebpy.types import InputBundle

from .nodeIterateOverGrids import IterateOverGrids


GROUP_NAME = "Max of Grids"


class MaxOfGrids(CustomGeometryGroup):
    _name = GROUP_NAME

    def __init__(self, grid_bundle: InputBundle = None):
        super().__init__(**{"Grid Bundle": grid_bundle})

    def _build_group(self, tree):
        _build_max_of_grids(tree)


def _build_max_of_grids(tree):
    tree._arrange = "simple"

    grid_bundle = tree.inputs.bundle("Grid Bundle")
    grid = tree.outputs.float("Grid", structure_type="GRID")

    closure = g.ClosureZone()
    closure.output.node.input_items.new("STRING", "Name")
    closure.output.node.input_items.new("FLOAT", "Grid")
    closure.output.node.input_items.new("INT", "Iteration")
    closure.output.node.input_items.new("GEOMETRY", "Accumulated Geometry")
    closure.output.node.input_items.new("FLOAT", "Accumulated Grid")
    closure.output.node.output_items.new("GEOMETRY", "Accumulated Geometry")
    closure.output.node.output_items.new("FLOAT", "Accumulated Grid")

    closure.input.o["Accumulated Geometry"] >> closure.output.i["Accumulated Geometry"]
    g.Math.maximum(
        closure.input.o["Accumulated Grid"],
        closure.input.o["Grid"],
    ).o.value >> closure.output.i["Accumulated Grid"]

    iterate = IterateOverGrids()
    tree.tree.links.new(grid_bundle.socket, iterate.node.inputs["Grid Bundle"])
    tree.tree.links.new(closure.output.o.closure.socket, iterate.node.inputs["Closure"])
    tree.tree.links.new(iterate.node.outputs["Accumulated Grid"], grid.socket)


def max_of_grids_node_group():
    node_group = bpy.data.node_groups.get(GROUP_NAME)
    if node_group is not None:
        return node_group

    with TreeBuilder.geometry(GROUP_NAME, arrange="simple") as tree:
        _build_max_of_grids(tree)

    return tree.tree
