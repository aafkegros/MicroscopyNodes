import bpy
from . import load

from bpy.types import (Panel,
                        Operator,
                        AddonPreferences,
                        PropertyGroup,
                        )


class TIFLoadPanel(bpy.types.Panel):
    bl_idname = "SCENE_PT_zstackpanel"
    bl_label = "tif loader"
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
        
        grid.prop(bpy.context.scene, 'TL_remake', 
                        text = 'Force remaking vdb files', icon_value=0, emboss=True)
        grid.prop(bpy.context.scene, 'TL_preset_environment', 
                        text = 'Preset environment', icon_value=0, emboss=True)
        grid.prop(bpy.context.scene, 'TL_otsu', 
                        text = 'Otsu on load (slow for big data)', icon_value=0, emboss=True)

        col = layout.column(align=True)
        col.label(text=".tif file:")
        col.prop(context.scene, "path_tif", text="")

        split = layout.split()
        col = split.column()
        col.label(text="xy pixel size (µm):")
        col.prop(scn, "xy_size")


        col = split.column(align=True)
        col.label(text="z pixel size (µm):")
        col.prop(scn, "z_size")
        
        col = layout.column(align=True)
#        col.label(text="axis order:")
        col.prop(scn, "axes_order", text="axes")
        
#        layout.label(text="Big Button:")
        layout.operator("tiftool.load")


class TifLoadOperator(bpy.types.Operator):
    bl_idname = "tiftool.load"
    bl_label = "Load TIF"
    
    def execute(self, context):
        scn = context.scene
        # print(scn.path_zstack)
        load.load(input_file = scn.path_tif, xy_scale=scn.xy_size, z_scale=scn.z_size, axes_order=scn.axes_order)
        return {'FINISHED'}

