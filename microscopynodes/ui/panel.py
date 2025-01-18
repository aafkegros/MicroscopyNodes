import bpy
from ..handle_blender_structs.dependent_props import *

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

        if bpy.context.scene.MiN_selected_zarr_level != "":
            col.menu(menu='SCENE_MT_ZarrMenu', text=bpy.context.scene.MiN_selected_zarr_level)
        
        # Create two columns, by using a split layout.
        split = layout.split()

        # First column
        col1 = split.column(align=True)
        col1.alignment='RIGHT'
        col1.label(text="xy pixel size (µm):")
        col1.label(text="z pixel size (µm):")
        col1.label(text="axes:")
        #  row.label(text="", icon='BLANK1')
        
        
        if not bpy.context.scene.MiN_enable_ui:
            col1.enabled=False

        col2 = split.column(align=True)
        col2.prop(scn, "MiN_xy_size", emboss=True)
        col2.prop(scn, "MiN_z_size", emboss=True)
        col2.prop(scn, "MiN_axes_order", emboss=True)


        if 't' in scn.MiN_axes_order:
            col1.label(text='time:')
            row = col2.row(align=True)
            row.prop(scn,'MiN_load_start_frame')
            row.prop(scn,'MiN_load_end_frame')


        if not bpy.context.scene.MiN_enable_ui:
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
        col.operator("microscopynodes.load")
        if not bpy.context.scene.MiN_enable_ui:
            col.enabled=False
        
        col.prop(context.scene, 'MiN_progress_str', emboss=False)
        

        box = layout.box()
        grid = box.grid_flow(columns = 1)

        grid.label(text="Data storage:", icon="FILE_FOLDER")
        grid.menu(menu='SCENE_MT_CacheSelectionMenu', text=bpy.context.scene.MiN_selected_cache_option)
        CACHE_LOCATIONS[bpy.context.scene.MiN_selected_cache_option]['ui_element'](grid)

        row = grid.split(factor=0.4)
        row.prop(bpy.context.scene, 'MiN_remake', 
                        text = 'Overwrite files', icon_value=0, emboss=True)
        row.prop(bpy.context.scene, 'MiN_preset_environment', 
                        text = 'Set environment', icon_value=0, emboss=True)
        row.prop(bpy.context.scene, 'MiN_chunk', emboss=True, text="Chunked", icon_value=0)                   


class CacheSelectOperator(bpy.types.Operator):
    """Select local storage location. This will host copies of all data in blender-compatible formats."""
    bl_idname = "microscopynodes.cacheselection"
    bl_label = "Cache Selection"
    selected: bpy.props.StringProperty()

    def execute(self, context):
        bpy.context.scene.MiN_selected_cache_option = self.selected
        return {'FINISHED'}


class CacheSelectionMenu(bpy.types.Menu):
    bl_label = "Cache/asset location"
    bl_idname = "SCENE_MT_CacheSelectionMenu"

    def draw(self, context):
        layout = self.layout
        for location in CACHE_LOCATIONS:
            prop = layout.operator(CacheSelectOperator.bl_idname, text=location, icon=CACHE_LOCATIONS[location]["icon"])
            prop.selected = location

CLASSES = [TIFLoadPanel, CacheSelectionMenu, CacheSelectOperator]
