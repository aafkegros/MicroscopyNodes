import bpy
from nodebpy import TreeBuilder, geometry as g
from nodebpy.builder import CustomGeometryGroup
from nodebpy.types import (
    InputCollection,
    InputFloat,
    InputGeometry,
    InputMenu,
    InputObject,
)

from ..nodeHolderBundleInputs import HolderBundleInputs
from .nodeMaskBoxField import ClipFieldToBox


GROUP_NAME = "Mask Grid"


class MaskGrid(CustomGeometryGroup):
    _name = GROUP_NAME

    def __init__(
        self,
        grid: InputFloat = 0.5,
        with_: InputMenu = "Object",
        object: InputObject = None,
        collection: InputCollection = None,
        mesh: InputGeometry = None,
        holder: InputObject = None,
        mask_resolution: InputFloat = 0.3,
        mask: InputFloat = 0.0,
    ):
        super().__init__(
            **{
                "Grid": grid,
                "With": with_,
                "Object": object,
                "Collection": collection,
                "Mesh": mesh,
                "Holder": holder,
                "Mask Resolution": mask_resolution,
                "Mask": mask,
            }
        )

    def _build_group(self, tree):
        _build_mask_grid(tree)


def _build_mask_grid(tree):
    tree._arrange = "simple"

    tree.tree.show_modifier_manage_panel = True

    grid = tree.inputs.float(
        "Grid",
        0.5,
        structure_type="GRID",
    )
    with_ = tree.inputs.menu("With", "Object")
    object = tree.inputs.object("Object")
    collection = tree.inputs.collection("Collection", optional_label=True)
    mesh = tree.inputs.geometry("Mesh")
    holder = tree.inputs.object(
        "Holder",
        optional_label=True,
        hide_value=True,
        hide_in_modifier=True,
    )
    mask_resolution = tree.inputs.float(
        "Mask Resolution",
        0.3,
        min_value=0.01,
        subtype="DISTANCE",
    )
    mask = tree.inputs.float(
        "Mask",
        hide_value=True,
        optional_label=True,
    )
    inside_mask = tree.outputs.float("Inside Mask")
    outside_mask = tree.outputs.float("Outside Mask")

    object_geometry = g.ObjectInfo(
        object=object,
        transform_space="RELATIVE",
    ).o.geometry
    collection_instances = g.CollectionInfo(
        collection=collection,
        transform_space="RELATIVE",
    ).o.instances

    mask_source = g.MenuSwitch.geometry(
        with_,
        {
            "Object": object_geometry,
            "Collection": collection_instances,
            "Mesh": mesh,
            "Grid": object_geometry,
            "Box": object_geometry,
        },
    )

    realized = g.RealizeInstances(
        mask_source.o.output,
    ).o.geometry
    holder_inputs = HolderBundleInputs(holder=holder)
    voxel_size = g.Math.divide(
        value=mask_resolution,
        value_001=holder_inputs.o.scene_world_scale_base,
    ).o.value

    volume_grid = g.GetNamedGrid.float(
        volume=g.MeshToVolume(
            mesh=realized,
            resolution_mode="Size",
            voxel_size=voxel_size,
            interior_band_width=0.0,
        ).o.volume,
        name="density",
    ).o.grid

    box_mask = g.FieldToGrid.boolean(
        topology=grid,
        items={
            "Mask": ClipFieldToBox(
                box_object=object,
            ).o.clipped_field,
        },
    ).node.outputs["Mask"]

    selected_grid = g.Switch.float(
        switch=mask_source.node.outputs["Grid"],
        false=volume_grid,
        true=mask,
    ).o.output

    sampled_mask = g.Math.greater_than(
        g.SampleGrid.float(
            grid=selected_grid,
        ).o.value,
        0.0,
    ).o.value
    mask_value = g.Switch.boolean(
        switch=mask_source.node.outputs["Box"],
        false=sampled_mask,
        true=box_mask,
    ).o.output
    g.PruneGrid.float(
        grid=g.Math.multiply(grid, mask_value).o.value,
    ).o.grid >> inside_mask
    g.PruneGrid.float(
        grid=g.Math.multiply(
            grid,
            g.BooleanMath.l_not(mask_value).o.boolean,
        ).o.value,
    ).o.grid >> outside_mask


def mask_grid_node_group():
    node_group = bpy.data.node_groups.get(GROUP_NAME)
    if node_group:
        return node_group

    with TreeBuilder.geometry(GROUP_NAME, arrange="simple") as tree:
        _build_mask_grid(tree)

    return tree.tree
