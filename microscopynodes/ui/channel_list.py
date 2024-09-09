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
    surface : bpy.props.BoolProperty(description="Load isosurface object.\nAlso useful for binary masks", default=True, update=mutex_surface)
    labelmask : bpy.props.BoolProperty(description="Do not use on regular images.\nLoads separate values in the mask as separate mesh objects", default=False, update=mutex_labelmask)
    surf_resolution : bpy.props.EnumProperty(
        name = "Meshing density of surfaces and masks",
        items=[
            ("ACTUAL", "Actual","Takes the actual grid size, most accurate, but heavy on RAM." ,"EVENT_A", 0),
            ("FINE", "Fine", "Close to actual grid meshing, but more flexible" ,"EVENT_F", 1),
            ("MEDIUM", "Medium", "Medium density mesh","EVENT_M", 2),
            ("COARSE", "Coarse","Coarse mesh minimizes the RAM usage of surface encoding.", "EVENT_C", 3),
        ], 
        description= "Coarser will be less RAM intensive",
        default='ACTUAL',
    )
    # The scene collectionproperty is created in __init__ of the package due to registration issues:
    # bpy.types.Scene.MiN_channelList = bpy.props.CollectionProperty(type=ui.ChannelDescriptor)

class SCENE_UL_Channels(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        self.use_filter_show =False #filtering is currently unsupported
        channel = item

        row = layout.row( align=True)
        row.prop(channel, "name", text="", emboss=True)
        
        volumecheckbox = "OUTLINER_OB_VOLUME" if channel.volume else "VOLUME_DATA"
        row.prop(channel, "volume", text="", emboss=True, icon=volumecheckbox)
        
        surfcheckbox = "OUTLINER_OB_SURFACE" if channel.surface else "SURFACE_DATA"
        row.prop(channel, "surface", text="", emboss=True, icon=surfcheckbox)

        maskcheckbox = "OUTLINER_OB_POINTCLOUD" if channel.labelmask else "POINTCLOUD_DATA"
        row.prop(channel, "labelmask", text="", emboss=True, icon=maskcheckbox)

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
        channel.surface = False
        channel.labelmask = False
        channel.materials = True
        channel.surf_resolution = 'ACTUAL'

CLASSES = [ChannelDescriptor, SCENE_UL_Channels]