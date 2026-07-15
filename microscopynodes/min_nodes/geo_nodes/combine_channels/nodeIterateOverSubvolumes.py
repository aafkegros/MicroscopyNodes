import bpy
from nodebpy import TreeBuilder, geometry as g
from nodebpy.builder import CustomGeometryGroup
from nodebpy.types import InputClosure, InputFloat, InputGeometry, InputObject

from ..nodeHolderBundleInputs import HolderBundleInputs


GROUP_NAME = "Iterate Over Subvolumes"


class IterateOverSubvolumes(CustomGeometryGroup):
    _name = GROUP_NAME

    def __init__(
        self,
        subvolumes: InputGeometry = None,
        closure: InputClosure = None,
        holder: InputObject = None,
        voxel_spacing: InputFloat = 0.3,
    ):
        super().__init__(
            **{
                "Subvolumes": subvolumes,
                "Closure": closure,
                "Holder": holder,
                "Voxel Spacing": voxel_spacing,
            }
        )

    def _build_group(self, tree):
        _build_iterate_over_subvolumes(tree)


def _build_iterate_over_subvolumes(tree):
    tree._arrange = "simple"

    tree.tree.show_modifier_manage_panel = True
    tree.tree.description = (
        "Iterate over selected subvolume instances and accumulate into a target grid"
    )

    subvolumes = tree.inputs.geometry(
        "Subvolumes",
        description="Volume instances to iterate over",
    )
    closure = tree.inputs.closure("Closure")
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
    accumulated_geometry = tree.outputs.geometry("Accumulated Geometry")
    accumulated_grid = tree.outputs.float("Accumulated Grid", structure_type="GRID")

    bounds_mesh = g.VolumeToMesh(
        volume=subvolumes,
        threshold=1e-5,
    ).o.mesh
    bounds_geometry = g.RealizeInstances(bounds_mesh).o.geometry
    bounds = g.BoundingBox(geometry=bounds_geometry)
    holder_inputs = HolderBundleInputs(holder=holder)
    inverse_world_scale = g.Math.divide(
        value=1.0,
        value_001=holder_inputs.o.scene_world_scale_base,
    ).o.value
    bounds_min = g.VectorMath.scale(
        vector=bounds.o.min,
        scale=inverse_world_scale,
    ).o.vector
    bounds_max = g.VectorMath.scale(
        vector=bounds.o.max,
        scale=inverse_world_scale,
    ).o.vector
    protected_voxel_spacing = g.Math.divide(
        value=voxel_spacing,
        value_001=holder_inputs.o.scene_world_scale_base,
    ).o.value
    extents = g.VectorMath.subtract(
        vector=bounds_max,
        vector_001=bounds_min,
    ).o.vector
    extents_xyz = g.SeparateXYZ(vector=extents)
    resolution_x = g.FloatToInteger(
        g.Math.maximum(
            g.Math.divide(extents_xyz.o.x, protected_voxel_spacing).o.value,
            1.0,
        ).o.value,
        rounding_mode="CEILING",
    ).o.integer
    resolution_y = g.FloatToInteger(
        g.Math.maximum(
            g.Math.divide(extents_xyz.o.y, protected_voxel_spacing).o.value,
            1.0,
        ).o.value,
        rounding_mode="CEILING",
    ).o.integer
    resolution_z = g.FloatToInteger(
        g.Math.maximum(
            g.Math.divide(extents_xyz.o.z, protected_voxel_spacing).o.value,
            1.0,
        ).o.value,
        rounding_mode="CEILING",
    ).o.integer
    initial_grid = g.FieldToGrid.float(
        topology=g.CubeGridTopology(
            bounds_min=bounds_min,
            bounds_max=bounds_max,
            resolution_x=resolution_x,
            resolution_y=resolution_y,
            resolution_z=resolution_z,
        ).o.topology,
        items={"Grid": 0.0},
    ).node.outputs["Grid"]

    instance_count = g.DomainSize(
        geometry=subvolumes,
        component="INSTANCES",
    ).o.instance_count
    repeat = g.RepeatZone()
    tree.tree.links.new(instance_count.socket, repeat.input.node.inputs["Iterations"])

    repeat.output.node.repeat_items.new("GEOMETRY", "Accumulated Geometry")
    repeat.output.node.repeat_items.new("FLOAT", "Accumulated Grid")
    repeat.output.node.repeat_items.new("GEOMETRY", "Subvolumes")

    subvolumes >> repeat.input.i["Subvolumes"]
    tree.tree.links.new(initial_grid, repeat.input.i["Accumulated Grid"].socket)

    keep_current_instance = g.Compare.integer.not_equal(
        g.Index().o.index,
        repeat.iteration,
    ).o.result
    subvolume = g.DeleteGeometry(
        geometry=repeat.input.o["Subvolumes"],
        selection=keep_current_instance,
        domain="INSTANCE",
    ).o.geometry
    subvolume_mesh = g.VolumeToMesh(
        volume=subvolume,
        threshold=1e-5,
    ).o.mesh
    instance_transform = g.SampleIndex.instance.matrix(
        geometry=subvolume_mesh,
        value=g.InstanceTransform().o.transform,
        index=0,
    ).o.value
    realized_subvolume = g.RealizeInstances(subvolume).o.geometry
    grid = g.GetNamedGrid.float(
        volume=realized_subvolume,
        name="density",
        remove=False,
    ).o.grid
    transformed_grid = g.SetGridTransform.float(
        grid=grid,
        transform=instance_transform @ g.GridInfo.float(grid=grid).o.transform,
    ).o.grid

    evaluate = g.EvaluateClosure(closure, define_signature=True)
    evaluate.node.input_items.new("GEOMETRY", "Subvolume")
    evaluate.node.input_items.new("FLOAT", "Grid")
    evaluate.node.input_items.new("INT", "Iteration")
    evaluate.node.input_items.new("GEOMETRY", "Accumulated Geometry")
    evaluate.node.input_items.new("FLOAT", "Accumulated Grid")
    evaluate.node.output_items.new("GEOMETRY", "Accumulated Geometry")
    evaluate.node.output_items.new("FLOAT", "Accumulated Grid")

    realized_subvolume >> evaluate.i["Subvolume"]
    transformed_grid >> evaluate.i["Grid"]
    repeat.iteration >> evaluate.i["Iteration"]
    repeat.input.o["Accumulated Geometry"] >> evaluate.i["Accumulated Geometry"]
    repeat.input.o["Accumulated Grid"] >> evaluate.i["Accumulated Grid"]

    evaluate.o["Accumulated Geometry"] >> repeat.output.i["Accumulated Geometry"]
    evaluate.o["Accumulated Grid"] >> repeat.output.i["Accumulated Grid"]
    repeat.input.o["Subvolumes"] >> repeat.output.i["Subvolumes"]

    repeat.output.o["Accumulated Geometry"] >> accumulated_geometry
    repeat.output.o["Accumulated Grid"] >> accumulated_grid


def iterate_over_subvolumes_node_group():
    node_group = bpy.data.node_groups.get(GROUP_NAME)
    if node_group:
        return node_group

    with TreeBuilder.geometry(GROUP_NAME, arrange="simple") as tree:
        _build_iterate_over_subvolumes(tree)

    return tree.tree
