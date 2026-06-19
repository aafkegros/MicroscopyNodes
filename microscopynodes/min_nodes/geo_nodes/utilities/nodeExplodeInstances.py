import bpy
from nodebpy import TreeBuilder, geometry as g
from nodebpy.builder import CustomGeometryGroup
from nodebpy.types import InputFloat, InputGeometry, InputMenu, InputObject


GROUP_NAME = "Explode Instances"


class ExplodeInstances(CustomGeometryGroup):
    _name = GROUP_NAME

    def __init__(
        self,
        instances: InputGeometry = None,
        amount: InputFloat = None,
        origin: InputMenu = "Centroid",
        origin_object: InputObject = None,
    ):
        super().__init__(
            Instances=instances,
            Amount=amount,
            Origin=origin,
            **{"Origin Object": origin_object},
        )

    def _build_group(self, tree):
        _build_explode_instances(tree)


def _build_explode_instances(tree):
    tree._arrange = "simple"
    tree.tree.description = "Move instances away from a shared origin"

    instances = tree.inputs.geometry(
        "Instances",
        "Instance geometry to spread apart",
    )
    amount = tree.inputs.float(
        "Amount",
        description="Distance to move each instance away from the instance center",
        subtype="DISTANCE",
    )
    origin = tree.inputs.menu(
        "Origin",
        default_value="Centroid",
        description="Point that instances move away from",
        optional_label=True,
    )
    origin_object = tree.inputs.object(
        "Origin Object",
        description="Object or empty used as the explosion origin",
        optional_label=True,
    )
    output = tree.outputs.geometry("Instances", description="Exploded instances")

    instance_bounds = g.InstanceBounds(use_radius=False)
    instance_position = (instance_bounds.o.min + instance_bounds.o.max) * 0.5
    centroid = g.AttributeStatistic.point.vector(
        geometry=g.RealizeInstances(geometry=instances).o.geometry,
        attribute=g.Position().o.position,
    ).o.mean
    center = g.MenuSwitch.vector(
        menu=origin,
        items={
            "Centroid": centroid,
            "Object": g.ObjectInfo(object=origin_object).o.location,
        },
    ).o.output
    direction = g.VectorMath.normalize(
        vector=instance_position - center,
    ).o.vector
    offset = g.VectorMath.scale(vector=direction, scale=amount).o.vector

    g.TranslateInstances(
        instances=instances,
        translation=offset,
        local_space=False,
    ).o.instances >> output


def explode_instances_node_group():
    node_group = bpy.data.node_groups.get(GROUP_NAME)
    if node_group is not None:
        return node_group

    with TreeBuilder.geometry(GROUP_NAME, arrange="simple") as tree:
        _build_explode_instances(tree)

    return tree.tree
