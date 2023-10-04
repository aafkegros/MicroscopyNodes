import bpy

from bpy.props import (StringProperty, FloatProperty,
                        PointerProperty,
                        )

from bpy.types import (Panel,
                        Operator,
                        AddonPreferences,
                        PropertyGroup,
                        )

# ------------------------------------------------------------------------
#    Scene Properties
# ------------------------------------------------------------------------

class MyProperties(PropertyGroup):

    path_zstack : StringProperty(
        name="",
        description="Zstacker executable",
        default="",
        maxlen=1024,
        subtype='FILE_PATH')

    path_tif : StringProperty(
        name="",
        description="RGB tif file",
        default="",
        maxlen=1024,
        subtype='FILE_PATH')
    
    axes_order : StringProperty(
        name="",
        description="axes order (only z is used currently)",
        default="zyx",
        maxlen=6)
    
    xy_size : FloatProperty(
        name="",
        description="xy physical pixel size in micrometer",
        default=1.0)
    
    z_size : FloatProperty(
        name="",
        description="z physical pixel size in micrometer",
        default=1.0)


class TifLoadOperator(bpy.types.Operator):
    bl_idname = "tiftool.load"
    bl_label = "Load TIF"

    def execute(self, context):
        print("Hello World")
        return {'FINISHED'}



class TIFLoadPanel(bpy.types.Panel):
    bl_idname = "SCENE_PT_zstackpanel"
    bl_label = "zstacker wrapper"
    # bl_space_type = "VIEW_3D"   
    # bl_region_type = "UI"
    # bl_category = "Tools"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"

    def draw(self, context):
        layout = self.layout
        scn = context.scene
        col = layout.column(align=True)
        col.label(text="RGB .tif file:")
        col.prop(scn.tiftool, "path_tif", text="")
        col.label(text="zstacker executable:")
        col.prop(scn.tiftool, "path_zstack", text="")

        split = layout.split()
        col = split.column()
        col.label(text="xy pixel size (µm):")
        col.prop(scn.tiftool, "xy_size")


        col = split.column(align=True)
        col.label(text="z pixel size (µm):")
        col.prop(scn.tiftool, "z_size")
        
        col = layout.column(align=True)
        col.label(text="axis order:")
        col.prop(scn.tiftool, "axes_order")
        
#        layout.label(text="Big Button:")
        layout.operator("tiftool.load")


# ------------------------------------------------------------------------
#    Registration
# ------------------------------------------------------------------------

classes = (
    MyProperties,
    TIFLoadPanel,
    TifLoadOperator
)

def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)

    bpy.types.Scene.tiftool = PointerProperty(type=MyProperties)

def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
    del bpy.types.Scene.tiftool


if __name__ == "__main__":
    register()

#if __name__ == "__main__":
#    register()
