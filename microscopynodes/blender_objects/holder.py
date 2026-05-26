import bpy
import numpy as np

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
        self.object.scale = (float(dataset_model.scale),) * 3
        self.object["_MiN_world_scale_base"] = float(dataset_model.scale)
        self.object["_MiN_data_unit"] = float(dataset_model.channels[0].data.unit)
        default_axis_unit_scale = float(dataset_model.axis_unit_scale)
        if np.isclose(default_axis_unit_scale, 1.0):
            default_axis_unit_scale = float(dataset_model.channels[0].data.affine[0][0])
        self.object["_MiN_default_axis_unit_scale"] = default_axis_unit_scale
