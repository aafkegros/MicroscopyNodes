import bpy
from nodebpy import TreeBuilder, geometry as g
from nodebpy.builder import CustomGeometryGroup
from nodebpy.types import InputBundle

from .nodeIterateOverGrids import IterateOverGrids
from .nodeIterateOverMeshes import IterateOverMeshes


GROUP_NAME = "Join Microscopy Grids and Meshes"


class JoinMicroscopyGridsAndMeshes(CustomGeometryGroup):
    _name = GROUP_NAME

    def __init__(self, channel_bundle: InputBundle = None):
        super().__init__(**{"Channel Bundle": channel_bundle})

    def _build_group(self, tree):
        _build_join_microscopy_grids_and_meshes(tree)


def _build_join_microscopy_grids_and_meshes(tree):
    tree.tree.show_modifier_manage_panel = True

    channel_bundle = tree.inputs.bundle("Channel Bundle")
    geometry = tree.outputs.geometry("Geometry")

    grid_closure = g.ClosureZone()
    grid_closure.output.node.input_items.new("STRING", "Name")
    grid_closure.output.node.input_items.new("FLOAT", "Grid")
    grid_closure.output.node.input_items.new("INT", "Iteration")
    grid_closure.output.node.input_items.new("GEOMETRY", "Accumulated Geometry")
    grid_closure.output.node.input_items.new(
        "FLOAT",
        "Accumulated Grid",
    )

    grid_closure.output.node.output_items.new("GEOMETRY", "Accumulated Geometry")
    grid_closure.output.node.output_items.new(
        "FLOAT",
        "Accumulated Grid",
    )

    stored_geometry = g.StoreNamedGrid.float(
        volume=grid_closure.input.o["Accumulated Geometry"],
        name=grid_closure.input.o["Name"],
        grid=grid_closure.input.o["Grid"],
    ).o.volume
    stored_geometry >> grid_closure.output.i["Accumulated Geometry"]
    grid_closure.input.o["Accumulated Grid"] >> grid_closure.output.i["Accumulated Grid"]

    iterate_grids = IterateOverGrids()
    tree.tree.links.new(
        channel_bundle.socket,
        iterate_grids.node.inputs["Grid Bundle"],
    )
    tree.tree.links.new(
        grid_closure.output.o.closure.socket,
        iterate_grids.node.inputs["Closure"],
    )

    mesh_closure = g.ClosureZone()
    mesh_closure.output.node.input_items.new("STRING", "Name")
    mesh_closure.output.node.input_items.new("GEOMETRY", "Geometry")
    mesh_closure.output.node.input_items.new("INT", "Iteration")
    mesh_closure.output.node.input_items.new("GEOMETRY", "Accumulated Geometry")
    mesh_closure.output.node.input_items.new("FLOAT", "Accumulated Grid")
    mesh_closure.output.node.output_items.new("GEOMETRY", "Accumulated Geometry")
    mesh_closure.output.node.output_items.new("FLOAT", "Accumulated Grid")

    indexed_mesh = g.StoreNamedAttribute.point.integer(
        geometry=mesh_closure.input.o["Geometry"],
        name=mesh_closure.input.o["Name"],
        value=1,
    ).o.geometry
    joined_meshes = g.JoinGeometry(
        geometry=[
            mesh_closure.input.o["Accumulated Geometry"],
            indexed_mesh,
        ]
    ).o.geometry
    joined_meshes >> mesh_closure.output.i["Accumulated Geometry"]
    mesh_closure.input.o["Accumulated Grid"] >> mesh_closure.output.i["Accumulated Grid"]

    iterate_meshes = IterateOverMeshes()
    tree.tree.links.new(
        channel_bundle.socket,
        iterate_meshes.node.inputs["Geometry Bundle"],
    )
    tree.tree.links.new(
        mesh_closure.output.o.closure.socket,
        iterate_meshes.node.inputs["Closure"],
    )

    g.JoinGeometry(
        geometry=[
            iterate_grids.o["Accumulated Geometry"],
            iterate_meshes.o["Accumulated Geometry"],
        ]
    ).o.geometry >> geometry


def join_microscopy_grids_and_meshes_node_group():
    node_group = bpy.data.node_groups.get(GROUP_NAME)
    if node_group:
        return node_group

    with TreeBuilder.geometry(GROUP_NAME) as tree:
        _build_join_microscopy_grids_and_meshes(tree)

    return tree.tree
