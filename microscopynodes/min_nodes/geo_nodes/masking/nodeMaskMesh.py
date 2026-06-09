import bpy
from nodebpy import TreeBuilder, geometry as g
from nodebpy.builder import CustomGeometryGroup
from nodebpy.types import (
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
    ):
        super().__init__(
            **{
                "Mesh": mesh,
                "With": with_,
                "Object": object,
                "Collection": collection,
                "Mask": mask,
            }
        )

    def _build_group(self, tree):
        _build_mask_mesh(tree)


def _build_mask_mesh(tree):
    tree._arrange = "simple"

    tree.tree.show_modifier_manage_panel = True

    mesh = tree.inputs.geometry("Mesh")
    with_ = tree.inputs.menu("With", "Object")
    object = tree.inputs.object("Object")
    collection = tree.inputs.collection("Collection", optional_label=True)
    mask = tree.inputs.geometry("Mask")
    inside_mask = tree.outputs.geometry("Inside Mask")
    outside_mask = tree.outputs.geometry("Outside Mask")

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
    masked_with_mesh = g.MeshBoolean.intersect(
        items=[realized_mesh, realized_mask],
    ).node.outputs["Mesh"]
    unmasked_with_mesh = g.MeshBoolean.difference(
        mesh_1=realized_mesh,
        items=[realized_mask],
    ).node.outputs["Mesh"]

    inside_box = ClipFieldToBox(box_object=object).o.clipped_field
    masked_with_box = g.DeleteGeometry(
        geometry=realized_mesh,
        selection=g.BooleanMath.l_not(inside_box).o.boolean,
    ).o.geometry
    unmasked_with_box = g.DeleteGeometry(
        geometry=realized_mesh,
        selection=inside_box,
    ).o.geometry

    g.Switch.geometry(
        switch=mask_source.node.outputs["Box"],
        false=masked_with_mesh,
        true=masked_with_box,
    ).o.output >> inside_mask
    g.Switch.geometry(
        switch=mask_source.node.outputs["Box"],
        false=unmasked_with_mesh,
        true=unmasked_with_box,
    ).o.output >> outside_mask


def mask_mesh_node_group():
    node_group = bpy.data.node_groups.get(GROUP_NAME)
    if node_group:
        return node_group

    with TreeBuilder.geometry(GROUP_NAME, arrange="simple") as tree:
        _build_mask_mesh(tree)

    return tree.tree
