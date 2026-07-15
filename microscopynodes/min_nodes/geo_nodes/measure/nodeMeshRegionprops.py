import bpy
from nodebpy import TreeBuilder, geometry as g
from nodebpy.builder import CustomGeometryGroup
from nodebpy.nodes.geometry.groups import PrincipalComponents
from nodebpy.types import InputGeometry


GROUP_NAME = "Mesh Regionprops"


class MeshRegionprops(CustomGeometryGroup):
    _name = GROUP_NAME

    def __init__(self, mesh: InputGeometry = None):
        super().__init__(Mesh=mesh)

    def _build_group(self, tree):
        _build_mesh_regionprops(tree)


def _build_mesh_regionprops(tree):
    tree._arrange = "simple"
    tree.tree.description = "Measure common regionprops-style values from a mesh"

    mesh = tree.inputs.geometry(
        "Mesh",
        "Closed, consistently oriented mesh to measure",
    )
    centroid = tree.outputs.vector("Centroid", description="Mean point position")
    bbox_min = tree.outputs.vector("BBox Min", description="Minimum bounding-box corner")
    bbox_max = tree.outputs.vector("BBox Max", description="Maximum bounding-box corner")
    bbox_extents = tree.outputs.vector(
        "BBox Extents",
        description="Bounding-box axis lengths",
    )
    bbox_center = tree.outputs.vector("BBox Center", description="Bounding-box center")
    surface_area = tree.outputs.float("Area", description="Total surface area")
    inferred_volume = tree.outputs.float(
        "Inferred Volume",
        description=(
            "Volume inferred from face normals; works well only for closed, "
            "consistently oriented meshes"
        ),
    )
    components = tree.outputs.vector(
        "Principal Components",
        description="Variance along the principal axes",
    )
    rotation = tree.outputs.rotation(
        "Principal Rotation",
        description="Principal-axis basis rotation",
    )
    longest = tree.outputs.vector(
        "Longest Axis",
        description="Principal axis with largest variance",
    )
    intermediate = tree.outputs.vector(
        "Intermediate Axis",
        description="Middle principal axis",
    )
    shortest = tree.outputs.vector(
        "Shortest Axis",
        description="Principal axis with smallest variance",
    )

    bbox = g.BoundingBox(geometry=mesh)
    measured_area = g.AttributeStatistic.face.float(
        geometry=mesh,
        attribute=g.FaceArea().o.area,
    ).o.sum
    volume_contribution = (
        g.Position().o.position.dot(g.Normal().o.normal) * g.FaceArea().o.area
    )
    measured_volume = (
        g.Math.absolute(
            g.AttributeStatistic.face.float(
                geometry=mesh,
                attribute=volume_contribution,
            ).o.sum
        ).o.value
        / 3.0
    )
    pca = PrincipalComponents(position=g.Position().o.position)

    g.AttributeStatistic.point.vector(
        geometry=mesh,
        attribute=g.Position().o.position,
    ).o.mean >> centroid
    bbox.o.min >> bbox_min
    bbox.o.max >> bbox_max
    extents = bbox.o.max - bbox.o.min
    extents >> bbox_extents
    ((bbox.o.min + bbox.o.max) * 0.5) >> bbox_center
    measured_area >> surface_area
    measured_volume >> inferred_volume
    pca.o.principal_components >> components
    pca.o.rotation >> rotation
    pca.o.longest_axis >> longest
    pca.o.intermediate_axis >> intermediate
    pca.o.shortest_axis >> shortest


def mesh_regionprops_node_group():
    node_group = bpy.data.node_groups.get(GROUP_NAME)
    if node_group is not None:
        return node_group

    with TreeBuilder.geometry(GROUP_NAME, arrange="simple") as tree:
        _build_mesh_regionprops(tree)

    return tree.tree
