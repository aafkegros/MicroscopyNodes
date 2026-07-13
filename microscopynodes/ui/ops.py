import bpy
from bpy.types import Operator
from ..data_model import DatasetModel
from ..io.local_file_process import LocalFileProcess
from ..io.generate import generate_local_files
from ..blender_state import Scene, Dataset
from .gui_to_data_model import parse_blender_ui
from ..handle_blender_structs.dependent_props import ensure_valid_reload_object
from ..handle_blender_structs.progress_handling import clear_progress


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
    local_file_process = None
    dataset_model: DatasetModel = None

    @classmethod
    def poll(cls, context):
        return not context.window_manager.MiN_load_running

    def _remove_timer(self, context):
        if self._timer is None:
            return
        try:
            context.window_manager.event_timer_remove(self._timer)
        except Exception:
            pass
        self._timer = None

    def _cleanup(self, context):
        self._remove_timer(context)
        if self.local_file_process is not None:
            self.local_file_process.close()
            self.local_file_process = None
        context.window_manager.MiN_load_running = False
        context.window_manager.MiN_cancel_load_requested = False
        clear_progress()

    def _read_progress(self, context):
        progress = self.local_file_process.progress()
        if progress is not None:
            context.scene.MiN_progress_str = progress

    def _finish(self, context):
        self.dataset_model = self.local_file_process.result()
        self._cleanup(context)
        Scene.from_blender_ui(context)
        ensure_valid_reload_object(context.scene)
        dataset = Dataset(holder=context.scene.MiN_reload)
        dataset.set_state(
            self.dataset_model,
            update_data=context.scene.MiN_update_data,
            update_settings=context.scene.MiN_update_settings,
        )
        select_post_load_object(context, dataset, self.prev_active_obj)
        clear_progress()
        return {'FINISHED'}

    def modal(self, context, event):
        if context.window_manager.MiN_cancel_load_requested:
            self._cleanup(context)
            return {'CANCELLED'}
        if event.type == 'TIMER':
            if context.area is not None:
                for region in context.area.regions:
                    region.tag_redraw()
            self._read_progress(context)
            returncode = self.local_file_process.poll()
            if returncode is None:
                return {"RUNNING_MODAL"}
            if returncode != 0:
                error = self.local_file_process.error()
                self._cleanup(context)
                self.report({'ERROR'}, error)
                return {'CANCELLED'}
            try:
                return self._finish(context)
            except Exception as error:
                self._cleanup(context)
                self.report({'ERROR'}, str(error))
                return {'CANCELLED'}
        if event.type in {'RIGHTMOUSE', 'ESC'}:  # Cancel
            self._cleanup(context)
            return {'CANCELLED'}

        return {"PASS_THROUGH"}


    def execute(self, context):
        wm = context.window_manager
        self.dataset_model = parse_blender_ui()
        self.prev_active_obj = context.active_object
        package_name = __package__.rsplit(".ui", 1)[0]
        try:
            self.local_file_process = LocalFileProcess(
                self.dataset_model,
                blender_binary=bpy.app.binary_path,
                package_name=package_name,
            )
        except Exception as error:
            self._cleanup(context)
            self.report({'ERROR'}, str(error))
            return {'CANCELLED'}
        context.window_manager.MiN_cancel_load_requested = False
        context.window_manager.MiN_load_running = True
        self._timer = wm.event_timer_add(0.1, window=context.window)
        wm.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def cancel(self, context):
        self._cleanup(context)


class TifLoadCancelOperator(bpy.types.Operator):
    """Cancel resaving the microscopy dataset to local cache files [Esc]"""

    bl_idname = "microscopynodes.cancel_load"
    bl_label = "Cancel"

    @classmethod
    def poll(cls, context):
        return context.window_manager.MiN_load_running

    def execute(self, context):
        context.window_manager.MiN_cancel_load_requested = True
        return {'FINISHED'}


class TifLoadBackgroundOperator(bpy.types.Operator):
    """ Load a microscopy image. Resaves your data into vdb (volume) and abc (mask) formats into Cache Folder"""
    bl_idname ="microscopynodes.load_background"
    bl_label = "Load"

    def execute(self, context):
        dataset_model = parse_blender_ui()
        generate_local_files(dataset_model)
        Scene.from_blender_ui(context)
        ensure_valid_reload_object(context.scene)
        dataset = Dataset(holder=context.scene.MiN_reload)
        dataset.set_state(
            dataset_model,
            update_data=context.scene.MiN_update_data,
            update_settings=context.scene.MiN_update_settings,
        )
        select_post_load_object(context, dataset, context.active_object)
        clear_progress()
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


CLASSES = [TifLoadOperator, TifLoadCancelOperator, TifLoadBackgroundOperator, ArrayOptionSelectOperator, ArrayOptionMenu, SelectPathOperator]
