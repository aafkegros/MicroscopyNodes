import bpy
from nodebpy import TreeBuilder, geometry as g
from nodebpy.builder import CustomGeometryGroup
from nodebpy.types import (
    InputBoolean,
    InputCollection,
    InputGeometry,
    InputMenu,
    InputObject,
)

from .nodeMaskBoxField import ClipFieldToBox


GROUP_NAME = "Mask Mesh"


class MaskMesh(CustomGeometryGroup):
    _name = GROUP_NAME

    def __init__(
        self,
        mesh: InputGeometry = None,
        with_: InputMenu = "Object",
        object: InputObject = None,
        collection: InputCollection = None,
        mask: InputGeometry = None,
        invert: InputBoolean = False,
    ):
        super().__init__(
            **{
                "Mesh": mesh,
                "With": with_,
                "Object": object,
                "Collection": collection,
                "Mask": mask,
                "Invert": invert,
            }
        )

    def _build_group(self, tree):
        _build_mask_mesh(tree)


def _build_mask_mesh(tree):
    tree.tree.show_modifier_manage_panel = True

    mesh = tree.inputs.geometry("Mesh")
    with_ = tree.inputs.menu("With", "Object")
    object = tree.inputs.object("Object")
    collection = tree.inputs.collection("Collection", optional_label=True)
    mask = tree.inputs.geometry("Mask")
    invert = tree.inputs.boolean("Invert")
    masked_mesh = tree.outputs.geometry("Masked Mesh")

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
            "Mesh": mask,
            "Box": object_geometry,
        },
    )

    realized_mesh = g.RealizeInstances(mesh).o.geometry
    realized_mask = g.RealizeInstances(mask_source.o.output).o.geometry
    masked_with_mesh = g.Switch.geometry(
        switch=invert,
        true=g.MeshBoolean.difference(
            mesh_1=realized_mesh,
            items=[realized_mask],
        ).node.outputs["Mesh"],
        false=g.MeshBoolean.intersect(
            items=[realized_mesh, realized_mask],
        ).node.outputs["Mesh"],
    ).o.output

    inside_box = ClipFieldToBox(box_object=object).o.clipped_field
    masked_with_box = g.DeleteGeometry(
        geometry=realized_mesh,
        selection=g.Switch.boolean(
            switch=invert,
            false=g.BooleanMath.l_not(inside_box).o.boolean,
            true=inside_box,
        ).o.output,
    ).o.geometry

    g.Switch.geometry(
        switch=mask_source.node.outputs["Box"],
        false=masked_with_mesh,
        true=masked_with_box,
    ).o.output >> masked_mesh


def mask_mesh_node_group():
    node_group = bpy.data.node_groups.get(GROUP_NAME)
    if node_group:
        return node_group

    with TreeBuilder.geometry(GROUP_NAME) as tree:
        _build_mask_mesh(tree)

    return tree.tree
