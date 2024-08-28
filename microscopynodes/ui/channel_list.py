import bpy
from bpy.types import UIList

def mutex_labelmask(self, context):
    if self.labelmask:
        self.volume = False
        self.surface = False

def mutex_volume(self, context):
    if self.volume:
        self.labelmask = False

def mutex_surface(self, context):
    if self.surface:
        self.labelmask = False


class ChannelDescriptor(bpy.types.PropertyGroup):
    ix : bpy.props.IntProperty() # channel in the image array
    name : bpy.props.StringProperty(description="Channel name (editable)")
    volume : bpy.props.BoolProperty(description="Load data as volume", default=True, update=mutex_volume)
    emission : bpy.props.BoolProperty(description="Volume data emits light on load\n(off is recommended for EM)", default=True)
    surface : bpy.props.BoolProperty(description="Load surface object as visible.\nAlso useful for binary masks\nHeavy for complicated geometry", default=True, update=mutex_surface)
    labelmask : bpy.props.BoolProperty(name="Load labelmask",description="Load separate meshes per integer value\nOnly necessary for masks with touching separate objects\nLess flexible than Surface loading.", default=False, update=mutex_labelmask)
    surf_resolution : bpy.props.EnumProperty(
        name = "Meshing density of surfaces and masks",
        items=[
            ("ACTUAL", "Actual","Takes the actual grid size, most accurate, but heavy on RAM." ,"EVENT_A", 0),
            ("FINE", "Fine", "Close to actual grid meshing, but more flexible" ,"EVENT_F", 1),
            ("MEDIUM", "Medium", "Medium density mesh","EVENT_M", 2),
            ("COARSE", "Coarse","Coarse mesh minimizes the RAM usage of surface encoding.", "EVENT_C", 3),
        ], 
        description= "Meshing density of surfaces and masks.\nSmaller will be less RAM intensive",
        default='ACTUAL',
    )
    # The scene collectionproperty is created in __init__ of the package due to registration issues:
    # bpy.types.Scene.MiN_channelList = bpy.props.CollectionProperty(type=ui.ChannelDescriptor)

class SCENE_UL_Channels(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        channel = item
        # row = layout.split(factor=0.3, align=True)
        row = layout.row( align=True)
        row.prop(channel, "name", text="", emboss=False)
        
        volumecheckbox = "OUTLINER_OB_VOLUME" if channel.volume else "VOLUME_DATA"
        row.prop(channel, "volume", text="", emboss=True, icon=volumecheckbox)
        
        surfcheckbox = "OUTLINER_OB_SURFACE" if channel.surface else "SURFACE_DATA"
        row.prop(channel, "surface", text="", emboss=True, icon=surfcheckbox)

        maskcheckbox = "OUTLINER_OB_POINTCLOUD" if channel.labelmask else "POINTCLOUD_DATA"
        row.prop(channel, "labelmask", text="", emboss=True, icon=maskcheckbox)

        # row = row.split(factor=0.1, align=True)

        emitcheckbox = "OUTLINER_OB_LIGHT" if channel.emission else "LIGHT_DATA"
        row.prop(channel, "emission", text="", emboss=False, icon=emitcheckbox)

        row.prop(channel, "surf_resolution", text="", emboss=False, icon_only=True)

    def invoke(self, context, event):
        pass   

def set_channels(self, context):
    bpy.context.scene.MiN_channelList.clear()

    for ch in range(bpy.context.scene.MiN_channel_nr):
        channel = bpy.context.scene.MiN_channelList.add()
        channel.ix = ch
        channel.name = f"Channel {ch}"
        # set all defaults explicitly so they are created as keys
        channel.volume = True
        channel.emission = True
        channel.surface = True
        channel.labelmask = False
        channel.materials = True
        channel.surf_resolution = 'ACTUAL'

CLASSES = [ChannelDescriptor, SCENE_UL_Channels]