import bpy
from nodebpy import TreeBuilder, geometry as g
from nodebpy.builder import CustomGeometryGroup
from nodebpy.types import (
    InputBoolean,
    InputFloat,
    InputGeometry,
    InputMenu,
    InputObject,
    InputString,
)

from .transform import mesh_from_holder_space, mesh_in_holder_space


GROUP_NAME = "Sample Grid on Mesh"


class SampleGridOnMesh(CustomGeometryGroup):
    _name = GROUP_NAME

    def __init__(
        self,
        grid: InputFloat = 0.0,
        mesh: InputGeometry = None,
        sampling: InputMenu = "Trilinear",
        name: InputString = "projected_val",
        mesh_parented_by_holder: InputBoolean = True,
        holder: InputObject = None,
    ):
        super().__init__(
            Grid=grid,
            Mesh=mesh,
            Holder=holder,
            **{"Mesh parented by holder": mesh_parented_by_holder},
            Sampling=sampling,
            Name=name,
        )

    def _build_group(self, tree):
        _build_sample_grid_on_mesh(tree)


def _build_sample_grid_on_mesh(tree):
    tree._arrange = "simple"
    tree.tree.description = (
        "Sample a float grid at each mesh point and store the values as an attribute"
    )

    grid = tree.inputs.float(
        "Grid",
        description="Float grid to sample",
        hide_value=True,
        structure_type="GRID",
    )
    mesh = tree.inputs.geometry(
        "Mesh",
        "Mesh whose point positions are used to sample the grid",
    )
    sampling = tree.inputs.menu(
        "Sampling",
        default_value="Trilinear",
        description="Interpolation method used between grid voxels",
    )
    name = tree.inputs.string(
        "Name",
        default_value="projected_val",
        description="Name of the float attribute stored on the mesh points",
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
        "Input mesh with the sampled float attribute",
    )

    sampling_mesh, holder_transform = mesh_in_holder_space(
        mesh,
        holder,
        mesh_parented_by_holder,
    )
    value = g.SampleGrid.float(
        grid=grid,
        position=g.Position().o.position,
        interpolation=sampling,
    ).o.value
    projected_mesh = g.StoreNamedAttribute.point.float(
        geometry=sampling_mesh,
        name=name,
        value=value,
    ).o.geometry
    mesh_from_holder_space(
        projected_mesh,
        holder_transform,
        mesh_parented_by_holder,
    ) >> output


def sample_grid_on_mesh_node_group():
    node_group = bpy.data.node_groups.get(GROUP_NAME)
    if node_group is not None:
        return node_group

    with TreeBuilder.geometry(GROUP_NAME, arrange="simple") as tree:
        _build_sample_grid_on_mesh(tree)

    return tree.tree
