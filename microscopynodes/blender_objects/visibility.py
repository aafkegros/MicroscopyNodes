import bpy
import numpy as np
from nodebpy import TreeBuilder, geometry as g

from .base import MiNObject
from ..min_nodes.geo_nodes.nodeActiveGridPositions import ActiveGridPositions


class VisibilityMaskObject(MiNObject):
    min_type = None

    def __init__(self, obj=None):
        self.visibility_node_group = None
        self.object_info_node = None
        self.sample_node = None
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
        self.sample_node = nodes.get("Active Channel 0")

    def read_points(self):
        point_cloud = self._evaluated_point_cloud()
        indices = self._read_vector_attribute(point_cloud, "ix").astype(int)
        if len(indices) == 0:
            return np.empty((0, 0, 0), dtype=bool)

        values = self._read_boolean_attribute(point_cloud, "value")
        mask = np.zeros(tuple(indices.max(axis=0) + 1), dtype=bool)
        mask[tuple(indices.T)] = values
        return mask

    def _evaluated_point_cloud(self):
        bpy.context.view_layer.update()
        depsgraph = bpy.context.evaluated_depsgraph_get()
        return self.object.evaluated_get(depsgraph).data

    def _read_vector_attribute(self, point_cloud, name):
        if len(point_cloud.points) == 0:
            return np.empty((0, 3), dtype=float)

        values = np.empty(len(point_cloud.points) * 3, dtype=float)
        point_cloud.attributes[name].data.foreach_get("vector", values)
        return values.reshape((-1, 3))

    def _read_boolean_attribute(self, point_cloud, name):
        values = np.empty(len(point_cloud.points), dtype=bool)
        point_cloud.attributes[name].data.foreach_get("value", values)
        return values

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

    def _node_group(self):
        with TreeBuilder.geometry("visibility mask") as tree:
            tree.tree.show_modifier_manage_panel = True
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

            sample = ActiveGridPositions(grid=channel_grid.o.grid)
            sample.node.name = "Active Channel 0"
            sample.node.location = (120, 0)
            self.sample_node = sample.node

            sample.o.points >> geometry

        return tree.tree
