import bpy
from nodebpy import TreeBuilder, geometry as g
from nodebpy.builder import CustomGeometryGroup
from nodebpy.types import InputGeometry


GROUP_NAME = "Align Text To Active Camera"


class AlignTextToActiveCamera(CustomGeometryGroup):
    _name = GROUP_NAME

    def __init__(self, geometry: InputGeometry = None):
        super().__init__(Geometry=geometry)

    def _build_group(self, tree):
        _build_align_text_to_active_camera(tree)


def _build_align_text_to_active_camera(tree):
    geometry = tree.inputs.geometry("Geometry")
    output = tree.outputs.geometry("Geometry")

    camera_rotation = g.ObjectInfo(
        object=g.ActiveCamera().o.active_camera,
        transform_space="RELATIVE",
    ).o.rotation
    g.TransformGeometry(
        geometry=geometry,
        rotation=camera_rotation,
    ).o.geometry >> output


def align_text_to_active_camera_node_group():
    node_group = bpy.data.node_groups.get(GROUP_NAME)
    if node_group is not None:
        return node_group

    with TreeBuilder.geometry(GROUP_NAME) as tree:
        _build_align_text_to_active_camera(tree)

    return tree.tree
