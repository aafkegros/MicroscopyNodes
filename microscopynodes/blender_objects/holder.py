import bpy

from .base import MiNObject
from ..handle_blender_structs.min_keys import min_keys

class Holder(MiNObject):
    min_type = min_keys.HOLDER

    def init_obj(self):
        bpy.ops.object.empty_add(type="PLAIN_AXES")
        self.object = bpy.context.view_layer.objects.active
        self.object.name = self.min_type.name.lower()
        return self.object

    def set_settings(self, dataset_model):
        for modifier in list(self.object.modifiers):
            self.object.modifiers.remove(modifier)
        self.object.hide_render = True
        self.object.display_type = 'WIRE'
        self.object.name = dataset_model.name
        self.object.location = (0.0, 0.0, 0.0)
        self.object.rotation_euler = (0.0, 0.0, 0.0)
        self.object["_MiN_input_scale"] = float(dataset_model.channels[0].data.unit)

    def set_scene(self, scene_model):
        world_scale = float(self.object["_MiN_input_scale"]) / float(scene_model.output_scale)
        previous_world_scale = self.object.get("_MiN_world_scale_base")

        if previous_world_scale is None:
            self.object.scale = (world_scale,) * 3
        else:
            ratio = world_scale / float(previous_world_scale)
            self.object.scale = tuple(float(value) * ratio for value in self.object.scale)
            self.object.location = tuple(float(value) * ratio for value in self.object.location)

        self.object["_MiN_world_scale_base"] = float(world_scale)
        self.object["_MiN_output_scale"] = float(scene_model.output_scale)
