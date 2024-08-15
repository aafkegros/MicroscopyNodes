import bpy
from .. import load
from .. import props


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

        layout.label(text = "Import Options", icon = "MODIFIER")
        box = layout.box()
        grid = box.grid_flow(columns = 1)
        
        grid.prop(bpy.context.scene, 'MiN_remake', 
                        text = 'Force remaking vdb files', icon_value=0, emboss=True)
        grid.prop(bpy.context.scene, 'MiN_preset_environment', 
                        text = 'Preset environment', icon_value=0, emboss=True)

        grid.label(text="Asset storage:")
        grid.menu(menu='SCENE_MT_CacheSelectionMenu', text=bpy.context.scene.MiN_selected_cache_option)
        exec(props.CACHE_LOCATIONS[bpy.context.scene.MiN_selected_cache_option]['ui_element']) # makes sure to have all in the same location defined
        
        split = layout.split()
        col = split.column()
        col.prop(bpy.context.scene, 'MiN_Surface', text= 'Surfaces')
        
        col = split.column(align=True)
        col.prop(bpy.context.scene, 'MiN_Emission', text= 'Emission')

        col = layout.column(align=True)
        col.label(text=".tif or .zarr:")
        row = col.row(align=True)
        row.prop(bpy.context.scene, 'MiN_input_file', text= '')
        row.operator("microscopynodes.select_path", text="", icon='FILEBROWSER')

        if bpy.context.scene.MiN_selected_zarr_level != "":
            col.menu(menu='SCENE_MT_ZarrMenu', text=bpy.context.scene.MiN_selected_zarr_level)
        
        split = layout.split()
        col = split.column()
        col.label(text="xy pixel size (µm):")
        col.prop(scn, "MiN_xy_size")


        col = split.column(align=True)
        col.label(text="z pixel size (µm):")
        col.prop(scn, "MiN_z_size")
        
        col = layout.column(align=True)
#        col.label(text="axis order:")
        col.prop(scn, "MiN_axes_order", text="axes")
        

        col.label(text="(optional) channels of label masks")
        col.prop(bpy.context.scene, 'MiN_mask_channels', 
                        placeholder = 'e.g. 0, 3, 4',  # this is for blender 4.1
                        icon_value=0, emboss=True)

        col.label(text="  ")
#        layout.label(text="Big Button:")
        layout.operator("tiftool.load")



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
    """ Select Zarr dataset"""
    bl_idname = "microscopynodes.zarrselection"
    bl_label = "Zarr Selection"
    selected: bpy.props.StringProperty()

    def execute(self, context):
        bpy.context.scene.MiN_selected_zarr_level = self.selected
        return {'FINISHED'}

class CacheSelectOperator(bpy.types.Operator):
    """ Select Zarr dataset"""
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