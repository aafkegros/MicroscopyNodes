import bpy
from nodebpy import TreeBuilder, geometry as g
from nodebpy.builder import CustomGeometryGroup
from nodebpy.types import InputBundle, InputClosure


GROUP_NAME = "Iterate Over Meshes"


class IterateOverMeshes(CustomGeometryGroup):
    _name = GROUP_NAME

    def __init__(
        self,
        geometry_bundle: InputBundle = None,
        closure: InputClosure = None,
    ):
        super().__init__(
            **{
                "Geometry Bundle": geometry_bundle,
                "Closure": closure,
            }
        )

    def _build_group(self, tree):
        _build_iterate_over_meshes(tree)


def _build_iterate_over_meshes(tree):
    tree.tree.show_modifier_manage_panel = True

    geometry_bundle = tree.inputs.bundle("Geometry Bundle")
    closure = tree.inputs.closure("Closure")
    accumulated_geometry = tree.outputs.geometry("Accumulated Geometry")
    accumulated_grid = tree.outputs.float("Accumulated Grid")
    geometry_names = tree.outputs.string("Geometry Names")
    geometry_names._interface_socket.structure_type = "LIST"

    paths = g.GetNestedBundlePaths(
        geometry_bundle,
        mode="Data Type",
        data_type="Geometry",
    ).o.paths
    path_count = g.ListLength.string(paths).o.length
    repeat = g.RepeatZone()
    tree.tree.links.new(path_count.socket, repeat.input.node.inputs["Iterations"])

    repeat.output.node.repeat_items.new("GEOMETRY", "Accumulated Geometry")
    repeat.output.node.repeat_items.new("FLOAT", "Accumulated Grid")
    repeat.output.node.repeat_items.new("BUNDLE", "Geometry Bundle")
    repeat.output.node.repeat_items.new("STRING", "Paths")

    geometry_bundle >> repeat.input.i["Geometry Bundle"]
    paths >> repeat.input.i["Paths"]

    path = g.GetListItem.string(
        list=repeat.input.o["Paths"],
        index=repeat.iteration,
    ).o.value
    geometry = g.GetBundleItem.geometry(
        bundle=repeat.input.o["Geometry Bundle"],
        path=path,
    ).o.item

    evaluate = g.EvaluateClosure(closure, define_signature=True)
    evaluate.node.input_items.new("STRING", "Name")
    evaluate.node.input_items.new("GEOMETRY", "Geometry")
    evaluate.node.input_items.new("INT", "Iteration")
    evaluate.node.input_items.new("GEOMETRY", "Accumulated Geometry")
    evaluate.node.input_items.new("FLOAT", "Accumulated Grid")
    evaluate.node.output_items.new("GEOMETRY", "Accumulated Geometry")
    evaluate.node.output_items.new("FLOAT", "Accumulated Grid")

    path >> evaluate.i["Name"]
    geometry >> evaluate.i["Geometry"]
    repeat.iteration >> evaluate.i["Iteration"]
    repeat.input.o["Accumulated Geometry"] >> evaluate.i["Accumulated Geometry"]
    repeat.input.o["Accumulated Grid"] >> evaluate.i["Accumulated Grid"]

    evaluate.o["Accumulated Geometry"] >> repeat.output.i["Accumulated Geometry"]
    evaluate.o["Accumulated Grid"] >> repeat.output.i["Accumulated Grid"]
    repeat.input.o["Geometry Bundle"] >> repeat.output.i["Geometry Bundle"]
    repeat.input.o["Paths"] >> repeat.output.i["Paths"]

    repeat.output.o["Accumulated Geometry"] >> accumulated_geometry
    repeat.output.o["Accumulated Grid"] >> accumulated_grid
    repeat.output.o["Paths"] >> geometry_names


def iterate_over_meshes_node_group():
    node_group = bpy.data.node_groups.get(GROUP_NAME)
    if node_group:
        return node_group

    with TreeBuilder.geometry(GROUP_NAME) as tree:
        _build_iterate_over_meshes(tree)

    return tree.tree
