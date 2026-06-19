import platform

import bpy

from ..data_model import SceneModel


class Scene():
    # wraps the blender scene and can hold Microscopy Nodes Datasets
    # This is essentially a placeholder for a more developed Scene Object that actually knows of its data
    def __init__(self, scene=None, overwrite_background_color=False, overwrite_render_settings=False):
        self.scene = scene or bpy.context.scene # TODO catch uninitialized scene
        self.set_auto_scale_if_empty()

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

    def set_auto_scale_if_empty(self):
        from ..handle_blender_structs.dependent_props import poll_holder
        from ..handle_blender_structs.units import AUTO_IMPORT_SCALE

        has_holder = any(poll_holder(self.scene, obj) for obj in self.scene.objects)
        if not has_holder:
            self.scene.MiN_import_scale = AUTO_IMPORT_SCALE

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
            import_transform=self.scene.MiN_import_loc,
        )

    def resolve_auto_import_scale(self, dataset_model):
        from ..handle_blender_structs.units import AUTO_IMPORT_SCALE, import_scale_for_extent

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
    scn.cycles.volume_biased = True
    scn.cycles.transparent_max_bounces = 40
    scn.cycles.use_denoising = False

    set_workspace_viewport_scene_world()
    return


def set_workspace_viewport_scene_world(workspace_name="Shading"):
    ws = bpy.data.workspaces.get(workspace_name)
    if ws is None:
        raise RuntimeError(f"No workspace named {workspace_name!r}")

    for screen in ws.screens:
        for area in screen.areas:
            if area.type != "VIEW_3D":
                continue

            for space in area.spaces:
                if space.type != "VIEW_3D":
                    continue

                space.shading.type = "RENDERED"
                space.shading.use_scene_world_render = True
                space.shading.use_scene_lights_render = True

                space.shading.use_scene_world = True
                space.shading.use_scene_lights = True

            area.tag_redraw()
