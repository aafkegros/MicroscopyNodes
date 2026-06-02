import bpy
import platform

from .handle_blender_structs.keyframe_handling import ensure_dataset_frame_driver, ensure_dataset_frame_property
from .handle_blender_structs.node_handling import get_min_gn
from .handle_blender_structs.min_keys import min_keys
from .blender_objects.factories import MinObjectFactory
from .blender_objects.visibility import VisibilityMaskObject
from .data_model import SceneModel

class Scene():
    # wraps the blender scene and can hold Microscopy Nodes Datasets
    # This is essentially a placeholder for a more developed Scene Object that actually knows of its data
    def __init__(self, scene=None, overwrite_background_color=False, overwrite_render_settings=False):
        self.scene = scene or bpy.context.scene # TODO catch uninitialized scene

        if overwrite_background_color:
            set_background_color()
        if overwrite_render_settings:
            self.set_render_settings()

    @classmethod
    def from_blender_ui(cls, context=None):
        context = context or bpy.context
        scene = context.scene
        return cls(
            scene=scene,
            overwrite_background_color=scene.MiN_overwrite_background_color,
            overwrite_render_settings=scene.MiN_overwrite_render_settings,
        )
        
    def set_background_color(self, bgcol):
        try:
            self.scene.world.node_tree.nodes["Background"].inputs[0].default_value = bgcol
        except:
            pass
    
    def set_render_settings(self):
        set_render_settings()
        return

    @property
    def import_scale(self):
        return self.scene.MiN_import_scale

    @property
    def output_scale(self):
        return SceneModel.output_scale_value(self.import_scale)

    @property
    def scene_model(self):
        return SceneModel(
            output_scale=self.import_scale,
        )

    def resolve_auto_import_scale(self, dataset_model):
        from .handle_blender_structs.units import AUTO_IMPORT_SCALE, import_scale_for_extent

        if self.scene.MiN_import_scale != AUTO_IMPORT_SCALE:
            return
        _, _, extent = dataset_model.intermediate_bbox
        input_extent_meters = float(max(extent)) * float(dataset_model.channels[0].data.unit)
        self.scene.MiN_import_scale = import_scale_for_extent(input_extent_meters)

    def update_dataset_scale(self, dataset, dataset_model):
        self.resolve_auto_import_scale(dataset_model)
        scene_model = self.scene_model
        if dataset.holder is not None:
            dataset.holder.set_scene(scene_model)
        if dataset.axes is not None:
            dataset.axes.set_scene(scene_model)

class Dataset():
    def __init__(self, holder=None, dataset_model=None, scene=None):
        self.scene = scene if isinstance(scene, Scene) else Scene(scene=scene)
        self.holder = None
        self.axes = None
        self.slicecube = None
        self.volume = None
        self.surface = None
        self.labelmask = None
        self.visibility = None

        if holder is not None:
            from .handle_blender_structs.dependent_props import valid_reload_object
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
            result = dataset_model.make_local_files()
            if not result["ok"]:
                raise RuntimeError(result["error"])

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
            if min_obj is None:
                min_obj = MinObjectFactory(min_key)
                setattr(self, min_key.name.lower(), min_obj)
            if update_data:
                min_obj.set_data(dataset_model)
            if update_settings:
                min_obj.set_settings(dataset_model)
        self.ensure_links_of_objects(dataset_model)
        if update_settings:
            self.scene.update_dataset_scale(self, dataset_model)
        if self.holder is not None:
            bpy.context.scene.MiN_reload = self.holder.object
        return    
    
    def ensure_links_of_objects(self, dataset_model):
        if self.holder is None:
            return

        ensure_dataset_frame_property(self.holder.object, dataset_model)

        for min_key in (min_keys.AXES, min_keys.SLICECUBE, min_keys.VOLUME, min_keys.SURFACE, min_keys.LABELMASK):
            min_obj = getattr(self, min_key.name.lower())
            if min_obj is not None:
                min_obj.object.parent = self.holder.object
                min_obj.object.matrix_parent_inverse.identity()

        if self.slicecube is not None:
            for min_obj in (self.volume, self.surface, self.labelmask):
                if min_obj is None:
                    continue
                for ch in dataset_model.channels:
                    if getattr(ch.viz, min_obj.min_type.name.lower(), False):
                        min_obj.set_parent_and_slicer(self.holder.object, self.slicecube.object, ch)

        for min_obj in (self.volume, self.surface, self.labelmask):
            if min_obj is not None:
                ensure_dataset_frame_driver(self.holder.object, min_obj)
        return

    def ensure_visibility_mask(self):
        if self.visibility is None:
            self.visibility = VisibilityMaskObject()
        if self.holder is not None:
            self.visibility.object.parent = self.holder.object
            self.visibility.object.matrix_parent_inverse.identity()
        self.visibility.link_dataset(self)
        return



def set_background_color():
    bgcol = (0.2,0.2,0.2, 1)
    emitting = [ch.emission for ch in bpy.context.scene.MiN_channelList if (ch.surface or ch.volume) or ch.labelmask]
    if all(emitting):
        bgcol = (0, 0, 0, 1)
    if all([(not emit) for emit in emitting]):
        bgcol = (1, 1, 1, 1)
    try:
        bpy.context.scene.world.node_tree.nodes["Background"].inputs[0].default_value = bgcol
    except:
        pass
    return


def set_render_settings():
    scn = bpy.context.scene
    scn.render.engine = 'CYCLES'

    eevee = getattr(scn, "eevee", None)
    if eevee is not None:
        volumetric_tile_size = '2' if platform.system() == "Windows" else '1' # windows can be buggy with eevee and large window size

        for attr, value in {
            "volumetric_tile_size": volumetric_tile_size,
            "volumetric_end": 300,
            "taa_samples": 64,
        }.items():
            if hasattr(eevee, attr):
                setattr(eevee, attr, value)

    scn.view_settings.view_transform = 'Standard'

    scn.cycles.transparent_max_bounces = 40
    scn.cycles.use_denoising = False

    set_viewport_scene_world()
    return


def set_viewport_scene_world():
    screen = getattr(bpy.context, "screen", None)
    if screen is None:
        return
    for area in screen.areas:
        if area.type != 'VIEW_3D':
            continue
        for space in area.spaces:
            if space.type != 'VIEW_3D':
                continue
            shading = space.shading
            for attr in ("use_scene_world", "use_scene_world_render"):
                if hasattr(shading, attr):
                    setattr(shading, attr, True)
