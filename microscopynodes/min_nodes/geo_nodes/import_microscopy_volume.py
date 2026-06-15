import bpy
from nodebpy import TreeBuilder, geometry as g
from nodebpy.builder import CustomGeometryGroup
from nodebpy.types import (
    InputBoolean,
    InputFloat,
    InputInteger,
    InputMatrix,
    InputObject,
    InputString,
)

from .nodeHolderBundleInputs import HolderBundleInputs


GROUP_NAME = "Import Microscopy Volume"


class ImportMicroscopyVolume(CustomGeometryGroup):
    _name = GROUP_NAME

    def __init__(
        self,
        holder: InputObject = None,
        grid_name: InputString = "data",
        normalized: InputBoolean = True,
        vdb_minimum: InputFloat = 0.0,
        vdb_maximum: InputFloat = 1.0,
        original_maximum: InputFloat = 1.0,
        include: InputBoolean = False,
        template_str: InputString = "",
        cache_dir: InputString = "",
        dataset_hash: InputString = "",
        scale: InputInteger = 0,
        masked: InputString = "False",
        channel_ix: InputInteger = 0,
        original_path: InputString = "",
        channel_affine_matrix: InputMatrix = None,
    ):
        super().__init__(
            Holder=holder,
            **{
                "Grid Name": grid_name,
                "Normalized": normalized,
                "VDB Minimum": vdb_minimum,
                "VDB Maximum": vdb_maximum,
                "Original Maximum": original_maximum,
                "Include": include,
                "template_str": template_str,
                "cache_dir": cache_dir,
                "dataset_hash": dataset_hash,
                "scale": scale,
                "masked": masked,
                "channel_ix": channel_ix,
                "original_path": original_path,
                "Channel Affine Matrix": channel_affine_matrix,
            },
        )

    def _build_group(self, tree):
        _build_import_microscopy_volume(tree)


def _build_import_microscopy_volume(tree):
    tree._arrange = "simple"

    tree.tree.is_modifier = True
    tree.tree.show_modifier_manage_panel = True

    holder = tree.inputs.object("Holder")
    grid_name = tree.inputs.string("Grid Name", default_value="data")
    normalized = tree.inputs.boolean("Normalized", default_value=True)
    vdb_minimum = tree.inputs.float(
        "VDB Minimum",
        min_value=-10000.0,
        max_value=10000.0,
    )
    vdb_maximum = tree.inputs.float(
        "VDB Maximum",
        default_value=1.0,
        min_value=-10000.0,
        max_value=10000.0,
    )
    original_maximum = tree.inputs.float("Original Maximum", default_value=1.0)
    include = tree.inputs.boolean("Include")
    template_str = tree.inputs.string("template_str")
    cache_dir = tree.inputs.string("cache_dir")
    dataset_hash = tree.inputs.string("dataset_hash")
    scale = tree.inputs.integer("scale")
    masked = tree.inputs.string("masked", default_value="False")
    channel_ix = tree.inputs.integer("channel_ix")
    tree.inputs.string("original_path")
    channel_affine_matrix = tree.inputs.matrix("Channel Affine Matrix")

    volume_output = tree.outputs.geometry("Volume")
    grid_output = tree.outputs.float("Grid", structure_type="GRID")

    frame = HolderBundleInputs(holder=holder).o.frame
    path = g.FormatString(
        format=template_str,
        items={
            "cache_dir": cache_dir,
            "dataset_hash": dataset_hash,
            "scale": scale,
            "masked": masked,
            "channel_ix": channel_ix,
            "t": frame,
        },
    ).o.string
    imported_volume = g.ImportVDB(path=path).o.volume

    source_grid = g.GetNamedGrid.float(
        volume=imported_volume,
        name=grid_name,
        remove=True,
    )
    normalized_grid = g.MapRange(
        value=source_grid.o.grid,
        from_min=vdb_minimum,
        from_max=vdb_maximum,
        to_min=0.0,
        to_max=1.0,
        clamp=True,
    ).o.result
    original_grid = g.Math.multiply(
        value=normalized_grid,
        value_001=original_maximum,
    ).o.value

    normalized_volume = g.StoreNamedGrid.float(
        volume=imported_volume,
        name=grid_name,
        grid=normalized_grid,
    ).o.volume
    original_volume = g.StoreNamedGrid.float(
        volume=imported_volume,
        name=grid_name,
        grid=original_grid,
    ).o.volume
    selected_volume = g.Switch.geometry(
        switch=normalized,
        false=original_volume,
        true=normalized_volume,
    ).o.output

    output_grid = g.GetNamedGrid.float(
        volume=selected_volume,
        name=grid_name,
        remove=False,
    )
    transformed_grid = g.SetGridTransform.float(
        grid=output_grid.o.grid,
        transform=channel_affine_matrix,
    ).o.grid

    fake_topology = g.CubeGridTopology(
        bounds_min=(-1.0, -1.0, -1.0),
        bounds_max=(1.0, 1.0, 1.0),
        resolution_x=3,
        resolution_y=3,
        resolution_z=3,
    ).o.topology
    fake_grid = g.FieldToGrid.float(
        topology=fake_topology,
        items={"Grid": 0.0},
    ).node.outputs["Grid"]
    fake_transform = g.CombineMatrix(
        column_1_row_1=1e-3,
        column_2_row_2=1e-3,
        column_3_row_3=1e-3,
        column_4_row_1=1_000_000.0,
        column_4_row_2=1_000_000.0,
        column_4_row_3=1_000_000.0,
    ).o.matrix
    invalid_grid = g.SetGridTransform.float(
        grid=fake_grid,
        transform=fake_transform,
    ).o.grid
    selected_grid = g.Switch.float(
        switch=include,
        false=invalid_grid,
        true=transformed_grid,
    ).o.output
    output_volume = g.StoreNamedGrid.float(
        volume=output_grid.o.volume,
        name=grid_name,
        grid=selected_grid,
    ).o.volume

    output_volume >> volume_output
    selected_grid >> grid_output


def import_microscopy_volume_node_group():
    node_group = bpy.data.node_groups.get(GROUP_NAME)
    if node_group is not None:
        return node_group

    with TreeBuilder.geometry(GROUP_NAME, arrange="simple") as tree:
        _build_import_microscopy_volume(tree)

    return tree.tree
