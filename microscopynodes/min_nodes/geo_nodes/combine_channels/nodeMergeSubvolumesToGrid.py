import bpy
from nodebpy import TreeBuilder, geometry as g
from nodebpy.builder import CustomGeometryGroup
from nodebpy.types import InputFloat, InputGeometry, InputObject

from .nodeIterateOverSubvolumes import IterateOverSubvolumes


GROUP_NAME = "Merge Subvolumes to Grid"


class MergeSubvolumesToGrid(CustomGeometryGroup):
    _name = GROUP_NAME

    def __init__(
        self,
        subvolumes: InputGeometry = None,
        holder: InputObject = None,
        voxel_spacing: InputFloat = 0.3,
    ):
        super().__init__(
            **{
                "Subvolumes": subvolumes,
                "Holder": holder,
                "Voxel Spacing": voxel_spacing,
            }
        )

    def _build_group(self, tree):
        _build_merge_subvolumes_to_grid(tree)


def _build_merge_subvolumes_to_grid(tree):
    tree._arrange = "simple"

    subvolumes = tree.inputs.geometry(
        "Subvolumes",
        description="Volume instances to merge",
    )
    holder = tree.inputs.object(
        "Holder",
        optional_label=True,
    )
    voxel_spacing = tree.inputs.float(
        "Voxel Spacing",
        0.3,
        min_value=0.01,
        subtype="DISTANCE",
        description="Output voxel spacing in meters",
    )
    grid = tree.outputs.float("Grid", structure_type="GRID")

    closure = g.ClosureZone()
    closure.output.node.input_items.new("GEOMETRY", "Subvolume")
    closure.output.node.input_items.new("FLOAT", "Grid")
    closure.output.node.input_items.new("INT", "Iteration")
    closure.output.node.input_items.new("GEOMETRY", "Accumulated Geometry")
    closure.output.node.input_items.new("FLOAT", "Accumulated Grid")
    closure.output.node.output_items.new("GEOMETRY", "Accumulated Geometry")
    closure.output.node.output_items.new("FLOAT", "Accumulated Grid")

    closure.input.o["Accumulated Geometry"] >> closure.output.i["Accumulated Geometry"]
    sampled_grid = g.SampleGrid.float(
        grid=closure.input.o["Grid"],
        interpolation="Nearest Neighbor",
    ).o.value
    g.Math.maximum(
        closure.input.o["Accumulated Grid"],
        sampled_grid,
    ).o.value >> closure.output.i["Accumulated Grid"]

    iterate = IterateOverSubvolumes(
        holder=holder,
        voxel_spacing=voxel_spacing,
    )
    tree.tree.links.new(subvolumes.socket, iterate.node.inputs["Subvolumes"])
    tree.tree.links.new(closure.output.o.closure.socket, iterate.node.inputs["Closure"])
    tree.tree.links.new(iterate.node.outputs["Accumulated Grid"], grid.socket)


def merge_subvolumes_to_grid_node_group():
    node_group = bpy.data.node_groups.get(GROUP_NAME)
    if node_group is not None:
        return node_group

    with TreeBuilder.geometry(GROUP_NAME, arrange="simple") as tree:
        _build_merge_subvolumes_to_grid(tree)

    return tree.tree
