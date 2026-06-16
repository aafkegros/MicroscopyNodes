import bpy
from nodebpy import TreeBuilder, geometry as g
from nodebpy.builder import CustomGeometryGroup
from nodebpy.types import (
    InputBoolean,
    InputFloat,
    InputGeometry,
    InputInteger,
    InputMenu,
    InputObject,
    InputString,
)

from .transform import mesh_from_holder_space, mesh_in_holder_space


GROUP_NAME = "Project Grid to Mesh"
DIRECTIONS = {
    "Outward": 0,
    "Inward": 1,
    "Both": 2,
}


class ProjectGridToMesh(CustomGeometryGroup):
    _name = GROUP_NAME

    def __init__(
        self,
        grid: InputFloat = 0.0,
        mesh: InputGeometry = None,
        distance: InputFloat = 0.5,
        samples: InputInteger = 10,
        direction: InputMenu = "Both",
        name: InputString = "projected_val",
        mesh_parented_by_holder: InputBoolean = True,
        holder: InputObject = None,
    ):
        super().__init__(
            Grid=grid,
            Mesh=mesh,
            Holder=holder,
            **{"Mesh parented by holder": mesh_parented_by_holder},
            Distance=distance,
            Samples=samples,
            Direction=direction,
            Name=name,
        )

    def _build_group(self, tree):
        _build_project_grid_to_mesh(tree)


def _build_project_grid_to_mesh(tree):
    tree._arrange = "simple"
    tree.tree.description = (
        "Project a float grid onto a mesh by averaging samples along each point normal"
    )

    grid = tree.inputs.float(
        "Grid",
        description="Float grid to project onto the mesh",
        hide_value=True,
        structure_type="GRID",
    )
    mesh = tree.inputs.geometry(
        "Mesh",
        "Mesh whose point normals define the sampling paths",
    )
    distance = tree.inputs.float(
        "Distance",
        default_value=0.5,
        description="Maximum distance sampled along each mesh point normal",
        min_value=0.0,
        subtype="DISTANCE",
    )
    samples = tree.inputs.integer(
        "Samples",
        default_value=10,
        description="Number of evenly spaced grid samples taken per mesh point",
        min_value=2,
    )
    direction = tree.inputs.menu(
        "Direction",
        default_value="Both",
        description="Sample outward, inward, or on both sides of the mesh",
        expanded=True,
        optional_label=True,
    )
    name = tree.inputs.string(
        "Name",
        default_value="projected_val",
        description="Name of the averaged float attribute stored on the mesh points",
    )
    mesh_parented_by_holder = tree.inputs.boolean(
        "Mesh parented by holder",
        default_value=True,
        description=(
            "Enable when the mesh already uses the holder's local coordinate space"
        ),
    )
    holder = tree.inputs.object(
        "Holder",
        description=(
            "Dataset holder used to convert an unparented mesh into grid coordinates"
        ),
        optional_label=True,
    )
    output = tree.outputs.geometry(
        "Mesh",
        "Input mesh with the projected float attribute",
    )

    sampling_mesh, holder_transform = mesh_in_holder_space(
        mesh,
        holder,
        mesh_parented_by_holder,
    )
    source = g.CaptureAttribute.point(
        geometry=sampling_mesh,
        items={
            "Source Index": g.Index().o.index,
            "Normal": g.Normal().o.normal,
        },
    )
    source_points = g.MeshToPoints.vertices(mesh=source.o.geometry)
    sample_points = g.DuplicateElements.point(
        geometry=source_points.o.points,
        amount=samples,
    )

    direction_index = g.MenuSwitch.integer(
        menu=direction,
        items=DIRECTIONS,
    ).o.output
    start = g.IndexSwitch.float(
        index=direction_index,
        items=(0.0, -distance, -distance),
    ).o.output
    end = g.IndexSwitch.float(
        index=direction_index,
        items=(distance, 0.0, distance),
    ).o.output
    sample_offset = g.MapRange.linear(
        value=sample_points.o.duplicate_index,
        from_max=samples - 1,
        to_min=start,
        to_max=end,
    ).o.result
    positioned_points = g.SetPosition(
        geometry=sample_points.o.geometry,
        offset=g.VectorMath.scale(
            vector=source.node.outputs["Normal"],
            scale=sample_offset,
        ).o.vector,
    ).o.geometry

    sampled_value = g.SampleGrid.float(
        grid=grid,
        position=g.Position().o.position,
    ).o.value
    average = g.FieldAverage.point.float(
        value=sampled_value,
        group_index=source.node.outputs["Source Index"],
    ).o.mean
    first_sample_index = g.IntegerMath.multiply(
        g.Index().o.index,
        samples,
    ).o.value
    projected_value = g.SampleIndex.point.float(
        geometry=positioned_points,
        value=average,
        index=first_sample_index,
    ).o.value

    projected_mesh = g.StoreNamedAttribute.point.float(
        geometry=sampling_mesh,
        name=name,
        value=projected_value,
    ).o.geometry
    mesh_from_holder_space(
        projected_mesh,
        holder_transform,
        mesh_parented_by_holder,
    ) >> output


def project_grid_to_mesh_node_group():
    node_group = bpy.data.node_groups.get(GROUP_NAME)
    if node_group is not None:
        return node_group

    with TreeBuilder.geometry(GROUP_NAME, arrange="simple") as tree:
        _build_project_grid_to_mesh(tree)

    return tree.tree
