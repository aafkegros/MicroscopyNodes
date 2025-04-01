import bpy
from bpy.types import UIList
import os
# from ..min_nodes.shader_nodes import draw_category_menus

def update_ix(self, context):
    context.scene.MiN_ch_index = self.ix


class ChannelDescriptor(bpy.types.PropertyGroup):
    # Initialization of these classes is done in set_channels - these defaults are not used by mic nodes itself
    ix : bpy.props.IntProperty() # channel in the image array

    update_func = update_ix
    if os.environ.get('MIN_TEST', False):
        update_func = None

    name : bpy.props.StringProperty(description="Channel name (editable)", update = update_func )
    volume : bpy.props.BoolProperty(description="Load data as volume", default=True, update=update_func )
    emission : bpy.props.BoolProperty(description="Volume data emits light on load\n(off is recommended for EM)", default=True, update=update_func )
    surface : bpy.props.BoolProperty(description="Load isosurface object.\nAlso useful for binary masks", default=True, update=update_func )
    labelmask : bpy.props.BoolProperty(description="Do not use on regular images.\nLoads separate values in the mask as separate mesh objects", default=False, update=update_func )
    # -- internal --
    threshold : bpy.props.FloatProperty(default=-1)
    cmap : bpy.props.EnumProperty(
        name = "Default Colormaps",
        items=[
            ("SINGLE_COLOR", "Single Color","Settable single color, will generate map from black to color" ,"MESH_PLANE", 0),
            ("VIRIDIS", "Viridis", "bids:viridis","IPO_LINEAR", 1),
            ("PLASMA", "Plasma","bids:plasma", "IPO_LINEAR", 2),
            ("COOLWARM", "Coolwarm","matplotlib:coolwarm", "LINCURVE", 3),
            ("ICEFIRE", "IceFire","seaborn:icefire", "LINCURVE", 4),
            ("TAB10", "Tab10","seaborn:tab10", "OUTLINER_DATA_POINTCLOUD", 5),
            ("BRIGHT", "Bright","tol:bright", "OUTLINER_DATA_POINTCLOUD", 6),
        ], 
        description= "Colormap for this channel",
        default='SINGLE_COLOR',
        update = update_func 
    )
    single_color : bpy.props.FloatVectorProperty(subtype="COLOR", min=0, max=1, update= update_func)

class SCENE_UL_Channels(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        self.use_filter_show =False #filtering is currently unsupported
        channel = item

        row1 = layout.row( align=True)
        split = row1.split(factor=0.9, align=True) # splitting to reduce the size of the color picker
        row = split.row(align=True)
        row.prop(channel, "name", text="", emboss=True)
        
        volumecheckbox = "OUTLINER_OB_VOLUME" if channel.volume else "VOLUME_DATA"
        row.prop(channel, "volume", text="", emboss=True, icon=volumecheckbox)
        
        surfcheckbox = "OUTLINER_OB_SURFACE" if channel.surface else "SURFACE_DATA"
        row.prop(channel, "surface", text="", emboss=True, icon=surfcheckbox)

        maskcheckbox = "OUTLINER_OB_POINTCLOUD" if channel.labelmask else "POINTCLOUD_DATA"
        row.prop(channel, "labelmask", text="", emboss=True, icon=maskcheckbox)

        row.separator()

        emitcheckbox = "OUTLINER_OB_LIGHT" if channel.emission else "LIGHT_DATA"
        row.prop(channel, "emission", text="", emboss=False, icon=emitcheckbox)

        row.prop(channel, "cmap", text="", emboss=False, icon_only=True)

        row = split.column(align=True)
        if channel.cmap == 'SINGLE_COLOR':
            row.prop(channel, "single_color", text="")
        else:
            row.label(text=channel.cmap.lower().capitalize())

    def invoke(self, context, event):
        pass   

INIT_COLORS = [
    (1.0, 1.0, 1.0),
    (0/255, 157/255, 224/255),
    (224/255, 0/255, 37/255),
    (224/255, 214/255, 0/255),
    (117/255, 0/255, 224/255),
    (0/255, 224/255, 87/255),
]

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
        channel.threshold=-1
        channel.cmap='SINGLE_COLOR'
        channel.single_color = INIT_COLORS[ch % len(INIT_COLORS)]

CLASSES = [ChannelDescriptor, SCENE_UL_Channels]