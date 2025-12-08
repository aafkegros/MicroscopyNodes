import bpy
from ..handle_blender_structs.dependent_props import *
from ..file_to_array import selected_array_option
from .preferences import addon_preferences

class TIFLoadPanel(bpy.types.Panel):
    bl_idname = "SCENE_PT_zstackpanel"
    bl_label = "Microscopy Nodes"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"

    def draw(self, context):
        layout = self.layout
        scn = bpy.context.scene

        col = layout.column(align=True)
        col.label(text=".tif or .zarr:")
        row = col.row(align=True)
        row.prop(bpy.context.scene, 'MiN_input_file', text= '')
        row.operator("microscopynodes.select_path", text="", icon='FILEBROWSER')

        
        
        if bpy.context.scene.MiN_selected_array_option != "" and len(bpy.context.scene.MiN_array_options) != 0:
            row =col.row(align=True)
            row.prop(bpy.context.scene, 'MiN_selected_array_option')
            row.enabled = True
            if len(bpy.context.scene.MiN_array_options) == 0:
                row.enabled = False
            if selected_array_option().is_rescaled:
                row.prop(bpy.context.scene, 'MiN_pixel_sizes_are_rescaled', icon="FIXED_SIZE", icon_only=True)
            # col.menu(menu='SCENE_MT_ArrayOptionMenu', text=selected_array_option().ui_text)
        
        
        # # Create two columns, by using a split layout.
        split = layout.split()

        # First column
        col1 = split.column(align=True)
        col1.alignment='RIGHT'
        if selected_array_option() is None or not selected_array_option().is_rescaled or not bpy.context.scene.MiN_pixel_sizes_are_rescaled:
            col1.label(text="xy pixel size:")
            col1.label(text="z pixel size:")
        else:
            if selected_array_option().path != "":
                col1.label(text=f"{selected_array_option().path} xy pixel size:")
                col1.label(text=f"{selected_array_option().path} z pixel size:")
            else:
                col1.label(text=f"xy pixel size (after rescaling):")
                col1.label(text=f"z pixel size (after rescaling):")
        col1.label(text="axes:")

        col2 = split.column(align=True)
        
        rowxy = col2.row(align=True)
        rowxy.prop(scn, "MiN_xy_size", emboss=True)
        rowxy.prop(scn, "MiN_unit", emboss=False)
        
        rowz = col2.row(align=True)
        rowz.prop(scn, "MiN_z_size", emboss=True)
        rowz.prop(scn, "MiN_unit", emboss=False)
        
        col2.prop(scn, "MiN_axes_order", emboss=True)

        if 't' in scn.MiN_axes_order:
            col1.label(text='time:')
            rowt = col2.row(align=True)
            rowt.prop(scn,'MiN_load_start_frame')
            rowt.prop(scn,'MiN_load_end_frame')

        if not bpy.context.scene.MiN_enable_ui:
            col1.enabled=False
            col2.enabled=False

        
        col = layout.column(align=False)  

        col.template_list("SCENE_UL_Channels", "", bpy.context.scene, "MiN_channelList", bpy.context.scene, "MiN_ch_index", rows=max(len(bpy.context.scene.MiN_channelList),1),sort_lock=True)

        if not bpy.context.scene.MiN_enable_ui:
            col.enabled=False

        col.separator()

        row = col.row(align=True)
        row.label(text="", icon='FILE_REFRESH')
        row.prop(bpy.context.scene, 'MiN_reload', icon="OUTLINER_OB_EMPTY")
        if bpy.context.scene.MiN_reload is not None:
            row.prop(bpy.context.scene, 'MiN_update_data', icon="FILE")
            row.prop(bpy.context.scene, 'MiN_update_settings', icon="MATERIAL_DATA")
        
        
        # layout.separator()
        col.separator()
        # col = layout.column(align=False)  
        # row = col.row(align=False)
        if bpy.context.scene.MiN_reload is None:
            col.operator("microscopynodes.load", text="Load")
        else:
            col.operator("microscopynodes.load", text="Reload")
        if not bpy.context.scene.MiN_enable_ui:
            col.enabled=False
        
        col.prop(context.scene, 'MiN_progress_str', emboss=False)

        
        box = layout.box()
        row = box.row(align=True)
        if context.scene.MiN_yaml_preferences != "":
            row.label(text=f"Preferences are overriden from {context.scene.MiN_yaml_preferences}", icon="ERROR")
            row= box.row()
            row.prop(bpy.context.scene, 'MiN_yaml_preferences', text="")
            row = box.row()
            row.operator("microscopynodes.reset_yaml")
            return
        
        

        row.label(text="Data Storage:", icon="FILE_FOLDER")
        row.prop(addon_preferences(context), 'cache_option', text="", icon="NONE", emboss=True)
        
        if addon_preferences().cache_option == 'PATH':
            row = box.row()
            row.prop(addon_preferences(context), 'cache_path', text="")
        if addon_preferences().cache_option == 'WITH_PROJECT' and bpy.path.abspath('//') == '':
            row = box.row()
            row.label(text = "Don't forget to save your blend file :)")

        row = box.row(align=True)
        
        row.prop(bpy.context.scene, 'MiN_overwrite_background_color', 
                        text = '', icon="WORLD",icon_only=True,emboss=True)
        row.prop(bpy.context.scene, 'MiN_overwrite_render_settings', 
                        text = '', icon="SCENE",icon_only=True,emboss=True)
        row.separator()
        row.label(text="", icon='CON_SIZELIKE')
        if bpy.context.scene.MiN_unit == "AU":
            row.prop(addon_preferences(bpy.context), 'import_scale_no_unit_spoof', emboss=True,text="")
        else:
            row.prop(addon_preferences(bpy.context), 'import_scale', emboss=True,text="")
        row.label(text="", icon='ORIENTATION_PARENT')
        row.prop(addon_preferences(bpy.context), 'import_loc', emboss=True,text="")

       
CLASSES = [TIFLoadPanel]
