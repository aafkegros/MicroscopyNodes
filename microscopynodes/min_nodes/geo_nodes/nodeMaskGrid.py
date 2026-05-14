import bpy
from nodebpy import TreeBuilder, geometry as g
from nodebpy.builder import CustomGeometryGroup
from nodebpy.types import (
    InputBoolean,
    InputCollection,
    InputFloat,
    InputGeometry,
    InputMenu,
    InputObject,
)

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
        mask_resolution: InputFloat = 0.3,
        mask: InputFloat = 0.0,
        invert: InputBoolean = False,
    ):
        super().__init__(
            **{
                "Grid": grid,
                "With": with_,
                "Object": object,
                "Collection": collection,
                "Mesh": mesh,
                "Mask Resolution": mask_resolution,
                "Mask": mask,
                "Invert": invert,
            }
        )

    def _build_group(self, tree):
        _build_mask_grid(tree)


def _build_mask_grid(tree):
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
    invert = tree.inputs.boolean("Invert")
    masked_grid = tree.outputs.float("Masked Grid")

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

    volume_grid = g.GetNamedGrid.float(
        volume=g.MeshToVolume(
            mesh=realized,
            resolution_mode="Size",
            voxel_size=mask_resolution,
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
    mask_factor = g.Switch.float(
        switch=invert,
        false=mask_value,
        true=g.BooleanMath.l_not(mask_value).o.boolean,
    ).o.output

    g.PruneGrid.float(
        grid=g.Math.multiply(grid, mask_factor).o.value,
    ).o.grid >> masked_grid


def mask_grid_node_group():
    node_group = bpy.data.node_groups.get(GROUP_NAME)
    if node_group:
        return node_group

    with TreeBuilder.geometry(GROUP_NAME) as tree:
        _build_mask_grid(tree)

    return tree.tree
