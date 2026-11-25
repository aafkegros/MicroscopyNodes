import textwrap

import bpy
from ..handle_blender_structs.dependent_props import valid_reload_object
from ..file_to_array import selected_array_option
from .preferences import addon_preferences

def wrapped(text, width, ui_scale):
    """Lines of text that fit labels in a region of this width in pixels. Approximate: characters differ in width."""
    return textwrap.wrap(text, max(int((width - 30) / (7.5 * (ui_scale or 1.0))), 20))


class TIFLoadPanel(bpy.types.Panel):
    bl_idname = "SCENE_PT_zstackpanel"
    bl_label = "Microscopy Nodes"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"

    def draw(self, context):
        layout = self.layout
        scn = context.scene
        wm = context.window_manager
        try:
            reload_object = scn.MiN_reload
        except ReferenceError:
            reload_object = None
        reload_object_is_valid = valid_reload_object(reload_object, scene=scn)
        data_inputs_enabled = not reload_object_is_valid or scn.MiN_update_data
        settings_inputs_enabled = not reload_object_is_valid or scn.MiN_update_settings

        source_col = layout.column(align=True)
        source_col.label(text=".tif or .zarr:")
        row = source_col.row(align=True)
        row.prop(bpy.context.scene, 'MiN_input_file', text= '')
        row.operator("microscopynodes.select_path", text="", icon='FILEBROWSER')

        
        
        if bpy.context.scene.MiN_selected_array_option != "" and len(bpy.context.scene.MiN_array_options) != 0:
            row = source_col.row(align=True)
            row.prop(bpy.context.scene, 'MiN_selected_array_option')
            row.enabled = True
            if len(bpy.context.scene.MiN_array_options) == 0:
                row.enabled = False
            if selected_array_option().is_rescaled:
                row.prop(bpy.context.scene, 'MiN_pixel_sizes_are_rescaled', icon="FIXED_SIZE", icon_only=True)
            # col.menu(menu='SCENE_MT_ArrayOptionMenu', text=selected_array_option().ui_text)
        source_col.enabled = data_inputs_enabled
        
        
        # # Create two columns, by using a split layout.
        split = layout.split()

        # First column
        col1 = split.column(align=True)
        col1.alignment='RIGHT'
        col2 = split.column(align=True)

        size_fields = [("xy", "MiN_ui_xy_size")]
        if addon_preferences(context).always_show_xyz_pixel_sizes or scn.MiN_x_size != scn.MiN_y_size:
            size_fields = [("x", "MiN_x_size"), ("y", "MiN_y_size")]
        size_fields.append(("z", "MiN_z_size"))

        option = selected_array_option()
        rescaled = option is not None and option.is_rescaled and scn.MiN_pixel_sizes_are_rescaled
        for axis, prop in size_fields:
            label = f"{axis} pixel size"
            if rescaled:
                label = f"{option.path} {label}" if option.path else f"{label} (after rescaling)"
            col1.label(text=f"{label}:")
            row = col2.row(align=True)
            row.prop(scn, prop, emboss=True)
            row.prop(scn, "MiN_unit", emboss=False)

        col1.label(text="axes:")
        col2.prop(scn, "MiN_axes_order", emboss=True)

        if 't' in scn.MiN_axes_order:
            col1.label(text='time:')
            rowt = col2.row(align=True)
            rowt.prop(scn,'MiN_load_start_frame')
            rowt.prop(scn,'MiN_load_end_frame')

        col1.enabled = bool(scn.MiN_input_file) and data_inputs_enabled
        col2.enabled = bool(scn.MiN_input_file) and data_inputs_enabled

        
        col = layout.column(align=False)  

        col.template_list("SCENE_UL_Channels", "", bpy.context.scene, "MiN_channelList", bpy.context.scene, "MiN_ch_index", rows=max(len(bpy.context.scene.MiN_channelList),1),sort_lock=True)

        col.enabled = scn.MiN_enable_ui and (
            data_inputs_enabled or settings_inputs_enabled
        )

        row = layout.row(align=True)
        row.label(text="", icon='FILE_REFRESH')
        row.prop(bpy.context.scene, 'MiN_reload', icon="OUTLINER_OB_MESH")
        if reload_object_is_valid:
            row.prop(bpy.context.scene, 'MiN_load_with_mask', icon="HIDE_OFF")
            row.prop(bpy.context.scene, 'MiN_update_data', icon="FILE")
            row.prop(bpy.context.scene, 'MiN_update_settings', icon="MATERIAL_DATA")
        row.enabled = scn.MiN_enable_ui

        
        
        # layout.separator()
        layout.separator()
        # col = layout.column(align=False)  
        # row = col.row(align=False)
        action = layout.column(align=False)
        if wm.MiN_load_running:
            action.operator("microscopynodes.cancel_load", text="Cancel", icon="CANCEL")
        elif not reload_object_is_valid:
            action.operator("microscopynodes.load", text="Load")
        else:
            action.operator("microscopynodes.load", text="Reload")
        action.enabled = wm.MiN_load_running or scn.MiN_enable_ui

        if scn.MiN_progress_str and not (wm.MiN_load_running or scn.MiN_enable_ui):
            # Loading failed. Show the message in full, a disabled field would truncate it.
            error = layout.column(align=True)
            error.alert = True
            for ix, line in enumerate(wrapped(scn.MiN_progress_str, context.region.width, context.preferences.system.ui_scale)):
                error.label(text=line, icon="ERROR" if ix == 0 else "BLANK1")
        else:
            action.prop(context.scene, 'MiN_progress_str', emboss=False)

        box = layout.box()
        on_load_split = box.split(factor=0.17, align=True)
        title_column = on_load_split.column(align=True)
        title_column.alignment = 'CENTER'
        title_column.label(text="On load")
        settings_split = on_load_split.split(factor=0.5, align=True)
        scene_controls = settings_split.row(align=True)
        scene_controls.alignment = 'RIGHT'
        scene_controls.label(text="Scene", icon="SCENE_DATA")
        scene_controls.prop(
            scn,
            'MiN_overwrite_background_color',
            text='',
            icon="WORLD",
            icon_only=True,
            emboss=True,
        )
        scene_controls.prop(
            scn,
            'MiN_overwrite_render_settings',
            text='',
            icon="SCENE",
            icon_only=True,
            emboss=True,
        )
        slice_controls = settings_split.row(align=True)
        slice_controls.alignment = 'RIGHT'
        slice_controls.label(text="Slicing", icon="SURFACE_NCURVE")
        slice_controls.prop_enum(
            addon_preferences(context),
            "slice_cube_mode",
            "GEOMETRY",
            text="",
            icon="GEOMETRY_NODES",
        )
        slice_controls.prop_enum(
            addon_preferences(context),
            "slice_cube_mode",
            "SHADER",
            text="",
            icon="MATERIAL",
        )
        on_load_split.enabled = settings_inputs_enabled

        row = box.row(align=True)
        row.label(text="Data Storage:", icon="FILE_FOLDER")
        row.prop(addon_preferences(context), 'cache_option', text="", icon="NONE", emboss=True)
        row.enabled = data_inputs_enabled

        if addon_preferences().cache_option == 'PATH':
            row = box.row()
            row.prop(addon_preferences(context), 'cache_path', text="")
            row.enabled = data_inputs_enabled
        if addon_preferences().cache_option == 'WITH_PROJECT' and bpy.path.abspath('//') == '':
            row = box.row()
            row.label(text = "Don't forget to save your blend file :)")

        row = layout.row(align=True)
        row.label(text="", icon='CON_SIZELIKE')
        row.prop(bpy.context.scene, 'MiN_import_scale', emboss=True,text="")
        row.label(text="", icon='ORIENTATION_PARENT')
        row.prop(bpy.context.scene, 'MiN_import_loc', emboss=True,text="")
        row.enabled = settings_inputs_enabled

       
CLASSES = [TIFLoadPanel]
