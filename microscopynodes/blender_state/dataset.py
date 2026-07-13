import bpy

from ..blender_objects.factories import MinObjectFactory
from ..handle_blender_structs.min_keys import min_keys
from ..handle_blender_structs.node_handling import get_min_gn
from .scene import Scene


class Dataset():
    def __init__(self, holder=None, dataset_model=None, scene=None):
        self.scene = scene if isinstance(scene, Scene) else Scene(scene=scene)
        self.holder = None
        self.axes = None
        self.slicecube = None
        self.volume = None
        self.surface = None
        self.labelmask = None

        if holder is not None:
            from ..handle_blender_structs.dependent_props import valid_reload_object
            holder = holder if valid_reload_object(holder) else None
        if holder is not None:
            self.initialize_from_previous(holder)
        if dataset_model is not None:
            self.set_state(dataset_model)

    def initialize_from_previous(self, holder_obj):
        # TODO sets objects as MiN objects, right now it is just pointers to blender objects
        self.holder = MinObjectFactory(min_keys.HOLDER, obj=holder_obj)
        for child in holder_obj.children:
            min_gn = get_min_gn(child)
            if min_gn is None:
                continue
            key = next((k for k in min_keys if k.name.lower() in min_gn.name.lower()), None)
            if key:
                min_obj = MinObjectFactory(key, obj=child)
                setattr(self, key.name.lower(), min_obj)
        return

    def set_state(self, dataset_model, update_data=True, update_settings=True):
        if not dataset_model.local_files_exist and update_data:
            dataset_model.make_local_files()
        self.scene.resolve_auto_import_scale(dataset_model)

        required_objects = {min_keys.HOLDER, min_keys.AXES, min_keys.SLICECUBE}
        for ch in dataset_model.channels:
            if ch.viz.volume:
                required_objects.add(min_keys.VOLUME)
            if ch.viz.surface:
                required_objects.add(min_keys.SURFACE)
            if ch.viz.labelmask:
                required_objects.add(min_keys.LABELMASK)

        for min_key in min_keys:
            min_obj = getattr(self, min_key.name.lower())
            if min_key not in required_objects and min_obj is None:
                continue
            initialize = min_obj is None
            if min_obj is None:
                min_obj = MinObjectFactory(min_key)
                setattr(self, min_key.name.lower(), min_obj)
            if update_data or initialize:
                min_obj.set_data(dataset_model)
            if update_settings:
                min_obj.set_settings(dataset_model)

        if update_settings:
            self.ensure_links_of_objects(dataset_model)
            self.scene.update_dataset_scale(self, dataset_model)
        if self.holder is not None:
            bpy.context.scene.MiN_reload = self.holder.object
        return

    def ensure_links_of_objects(self, dataset_model):
        if self.holder is None:
            return

        for min_key in (min_keys.AXES, min_keys.SLICECUBE, min_keys.VOLUME, min_keys.SURFACE, min_keys.LABELMASK):
            min_obj = getattr(self, min_key.name.lower())
            if min_obj is not None:
                min_obj.object.parent = self.holder.object
                min_obj.object.matrix_parent_inverse.identity()

        for min_obj in (self.axes, self.slicecube, self.volume, self.surface, self.labelmask):
            if min_obj is not None:
                min_obj.set_holder(self.holder.object)

        if self.slicecube is not None:
            for min_obj in (self.volume, self.surface, self.labelmask):
                if min_obj is None:
                    continue
                for ch in dataset_model.channels:
                    if getattr(ch.viz, min_obj.min_type.name.lower(), False):
                        min_obj.set_parent_and_slicer(self.holder.object, self.slicecube.object, ch)

        return
