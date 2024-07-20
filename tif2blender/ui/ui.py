import bpy
from .. import load

from bpy.types import (Panel,
                        Operator,
                        AddonPreferences,
                        PropertyGroup,
                        )


class TIFLoadPanel(bpy.types.Panel):
    bl_idname = "SCENE_PT_zstackpanel"
    bl_label = "Tif2Blender"
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
        
        grid.prop(bpy.context.scene, 'T2B_remake', 
                        text = 'Force remaking vdb files', icon_value=0, emboss=True)
        grid.prop(bpy.context.scene, 'T2B_preset_environment', 
                        text = 'Preset environment', icon_value=0, emboss=True)
        grid.prop(bpy.context.scene, 'T2B_cache_dir', text= 'Cache dir')

        split = layout.split()
        col = split.column()
        col.prop(bpy.context.scene, 'T2B_Surface', text= 'Surfaces')
        
        col = split.column(align=True)
        col.prop(bpy.context.scene, 'T2B_Emission', text= 'Emission')

        col = layout.column(align=True)
        col.label(text=".tif file:")
        col.prop(context.scene, "T2B_input_file", text="")

        
        split = layout.split()
        col = split.column()
        col.label(text="xy pixel size (µm):")
        col.prop(scn, "T2B_xy_size")


        col = split.column(align=True)
        col.label(text="z pixel size (µm):")
        col.prop(scn, "T2B_z_size")
        
        col = layout.column(align=True)
#        col.label(text="axis order:")
        col.prop(scn, "T2B_axes_order", text="axes")
        

        col.label(text="(optional) channels of label masks")
        col.prop(bpy.context.scene, 'T2B_mask_channels', 
                        placeholder = 'e.g. 0, 3, 4',  # this is for blender 4.1
                        icon_value=0, emboss=True)

        col.label(text="  ")
#        layout.label(text="Big Button:")
        layout.operator("tiftool.load")


class TifLoadOperator(bpy.types.Operator):
    bl_idname = "tiftool.load"
    bl_label = "Load TIF"
    
    def execute(self, context):
        load.load()
        return {'FINISHED'}

CLASSES = [TifLoadOperator, TIFLoadPanel]