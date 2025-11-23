import bpy
from pathlib import Path
import numpy as np

from .handle_blender_structs import *
from .handle_blender_structs import dependent_props
from .load_components import *
# from .parse_inputs import *
from .file_to_array import load_array, arr_shape
from mathutils import Matrix

class Scene():
    # wraps the blender scene and can hold Microscopy Nodes Datasets
    def __init__(self, bgcol = None, render_preset=None):
        self.scn = bpy.context.scene # TODO catch uninitialized scene
        if bgcol is not None:
            self.set_background_color(bgcol)
        if render_preset is not None:
            self.set_render_settings(render_preset)
        
    def set_background_color(bgcol):
        try:
            bpy.context.scene.world.node_tree.nodes["Background"].inputs[0].default_value = bgcol
        except:
            pass
    
    def set_render_settings(render_preset):
        return

class Dataset():
    def __init__(self, holder=None, dataset_model=None):
        self.holder = None
        self.axes = None
        self.slice_cube = None
        self.volume = None
        self.surface = None
        self.labelmask = None

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
            key = next((k for k in min_keys if s in k.name.lower()), None)
            if key:
                min_obj = MinObjectFactory(type=min_key, obj=child)
                setattr(self, min_key.name.lower, min_obj)
        return

    def set_state(self, dataset_model):
        if not dataset_model.local_files_exist:
            dataset_model.make_local_files()
        for min_key in min_keys:
            min_obj = getattr(self, min_key.name.lower)
            if min_obj is None:
                min_obj = MinObjectFactory(min_key, dataset_model)
                setattr(self, min_key.name.lower, min_obj)
            if dataset_model.update_data:
                min_obj.set_data(dataset_model)
            if dataset_model.update_settings:
                min_obj.set_settings(dataset_model)
        self.ensure_links_of_objects()
        return    
    
    def ensure_links_of_objects(self):
        # set parentage, slicing, maybe also share action
        return



# def load_threaded(dataset_model):
#     # try:
#     if not bpy.context.scene.MiN_update_data:
#         return dataset_model
#     for ch in dataset_model.channels:
#         for min_type, load in ch.visible_as.items():
#             if load:
#                 data_io = DataIOFactory(min_type)
#                 file_constructors = data_io.generate_file_constructors(ch)
#                 data_io.export_ch(ch, file_constructors)
#     log('Loading objects to Blender')
#     # except Exception as e:
#     #     dataset_model.exception = str(e)
#     return dataset_model

def load_blocking(dataset_model):
    # loads from the modal/threaded implementation
    # ch_dicts, (axes_order, pixel_size, size_px), cache_dir = params
    prev_active_obj = bpy.context.active_object
    scn = bpy.context.scene

    # reads env variables
    base_coll = min_base_colls(Path(scn.MiN_input_file).stem[:50], scn.MiN_reload)    

    if scn.MiN_overwrite_background_color:
        set_background_color()
    if scn.MiN_overwrite_render_settings:
        set_render_settings()

    # --- Prepare  container ---
    container = scn.MiN_reload
    objs = parse_reload(container)

    if container is None:
        bpy.ops.object.empty_add(type="PLAIN_AXES")
        container = bpy.context.view_layer.objects.active
        container.name = Path(scn.MiN_input_file).stem[:50]

    # -- axes, slice cube and scales -- 
    # scale, scale_factor = parse_scale(size_px, pixel_size, objs) 
    # loc = parse_loc(scale, size_px, container)
    # axes_obj = load_axes(size_px, pixel_size, scale, scale_factor, axes_obj=objs[min_keys.AXES], container=container)
    # slice_cube = load_slice_cube(size_px, scale, scale_factor, container, slicecube=objs[min_keys.SLICECUBE])

    # for min_type in [min_keys.VOLUME, min_keys.SURFACE, min_keys.LABELMASK]:
    #     if not any([ch[min_type] for ch in ch_dicts]) and objs[min_type] is None:
    #         continue
    #     ch_obj = ChannelObjectFactory(min_type, objs[min_type], scale)

    #     for ch in ch_dicts:
    #         if ch[min_type] and scn.MiN_update_data:
    #             file_constructors = DataIOFactory(min_type).generate_file_constructors(ch, cache_dir)
    #             ch.metadata[min_type] = DataIOFactory(min_type).get_metadata(file_constructors)
    #             ch_obj.update_ch_data(ch, file_constructors)
    #         if scn.MiN_update_settings:
    #             ch_obj.update_ch_settings(ch)
    #         ch_obj.set_parent_and_slicer(container, slice_cube, ch)

    # container.location = loc
    
    # # -- wrap up --
    # collection_deactivate_by_name('cache')

    # if scn.frame_current < scn.MiN_load_start_frame or scn.frame_current > scn.MiN_load_end_frame:
    #     scn.frame_set(scn.MiN_load_start_frame)

    try:
        if prev_active_obj is not None:
            prev_active_obj.select_set(True)
            bpy.context.view_layer.objects.active = prev_active_obj
    except:
        pass
    # after first load this should not be used again, to prevent overwriting user values
    scn.MiN_reload = container
    scn.MiN_overwrite_render_settings = False
    scn.MiN_enable_ui = True
    log('')
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
    bpy.context.scene.eevee.volumetric_tile_size = '1'
    # bpy.context.scene.cycles.preview_samples = 8
    # bpy.context.scene.cycles.samples = 64
    bpy.context.scene.view_settings.view_transform = 'Standard'
    bpy.context.scene.eevee.volumetric_end = 300
    bpy.context.scene.eevee.taa_samples = 64

    bpy.context.scene.render.engine = 'CYCLES'
    bpy.context.scene.cycles.transparent_max_bounces = 40 # less slicing artefacts
    # bpy.context.scene.cycles.volume_bounces = 32
    # bpy.context.scene.cycles.volume_max_steps = 16 # less time to render
    bpy.context.scene.cycles.use_denoising = False # this will introduce noise, but at least also not remove data-noise=
    return
