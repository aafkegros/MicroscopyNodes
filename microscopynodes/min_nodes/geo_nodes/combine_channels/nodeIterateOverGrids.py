import bpy
from nodebpy import TreeBuilder, geometry as g
from nodebpy.builder import CustomGeometryGroup
from nodebpy.types import InputBoolean, InputBundle, InputClosure


GROUP_NAME = "Iterate Over Grids"


class IterateOverGrids(CustomGeometryGroup):
    _name = GROUP_NAME

    def __init__(
        self,
        grid_bundle: InputBundle = None,
        closure: InputClosure = None,
        iterate_invalid_grids: InputBoolean = False,
    ):
        super().__init__(
            **{
                "Grid Bundle": grid_bundle,
                "Closure": closure,
                "Iterate Invalid Grids": iterate_invalid_grids,
            }
        )

    def _build_group(self, tree):
        _build_iterate_over_grids(tree)


def _build_iterate_over_grids(tree):
    tree._arrange = "simple"

    tree.tree.show_modifier_manage_panel = True

    grid_bundle = tree.inputs.bundle("Grid Bundle")
    closure = tree.inputs.closure("Closure")
    iterate_invalid_grids = tree.inputs.boolean("Iterate Invalid Grids")
    accumulated_geometry = tree.outputs.geometry("Accumulated Geometry")
    accumulated_grid = tree.outputs.float("Accumulated Grid")
    grid_names = tree.outputs.string("Grid Names")
    grid_names._interface_socket.structure_type = "LIST"

    paths = g.GetNestedBundlePaths(
        grid_bundle,
        mode="Data Type",
        data_type="Float",
    ).o.paths
    path_count = g.ListLength.string(paths).o.length
    repeat = g.RepeatZone()
    tree.tree.links.new(path_count.socket, repeat.input.node.inputs["Iterations"])

    repeat.output.node.repeat_items.new("GEOMETRY", "Accumulated Geometry")
    repeat.output.node.repeat_items.new("FLOAT", "Accumulated Grid")
    repeat.output.node.repeat_items.new("BUNDLE", "Grid Bundle")
    repeat.output.node.repeat_items.new("STRING", "Paths")

    grid_bundle >> repeat.input.i["Grid Bundle"]
    paths >> repeat.input.i["Paths"]

    path = g.GetListItem.string(
        list=repeat.input.o["Paths"],
        index=repeat.iteration,
    ).o.value
    grid = g.GetBundleItem(
        bundle=repeat.input.o["Grid Bundle"],
        path=path,
        socket_type="FLOAT",
        structure_type="GRID",
    ).o.item
    check_frame = g.Frame(
        label=(
            "hacky check for non-included data, "
            "will be improved once voxel extents are readable"
        )
    )
    grid_info = g.GridInfo.float(grid=grid)
    matrix_values = g.SeparateMatrix(matrix=grid_info.o.transform)
    is_invalid = g.Compare.float.equal(
        matrix_values.o.column_4_row_1,
        1_000_000.0,
        epsilon=0.1,
    )
    skip_invalid_grids = g.BooleanMath.l_not(iterate_invalid_grids)
    bypass_closure = g.BooleanMath.l_and(
        is_invalid.o.result,
        skip_invalid_grids.o.boolean,
    )
    for node in (
        grid_info,
        matrix_values,
        is_invalid,
        skip_invalid_grids,
        bypass_closure,
    ):
        node.node.parent = check_frame.node

    evaluate = g.EvaluateClosure(closure, define_signature=True)
    evaluate.node.input_items.new("STRING", "Name")
    evaluate.node.input_items.new("FLOAT", "Grid")
    evaluate.node.input_items.new("INT", "Iteration")
    evaluate.node.input_items.new("GEOMETRY", "Accumulated Geometry")
    evaluate.node.input_items.new("FLOAT", "Accumulated Grid")
    evaluate.node.output_items.new("GEOMETRY", "Accumulated Geometry")
    evaluate.node.output_items.new("FLOAT", "Accumulated Grid")

    path >> evaluate.i["Name"]
    grid >> evaluate.i["Grid"]
    repeat.iteration >> evaluate.i["Iteration"]
    repeat.input.o["Accumulated Geometry"] >> evaluate.i["Accumulated Geometry"]
    repeat.input.o["Accumulated Grid"] >> evaluate.i["Accumulated Grid"]

    geometry_output = g.Switch.geometry(
        switch=bypass_closure.o.boolean,
        false=evaluate.o["Accumulated Geometry"],
        true=repeat.input.o["Accumulated Geometry"],
    )
    grid_output = g.Switch.float(
        switch=bypass_closure.o.boolean,
        false=evaluate.o["Accumulated Grid"],
        true=repeat.input.o["Accumulated Grid"],
    )
    geometry_output.node.parent = check_frame.node
    grid_output.node.parent = check_frame.node
    geometry_output.o.output >> repeat.output.i["Accumulated Geometry"]
    grid_output.o.output >> repeat.output.i["Accumulated Grid"]
    repeat.input.o["Grid Bundle"] >> repeat.output.i["Grid Bundle"]
    repeat.input.o["Paths"] >> repeat.output.i["Paths"]

    repeat.output.o["Accumulated Geometry"] >> accumulated_geometry
    repeat.output.o["Accumulated Grid"] >> accumulated_grid
    repeat.output.o["Paths"] >> grid_names


def iterate_over_grids_node_group():
    node_group = bpy.data.node_groups.get(GROUP_NAME)
    if node_group:
        return node_group

    with TreeBuilder.geometry(GROUP_NAME, arrange="simple") as tree:
        _build_iterate_over_grids(tree)

    return tree.tree
