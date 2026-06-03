import bpy
from nodebpy import TreeBuilder, geometry as g

from .base import MiNObject
from ..min_nodes.geo_nodes.nodeSubsample import SubsampledActiveGridPositions


class VisibilityMaskObject(MiNObject):
    min_type = None
    default_resolution = (20, 20, 10)

    def __init__(self, obj=None):
        self.visibility_node_group = None
        self.object_info_node = None
        self.sample_node = None
        self.resolution = self.default_resolution
        super().__init__(obj)
        if obj is not None:
            self._load_existing_nodes()

    def init_obj(self):
        pointcloud = bpy.data.pointclouds.new("visibility mask")
        self.object = bpy.data.objects.new("visibility mask", pointcloud)
        bpy.context.collection.objects.link(self.object)

        self.visibility_node_group = self._node_group()
        modifier = self.object.modifiers.new("[Microscopy Nodes visibility]", "NODES")
        modifier.node_group = self.visibility_node_group
        return self.object

    def _load_existing_nodes(self):
        modifier = next(
            (mod for mod in self.object.modifiers if mod.type == "NODES" and mod.node_group is not None),
            None,
        )
        if modifier is None:
            return
        self.visibility_node_group = modifier.node_group
        nodes = self.visibility_node_group.nodes
        self.object_info_node = nodes.get("Dataset Volume")
        self.sample_node = nodes.get("Subsample Channel 0")

    def read_points(self):
        bpy.context.view_layer.update()
        depsgraph = bpy.context.evaluated_depsgraph_get()
        evaluated_object = self.object.evaluated_get(depsgraph)
        point_cloud = evaluated_object.data
        points = point_cloud.points
        if len(points) == 0:
            return []

        locations = [0.0] * (len(points) * 3)
        try:
            points.foreach_get("co", locations)
        except Exception:
            point_cloud.attributes["position"].data.foreach_get("vector", locations)
        return [
            tuple(float(value) for value in locations[ix:ix + 3])
            for ix in range(0, len(locations), 3)
        ]

    def read_normalized_points(self):
        bpy.context.view_layer.update()
        depsgraph = bpy.context.evaluated_depsgraph_get()
        evaluated_object = self.object.evaluated_get(depsgraph)
        point_cloud = evaluated_object.data
        points = point_cloud.points
        if len(points) == 0:
            return []

        locations = [0.0] * (len(points) * 3)
        point_cloud.attributes["normalized position"].data.foreach_get("vector", locations)
        return [
            tuple(float(value) for value in locations[ix:ix + 3])
            for ix in range(0, len(locations), 3)
        ]

    def link_volume(self, volume_object):
        self.object_info_node.inputs["Object"].default_value = volume_object.object
        return

    def link_dataset(self, dataset):
        if dataset.volume is not None:
            self.link_volume(dataset.volume)
        if dataset.surface is not None:
            self.link_surface(dataset.surface)
        if dataset.labelmask is not None:
            self.link_labelmask(dataset.labelmask)
        return

    def link_surface(self, surface_object):
        return

    def link_labelmask(self, labelmask_object):
        return

    def read_voxel_extents(self):
        bpy.context.view_layer.update()
        depsgraph = bpy.context.evaluated_depsgraph_get()
        evaluated_object = self.object.evaluated_get(depsgraph)
        point_cloud = evaluated_object.data
        if len(point_cloud.points) == 0:
            return tuple(1.0 / value for value in self.resolution)

        extents = [0.0] * (len(point_cloud.points) * 3)
        point_cloud.attributes["voxel extents"].data.foreach_get("vector", extents)
        return tuple(float(value) for value in extents[:3])

    def _node_group(self):
        resolution_x, resolution_y, resolution_z = self.default_resolution
        with TreeBuilder.geometry("visibility mask") as tree:
            tree.tree.show_modifier_manage_panel = True
            resolution_x = tree.inputs.integer("Resolution X", resolution_x, min_value=1)
            resolution_y = tree.inputs.integer("Resolution Y", resolution_y, min_value=1)
            resolution_z = tree.inputs.integer("Resolution Z", resolution_z, min_value=1)
            geometry = tree.outputs.geometry("Geometry")

            object_info = g.ObjectInfo(transform_space="RELATIVE")
            object_info.node.name = "Dataset Volume"
            object_info.node.location = (-600, 80)
            self.object_info_node = object_info.node

            channel_grid = g.GetNamedGrid.float(
                volume=object_info.o.geometry,
                name="Channel 0",
            )
            channel_grid.node.name = "Channel 0"
            channel_grid.node.location = (-300, 80)

            sample = SubsampledActiveGridPositions(
                grid=channel_grid.o.grid,
                resolution_x=resolution_x,
                resolution_y=resolution_y,
                resolution_z=resolution_z,
            )
            sample.node.name = "Subsample Channel 0"
            sample.node.location = (120, 0)
            self.sample_node = sample.node

            voxel_extents = g.CombineXYZ(
                x=g.Math.divide(1.0, resolution_x).o.value,
                y=g.Math.divide(1.0, resolution_y).o.value,
                z=g.Math.divide(1.0, resolution_z).o.value,
            )
            voxel_extents.node.name = "Voxel Extents"
            voxel_extents.node.location = (360, -160)

            g.StoreNamedAttribute.point.vector(
                geometry=sample.node.outputs["Points"],
                name="voxel extents",
                value=voxel_extents.o.vector,
            ).o.geometry >> geometry

        return tree.tree
