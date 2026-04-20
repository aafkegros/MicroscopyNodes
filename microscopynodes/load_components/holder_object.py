from .base import *
from pathlib import Path
from ..handle_blender_structs.props import min_keys

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
