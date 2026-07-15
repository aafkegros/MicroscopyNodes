import bpy
import numpy as np
from bpy.types import Operator

from ....data_model import ChannelDataModel, ChannelModel, ChannelVizModel
from ....handle_blender_structs.min_keys import min_keys


def _object_type(obj):
    for modifier in obj.modifiers:
        if modifier.type != "NODES" or "Microscopy Nodes" not in modifier.name:
            continue
        return next(
            (
                key
                for key in (min_keys.VOLUME, min_keys.SURFACE, min_keys.LABELMASK)
                if key.name.lower() in modifier.name.lower()
            ),
            None,
        )
    return None


def _next_channel_index(material):
    indices = [
        int(node.name.removeprefix("[frame_ch_id").removesuffix("]"))
        for node in material.node_tree.nodes
        if node.name.startswith("[frame_ch_id") and node.name.endswith("]")
    ]
    return max(indices, default=-1) + 1


def _channel_model(channel_index, object_type):
    name = f"Channel {channel_index}"
    channel = ChannelModel(
        cache_path="",
        data=ChannelDataModel(
            dataset_resolution=0,
            ix=channel_index,
            axes_order="xyz",
            unit=1.0,
            source="empty channel",
        ),
        viz=ChannelVizModel(
            ix=channel_index,
            name=name,
            emission=True,
        ),
    )
    channel.files_for(object_type).metadata = {
        "histogram": np.ones(2, dtype=float),
        "threshold": 0.0,
        "max": 1,
    }
    return channel


class MIN_OT_Add_Empty_Channel(Operator):
    """Add an empty channel shader to the active Microscopy Nodes object."""

    bl_idname = "microscopynodes.add_empty_channel"
    bl_label = "Add Empty Channel"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        from ....blender_objects.factories import MinObjectFactory

        obj = context.object
        object_type = _object_type(obj) if obj is not None else None
        if object_type is None:
            self.report({"ERROR"}, "Select a volume, surface, or labelmask object")
            return {"CANCELLED"}

        min_object = MinObjectFactory(object_type, obj=obj)
        material = min_object.add_material(None)
        if material.node_tree.nodes.get("Add Shaders") is None:
            min_object.init_shader(material)

        channel_index = _next_channel_index(material)
        min_object.shader_count = max(min_object.shader_count, channel_index + 1)
        min_object.ensure_channel_capacity()
        channel = _channel_model(channel_index, object_type)
        min_object.init_channel_shader(material, channel)
        min_object.update_material(material, channel)
        return {"FINISHED"}
