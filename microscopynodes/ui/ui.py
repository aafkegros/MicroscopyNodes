import bpy
from .. import load
from . import props

from .channel_list import *


from bpy.types import (Panel,
                        Operator,
                        AddonPreferences,
                        PropertyGroup,
                        )


class TIFLoadPanel(bpy.types.Panel):
    bl_idname = "SCENE_PT_zstackpanel"
    bl_label = "Microscopy Nodes"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"

    def draw(self, context):
        # print('drawing tifloadpanel')
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
        col = split.column(align=True)
        col.alignment='RIGHT'
        col.label(text="xy pixel size (µm):")
        col.label(text="z pixel size (µm):")
        col.label(text="axes:")
        if not bpy.context.scene.MiN_enable_ui:
            col.enabled=False

        # Second column, aligned
        col = split.column(align=True)
        col.prop(scn, "MiN_xy_size", emboss=True)
        col.prop(scn, "MiN_z_size", emboss=True)
        col.prop(scn, "MiN_axes_order", emboss=True)
        
        if not bpy.context.scene.MiN_enable_ui:
            col.enabled=False
        
        col = layout.column(align=False)  

        col.template_list("SCENE_UL_Channels", "", bpy.context.scene, "MiN_channelList", bpy.context.scene, "MiN_ch_index", rows=max(len(bpy.context.scene.MiN_channelList),1))

        if not bpy.context.scene.MiN_enable_ui:
            col.enabled=False

        row = col.row(align=False)
        row.prop(bpy.context.scene, 'MiN_reload_data_of', icon="OUTLINER_OB_EMPTY", text='Reload data')
        
        layout.separator()
        col = layout.column(align=False)  
        col.operator("tiftool.load")
        if not bpy.context.scene.MiN_enable_ui:
            col.enabled=False
        
        layout.separator()

        box = layout.box()
        grid = box.grid_flow(columns = 1)

        grid.label(text="Data storage:", icon="FILE_FOLDER")
        grid.menu(menu='SCENE_MT_CacheSelectionMenu', text=bpy.context.scene.MiN_selected_cache_option)
        props.CACHE_LOCATIONS[bpy.context.scene.MiN_selected_cache_option]['ui_element'](grid)

        row = grid.split(factor=0.4)
        row.prop(bpy.context.scene, 'MiN_remake', 
                        text = 'Overwrite files', icon_value=0, emboss=True)
        row.prop(bpy.context.scene, 'MiN_preset_environment', 
                        text = 'Set environment', icon_value=0, emboss=True)






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
        print(f"set min input to {self.filepath}, {self.directory}")
        return {'FINISHED'}

    def invoke(self, context, event):
        self.filepath = ""
        self.directory = ""
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class TifLoadOperator(bpy.types.Operator):
    """ Load a microscopy image. Resaves your data into vdb (volume) and abc (mask) formats into Cache Folder"""
    bl_idname = "tiftool.load"
    bl_label = "Load"
    
    def execute(self, context):
        load.load()
        return {'FINISHED'}

class ZarrSelectOperator(bpy.types.Operator):
    """Select Zarr dataset"""
    bl_idname = "microscopynodes.zarrselection"
    bl_label = "Zarr Selection"
    selected: bpy.props.StringProperty()

    def execute(self, context):
        bpy.context.scene.MiN_selected_zarr_level = self.selected
        return {'FINISHED'}

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
        for location in props.CACHE_LOCATIONS:
            prop = layout.operator(CacheSelectOperator.bl_idname, text=location, icon=props.CACHE_LOCATIONS[location]["icon"])
            prop.selected = location

class ZarrMenu(bpy.types.Menu):
    bl_label = "Zarr datasets"
    bl_idname = "SCENE_MT_ZarrMenu"

    def draw(self, context):
        layout = self.layout
        for zarrlevel in bpy.context.scene.MiN_zarrLevels:
            prop = layout.operator(ZarrSelectOperator.bl_idname, text=zarrlevel.level_descriptor, icon='VOLUME_DATA')
            prop.selected = zarrlevel.level_descriptor

CLASSES = [TifLoadOperator, TIFLoadPanel, ZarrSelectOperator, ZarrMenu, SelectPathOperator, CacheSelectionMenu, CacheSelectOperator]