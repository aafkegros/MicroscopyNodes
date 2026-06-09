import bpy
from nodebpy import TreeBuilder, geometry as g
from nodebpy.builder import CustomGeometryGroup
from nodebpy.types import InputBundle

from .nodeIterateOverGrids import IterateOverGrids


GROUP_NAME = "Max Channels"


class MaxChannels(CustomGeometryGroup):
    _name = GROUP_NAME

    def __init__(self, channel_bundle: InputBundle = None):
        super().__init__(**{"Channel Bundle": channel_bundle})

    def _build_group(self, tree):
        _build_max_channels(tree)


def _build_max_channels(tree):
    tree._arrange = "simple"

    channel_bundle = tree.inputs.bundle("Channel Bundle")
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
    tree.tree.links.new(channel_bundle.socket, iterate.node.inputs["Grid Bundle"])
    tree.tree.links.new(closure.output.o.closure.socket, iterate.node.inputs["Closure"])
    tree.tree.links.new(iterate.node.outputs["Accumulated Grid"], grid.socket)


def max_channels_node_group():
    node_group = bpy.data.node_groups.get(GROUP_NAME)
    if node_group is not None:
        return node_group

    with TreeBuilder.geometry(GROUP_NAME, arrange="simple") as tree:
        _build_max_channels(tree)

    return tree.tree
