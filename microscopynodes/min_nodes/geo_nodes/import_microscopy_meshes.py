import bpy
from nodebpy import TreeBuilder, geometry as g
from nodebpy.builder import CustomGeometryGroup
from nodebpy.types import (
    InputBoolean,
    InputInteger,
    InputMatrix,
    InputObject,
    InputString,
)

from .nodeHolderBundleInputs import HolderBundleInputs


GROUP_NAME = "Import Microscopy Meshes"


class ImportMicroscopyMeshes(CustomGeometryGroup):
    _name = GROUP_NAME

    def __init__(
        self,
        holder: InputObject = None,
        include: InputBoolean = False,
        template_str: InputString = "",
        cache_dir: InputString = "",
        dataset_hash: InputString = "",
        scale: InputInteger = 0,
        resolution: InputInteger = 0,
        channel_ix: InputInteger = 0,
        original_path: InputString = "",
        channel_affine_matrix: InputMatrix = None,
    ):
        super().__init__(
            Holder=holder,
            Include=include,
            **{
                "template_str": template_str,
                "cache_dir": cache_dir,
                "dataset_hash": dataset_hash,
                "scale": scale,
                "resolution": resolution,
                "channel_ix": channel_ix,
                "original_path": original_path,
                "Channel Affine Matrix": channel_affine_matrix,
            },
        )

    def _build_group(self, tree):
        _build_import_microscopy_meshes(tree)


def _build_import_microscopy_meshes(tree):
    tree._arrange = "simple"

    tree.tree.is_modifier = True
    tree.tree.show_modifier_manage_panel = True

    holder = tree.inputs.object("Holder")
    include = tree.inputs.boolean("Include")
    template_str = tree.inputs.string("template_str")
    cache_dir = tree.inputs.string("cache_dir")
    dataset_hash = tree.inputs.string("dataset_hash")
    scale = tree.inputs.integer("scale")
    resolution = tree.inputs.integer("resolution")
    channel_ix = tree.inputs.integer("channel_ix")
    tree.inputs.string("original_path")
    channel_affine_matrix = tree.inputs.matrix("Channel Affine Matrix")
    geometry_output = tree.outputs.geometry("Geometry")

    frame = HolderBundleInputs(holder=holder).o.frame
    path = g.FormatString(
        format=template_str,
        items={
            "cache_dir": cache_dir,
            "dataset_hash": dataset_hash,
            "scale": scale,
            "resolution": resolution,
            "channel_ix": channel_ix,
            "t": frame,
        },
    ).o.string
    obj_path = g.JoinStrings(strings=(path, ".obj"), delimiter="").o.string
    csv_path = g.JoinStrings(strings=(path, ".csv"), delimiter="").o.string

    imported_instances = g.ImportOBJ(path=obj_path).o.instances
    imported_ids = g.ImportCSV(path=csv_path, delimiter=",").o.point_cloud

    foreach_in = tree.nodes.new("GeometryNodeForeachGeometryElementInput")
    foreach_out = tree.nodes.new("GeometryNodeForeachGeometryElementOutput")
    foreach_out.domain = "INSTANCE"
    foreach_out.generation_items.clear()
    foreach_out.generation_items.new("GEOMETRY", "Geometry").domain = "POINT"
    foreach_out.input_items.clear()
    foreach_out.main_items.clear()
    foreach_in.pair_with_output(foreach_out)
    foreach_in.inputs["Selection"].default_value = True
    tree.tree.links.new(imported_instances.socket, foreach_in.inputs[0])

    oid = g.SampleIndex.point.integer(
        geometry=imported_ids,
        value=g.NamedAttribute.integer(name="oid").o.attribute,
        index=foreach_in.outputs["Index"],
        clamp=False,
    ).o.value
    geometry_with_oid = g.StoreNamedAttribute.point.integer(
        geometry=foreach_in.outputs["Element"],
        name="oid",
        value=oid,
    ).o.geometry
    tree.tree.links.new(geometry_with_oid.socket, foreach_out.inputs[1])

    transformed = g.TransformGeometry(
        geometry=foreach_out.outputs[2],
        mode="Matrix",
        transform=channel_affine_matrix,
    ).o.geometry
    g.Switch.geometry(
        switch=include,
        true=transformed,
    ).o.output >> geometry_output


def import_microscopy_meshes_node_group():
    node_group = bpy.data.node_groups.get(GROUP_NAME)
    if node_group is not None:
        return node_group

    with TreeBuilder.geometry(GROUP_NAME, arrange="simple") as tree:
        _build_import_microscopy_meshes(tree)

    return tree.tree
