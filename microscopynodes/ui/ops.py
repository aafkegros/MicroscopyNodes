import bpy
from .. import load
from .. import parse_inputs
from .. import handle_blender_structs
from .channel_list import *
from bpy.types import (Panel,
                        Operator,
                        AddonPreferences,
                        PropertyGroup,
                        )
from bpy.types import UIList
import threading
from ..data_model import DatasetModel
from ..load import Scene, Dataset
from ..parse_inputs import parse_blender_ui


def select_post_load_object(context, dataset, previous_active_obj):
    try:
        if previous_active_obj is not None and previous_active_obj.name in bpy.data.objects:
            previous_active_obj.select_set(True)
            context.view_layer.objects.active = previous_active_obj
            return
    except Exception:
        pass

    for min_obj in (dataset.volume, dataset.surface, dataset.labelmask, dataset.axes, dataset.slicecube):
        if min_obj is None:
            continue
        obj = min_obj.object
        if obj is None:
            continue
        try:
            obj.select_set(True)
            context.view_layer.objects.active = obj
            return
        except Exception:
            continue


class TifLoadOperator(bpy.types.Operator):
    """ Load a microscopy dataset. Resaves your data into vdb (volume) and abc (mask) formats into Cache Folder"""
    bl_idname ="microscopynodes.load"
    bl_label = "Load"

    _timer = None
    value = 0 
    thread = None
    params = None
    dataset_model: DatasetModel = None

    def modal(self, context, event):
        if event.type == 'TIMER':
            [region.tag_redraw() for region in context.area.regions]
            if self.thread is None:
                if len(self.dataset_model.exception) > 0: 
                    raise(Exception(self.dataset_model.exception))
                    return {"CANCELLED"}
                context.window_manager.event_timer_remove(self._timer)
                Scene.from_blender_ui(context)
                dataset = Dataset(holder=context.scene.MiN_reload)
                dataset.set_state(self.dataset_model)
                select_post_load_object(context, dataset, self.prev_active_obj)
                return {'FINISHED'}
            if not self.thread.is_alive():
                self.thread = None # update UI for one timer-round
            return {"RUNNING_MODAL"}
        if event.type in {'RIGHTMOUSE', 'ESC'}:  # Cancel
            # Revert all changes that have been made
            return {'CANCELLED'}

        return {"RUNNING_MODAL"}


    def execute(self, context):
        wm = context.window_manager
        self._timer = wm.event_timer_add(0.1, window=context.window)

        self.dataset_model = parse_blender_ui()
        # self.min_scene = Scene()
        print(self.dataset_model)
        self.thread = threading.Thread(name='loading thread', target=self.dataset_model.make_local_files)
        self.prev_active_obj = bpy.context.active_object
        # self.thread = threading.Thread(name='loading thread', target=self.dataset_model.make_local_files, args=(self.dataset_model,))
        
        # self.params = parse_inputs.parse_initial()
        # self.thread = threading.Thread(name='loading thread', target=load.load_threaded, args=(self.params,))
        wm.modal_handler_add(self)
        self.thread.start()
        return {'RUNNING_MODAL'}

    def cancel(self, context):
        wm = context.window_manager
        wm.event_timer_remove(self._timer)
        return


class TifLoadBackgroundOperator(bpy.types.Operator):
    """ Load a microscopy image. Resaves your data into vdb (volume) and abc (mask) formats into Cache Folder"""
    bl_idname ="microscopynodes.load_background"
    bl_label = "Load"

    def execute(self, context):
        dataset_model = parse_blender_ui()
        dataset_model.make_local_files()
        Scene.from_blender_ui(context)
        dataset = Dataset(holder=context.scene.MiN_reload)
        dataset.set_state(dataset_model)
        select_post_load_object(context, dataset, context.active_object)
        return {'FINISHED'}


class ArrayOptionSelectOperator(bpy.types.Operator):
    """Select Zarr dataset"""
    bl_idname = "microscopynodes.arrayselection"
    bl_label = "Load array option"
    ix: bpy.props.IntProperty()

    def execute(self, context):
        bpy.context.scene.MiN_selected_zarr_level = self.ix
        return {'FINISHED'}

class ArrayOptionMenu(bpy.types.Menu):
    bl_label = "Zarr datasets"
    bl_idname = "SCENE_MT_ArrayOptionMenu"

    def draw(self, context):
        layout = self.layout
        for ix, array_option in enumerate(bpy.context.scene.MiN_array_options):
            prop = layout.operator(ArrayOptionSelectOperator.bl_idname, text=array_option.ui_text, icon=array_option.icon)
            prop.ix = ix

class SelectPathOperator(Operator):
    """Select file or directory"""
    bl_idname = "microscopynodes.select_path"
    bl_label = "Select path"
    bl_options = {'REGISTER'}

    # These are magic keywords for Blender 
    filepath: bpy.props.StringProperty(
        name="filepath",
        description=".tif path",
        default = ""
        )
    directory: bpy.props.StringProperty(
        name="directory",
        description=".zarr path",
        default= ""
        )
    
    def execute(self, context):
        if self.filepath != "":
            bpy.context.scene.MiN_input_file = self.filepath
        elif self.directory != "":
            bpy.context.scene.MiN_input_file = self.directory
        return {'FINISHED'}

    def invoke(self, context, event):
        self.filepath = ""
        self.directory = ""
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


CLASSES = [TifLoadOperator, TifLoadBackgroundOperator, ArrayOptionSelectOperator, ArrayOptionMenu, SelectPathOperator]
