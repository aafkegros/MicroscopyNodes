import bpy
import numpy as np
from databpy import create_object

from .base import MiNObject
from ..handle_blender_structs.min_keys import min_keys

class Holder(MiNObject):
    min_type = min_keys.HOLDER
    SCENE_IMPORT_TRANSFORM_ATTRIBUTE = "scene import transform"

    def init_obj(self):
        self.object = create_object(
            vertices=np.zeros((1, 3), dtype=float),
            name=self.min_type.name.lower(),
            collection=bpy.context.collection,
        )
        self.object.name = self.min_type.name.lower()
        return self.object

    def set_settings(self, dataset_model):
        super().set_settings(dataset_model)
        for modifier in list(self.object.modifiers):
            self.object.modifiers.remove(modifier)
        self.object.hide_render = True
        self.object.display_type = 'WIRE'
        self.object.name = dataset_model.name
        self.object.rotation_euler = (0.0, 0.0, 0.0)

    def set_scene(self, scene_model):
        scene_world_scale = float(self.object[self.DATASET_INPUT_SCALE]) / float(scene_model.output_scale)
        dataset_size = self.dataset_extents * scene_world_scale
        scene_import_transform = np.asarray(scene_model.import_transform, dtype=float)

        self.store_named_attribute(
            np.asarray([scene_import_transform], dtype=float),
            self.SCENE_IMPORT_TRANSFORM_ATTRIBUTE,
        )
        previous_scene_import_offset = np.asarray(
            self.object.get(self.SCENE_IMPORT_OFFSET, (0.0, 0.0, 0.0)),
            dtype=float,
        )
        scene_import_offset = -scene_import_transform * dataset_size
        user_offset = np.asarray(self.object.location, dtype=float) - previous_scene_import_offset

        self.object.scale = (scene_world_scale,) * 3
        self.object.location = tuple(user_offset + scene_import_offset)

        super().set_scene(scene_model, scene_import_offset=scene_import_offset)
