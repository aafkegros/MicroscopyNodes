import bpy

from .base import MiNObject
from ..min_nodes.geo_nodes.nodeSubsample import subsampled_active_grid_positions_node_group


class VisibilityMaskObject(MiNObject):
    default_resolution = (20, 20, 10)

    def __init__(self):
        self.visibility_node_group = None
        self.object_info_node = None
        self.sample_node = None
        self.voxel_extents_node = None
        self.resolution = self.default_resolution
        super().__init__()

    def init_obj(self):
        pointcloud = bpy.data.pointclouds.new("visibility mask")
        self.object = bpy.data.objects.new("visibility mask", pointcloud)
        bpy.context.collection.objects.link(self.object)

        self.visibility_node_group = self._node_group()
        modifier = self.object.modifiers.new("visibility mask", "NODES")
        modifier.node_group = self.visibility_node_group
        return self.object

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

    def set_resolution(self, resolution):
        if isinstance(resolution, int):
            resolution_x = resolution_y = resolution_z = resolution
        else:
            resolution_x, resolution_y, resolution_z = (int(value) for value in resolution)
        self.resolution = (resolution_x, resolution_y, resolution_z)
        self.sample_node.inputs["Resolution X"].default_value = resolution_x
        self.sample_node.inputs["Resolution Y"].default_value = resolution_y
        self.sample_node.inputs["Resolution Z"].default_value = resolution_z
        self.voxel_extents_node.inputs["X"].default_value = 1.0 / resolution_x
        self.voxel_extents_node.inputs["Y"].default_value = 1.0 / resolution_y
        self.voxel_extents_node.inputs["Z"].default_value = 1.0 / resolution_z

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
        node_group = bpy.data.node_groups.new("visibility mask", "GeometryNodeTree")
        node_group.interface.new_socket(
            name="Geometry",
            in_out="OUTPUT",
            socket_type="NodeSocketGeometry",
        )

        nodes = node_group.nodes
        links = node_group.links

        output = nodes.new("NodeGroupOutput")
        output.name = "Group Output"
        output.is_active_output = True
        output.location = (600, 0)

        object_info = nodes.new("GeometryNodeObjectInfo")
        object_info.name = "Dataset Volume"
        object_info.location = (-600, 80)
        if hasattr(object_info, "transform_space"):
            object_info.transform_space = "RELATIVE"
        self.object_info_node = object_info

        channel_grid = nodes.new("GeometryNodeGetNamedGrid")
        channel_grid.name = "Channel 0"
        channel_grid.data_type = "FLOAT"
        channel_grid.inputs["Name"].default_value = "Channel 0"
        channel_grid.location = (-300, 80)

        sample = nodes.new("GeometryNodeGroup")
        sample.name = "Subsample Channel 0"
        sample.node_tree = subsampled_active_grid_positions_node_group()
        sample.location = (120, 0)
        self.sample_node = sample

        voxel_extents = nodes.new("ShaderNodeCombineXYZ")
        voxel_extents.name = "Voxel Extents"
        voxel_extents.location = (360, -160)
        self.voxel_extents_node = voxel_extents
        self.set_resolution(self.default_resolution)

        store_voxel_extents = nodes.new("GeometryNodeStoreNamedAttribute")
        store_voxel_extents.name = "Store Voxel Extents"
        store_voxel_extents.data_type = "FLOAT_VECTOR"
        store_voxel_extents.domain = "POINT"
        store_voxel_extents.location = (360, 0)
        store_voxel_extents.inputs["Name"].default_value = "voxel extents"

        links.new(object_info.outputs["Geometry"], channel_grid.inputs["Volume"])
        links.new(channel_grid.outputs["Grid"], sample.inputs["Grid"])
        links.new(sample.outputs["Geometry"], store_voxel_extents.inputs["Geometry"])
        links.new(voxel_extents.outputs["Vector"], store_voxel_extents.inputs["Value"])
        links.new(store_voxel_extents.outputs["Geometry"], output.inputs["Geometry"])
        return node_group
