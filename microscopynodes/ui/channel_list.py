import bpy
from bpy.types import UIList

def mutex_labelmask(self, context):
    if self.labelmask:
        self.volume = False
        self.emission = False
        self.surface = False
    print(self.labelmask)

def mutex_volume(self, context):
    if self.volume:
        self.labelmask = False

def mutex_emission(self, context):
    if self.volume:
        self.labelmask = False

def mutex_surface(self, context):
    if self.surface:
        self.labelmask = False

class ChannelDescriptor(bpy.types.PropertyGroup):
    ix : bpy.props.IntProperty() # not UI-changable or visualized
    name : bpy.props.StringProperty(description="Channel name (editable)")
    volume : bpy.props.BoolProperty(description="Load data as volume", default=True, update=mutex_volume)
    emission : bpy.props.BoolProperty(description="Volume data emits light on load\n(off is recommended for EM)", default=True, update=mutex_emission)
    surface : bpy.props.BoolProperty(description="Load surface object.\nAlso useful for binary masks\nHeavy for complicated geometry", default=True, update=mutex_surface)
    labelmask : bpy.props.BoolProperty(description="Load as labelmask as separate objects.\nExpects objects in the mask per integer value", default=False, update=mutex_labelmask)
    # The scene collectionproperty is created in __init__ of the package due to registration issues:
    # bpy.types.Scene.MiN_channelList = bpy.props.CollectionProperty(type=ui.ChannelDescriptor)



class SCENE_UL_Channels(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        channel = item
        row = layout.split(factor=0.7)
        # print(channel, channel.name, channel.volume,'hey', len(bpy.context.scene.MiN_channelList), bpy.context.scene.MiN_channel_nr)
        # row.label(text=channel.name, icon='VOLUME_DATA') # avoids renaming the item by accident
        # split.label("hde")
        row.prop(channel, "name", text="", emboss=False)

        volumecheckbox = "OUTLINER_OB_VOLUME" if channel.volume else "VOLUME_DATA"
        row.prop(channel, "volume", text="", emboss=False, icon=volumecheckbox)
        
        emitcheckbox = "OUTLINER_OB_LIGHT" if channel.emission else "LIGHT_DATA"
        row.prop(channel, "emission", text="", emboss=False, icon=emitcheckbox)
        
        surfcheckbox = "OUTLINER_OB_SURFACE" if channel.surface else "SURFACE_DATA"
        row.prop(channel, "surface", text="", emboss=False, icon=surfcheckbox)

        maskcheckbox = "OUTLINER_OB_POINTCLOUD" if channel.labelmask else "POINTCLOUD_DATA"
        row.prop(channel, "labelmask", text="", emboss=False, icon=maskcheckbox)
            # split.prop(channel.volume)

    def invoke(self, context, event):
        pass   

def set_channels(self, context):
    bpy.context.scene.MiN_channelList.clear()
    print('setting channels', bpy.context.scene.MiN_channel_nr)
    for ch in range(bpy.context.scene.MiN_channel_nr):
        channel = bpy.context.scene.MiN_channelList.add()
        channel.ix = ch
        channel.name = f"Channel {ch}"
        # channel.volume = True
        channel.surface = True
        channel.labelmask = False

CLASSES = [ChannelDescriptor, SCENE_UL_Channels]