import bpy
from nodebpy import TreeBuilder, geometry as g
from nodebpy.builder import CustomGeometryGroup
from nodebpy.types import InputFloat, InputGeometry, InputMenu, InputObject

from ..nodeHolderBundleInputs import HolderBundleInputs


GROUP_NAME = "Split to Subvolumes"


class SplitToSubvolumes(CustomGeometryGroup):
    _name = GROUP_NAME

    def __init__(
        self,
        mesh_instances: InputGeometry = None,
        grid: InputFloat = 0.0,
        holder: InputObject = None,
        voxel_size: InputFloat = 0.3,
        sampling: InputMenu = "Nearest Neighbor",
    ):
        super().__init__(
            **{
                "Mesh Instances": mesh_instances,
                "Holder": holder,
                "Voxel Size": voxel_size,
                "Sampling": sampling,
            },
            Grid=grid,
        )

    def _build_group(self, tree):
        _build_split_to_subvolumes(tree)


def _build_split_to_subvolumes(tree):
    tree._arrange = "simple"
    tree.tree.description = (
        "Voxelize pre-split mesh instances and sample a grid into each generated subvolume"
    )

    mesh_instances = tree.inputs.geometry(
        "Mesh Instances",
        description="Pre-split mesh instances to voxelize",
    )
    grid = tree.inputs.float(
        "Grid",
        description="Float grid sampled into each generated subvolume",
        hide_value=True,
        structure_type="GRID",
    )
    holder = tree.inputs.object(
        "Holder",
        optional_label=True,
    )
    voxel_size = tree.inputs.float(
        "Voxel Size",
        0.3,
        min_value=0.01,
        subtype="DISTANCE",
        description="Voxel size for each generated subvolume",
    )
    sampling = tree.inputs.menu(
        "Sampling",
        default_value="Nearest Neighbor",
        description="Interpolation method used when sampling the input grid",
    )
    subvolumes = tree.outputs.geometry(
        "Subvolumes",
        description="Generated subvolume instances, one sampled volume per input mesh instance",
    )

    foreach = g.ForEachGeometryElementZone(
        geometry=mesh_instances,
        domain="INSTANCE",
    )
    holder_inputs = HolderBundleInputs(holder=holder)
    protected_voxel_size = g.Math.divide(
        value=voxel_size,
        value_001=holder_inputs.o.scene_world_scale_base,
    ).o.value
    topology = g.MeshToDensityGrid(
        mesh=foreach.input.o.element,
        voxel_size=protected_voxel_size,
        gradient_width=0.0,
    ).o.density_grid
    sampled_grid = g.FieldToGrid.float(
        topology=topology,
        items={
            "Sampled Grid": g.SampleGrid.float(
                grid=grid,
                position=g.Position().o.position,
                interpolation=sampling,
            ).o.value,
        },
    ).node.outputs["Sampled Grid"]
    base_volume = g.MeshToVolume(
        mesh=foreach.input.o.element,
        resolution_mode="Size",
        voxel_size=protected_voxel_size,
        interior_band_width=0.0,
    ).o.volume
    sampled_volume = g.StoreNamedGrid.float(
        volume=base_volume,
        name="density",
        grid=sampled_grid,
    ).o.volume

    foreach.output.capture_generated(sampled_volume) >> subvolumes


def split_to_subvolumes_node_group():
    node_group = bpy.data.node_groups.get(GROUP_NAME)
    if node_group is not None:
        return node_group

    with TreeBuilder.geometry(GROUP_NAME, arrange="simple") as tree:
        _build_split_to_subvolumes(tree)

    return tree.tree
