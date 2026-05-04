import bpy
from bpy.types import UIList
import os

# from ..min_nodes.shader_nodes import draw_category_menus

CMAP_ITEMS = [
    ("SINGLE_COLOR", "Single Color","Settable single color, will generate map from black to color" ,"MESH_PLANE", 0),
    ("VIRIDIS", "Viridis", "bids:viridis","IPO_LINEAR", 1),
    ("PLASMA", "Plasma","bids:plasma", "IPO_LINEAR", 2),
    ("COOLWARM", "Coolwarm","matplotlib:coolwarm", "LINCURVE", 3),
    ("ICEFIRE", "IceFire","seaborn:icefire", "LINCURVE", 4),
    ("TAB10", "Tab10","seaborn:tab10", "OUTLINER_DATA_POINTCLOUD", 5),
    ("BRIGHT", "Bright","tol:bright", "OUTLINER_DATA_POINTCLOUD", 6),
]

CMAP_NAMES = {
    "SINGLE_COLOR": "single_color",
    **{item[0]: item[2] for item in CMAP_ITEMS if item[0] != "SINGLE_COLOR"},
}
CMAP_ENUMS = {
    name: item[0]
    for item in CMAP_ITEMS
    for name in (item[2].lower(), item[2].split(":")[-1].lower())
}
SURF_RESOLUTION_NAMES = {
    "ACTUAL": 0,
    "FINE": 1,
    "MEDIUM": 2,
    "COARSE": 3,
}

def surf_resolution_value(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return SURF_RESOLUTION_NAMES.get(str(value).upper(), 0)

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
    surface : bpy.props.BoolProperty(description="Load isosurface object.\nAlso useful for binary masks", default=False, update=update_func )
    labelmask : bpy.props.BoolProperty(description="Do not use on regular images.\nLoads separate values in the mask as separate mesh objects", default=False, update=update_func )
    surf_resolution : bpy.props.IntProperty(default=0, min=0, max=3, update=update_func)
    # -- internal --
    cmap : bpy.props.EnumProperty(
        name = "Default Colormaps",
        items=CMAP_ITEMS, 
        description= "Colormap for this channel",
        default='SINGLE_COLOR',
        update = update_func 
    )
    single_color : bpy.props.FloatVectorProperty(subtype="COLOR_GAMMA", min=0, max=1, update= update_func)

    def to_channelviz(self):
        from ..data_model import ChannelVizModel
        from ..min_nodes.shader_nodes.handle_cmap import get_colormap

        return ChannelVizModel(
            ix=self.ix,
            name=self.name,
            volume=self.volume,
            surface=self.surface,
            labelmask=self.labelmask,
            emission=self.emission,
            surf_resolution=surf_resolution_value(self.surf_resolution),
            cmap=get_colormap(CMAP_NAMES.get(self.cmap, self.cmap), tuple(self.single_color)),
        )

    def from_channelviz(self, channelviz):
        self.ix = channelviz.ix
        self.name = channelviz.name
        self.volume = channelviz.volume
        self.surface = channelviz.surface
        self.labelmask = channelviz.labelmask
        self.emission = channelviz.emission
        self.surf_resolution = surf_resolution_value(channelviz.surf_resolution)

        cmap_data = channelviz.cmap.as_dict()
        cmap_name = str(cmap_data.get("name", cmap_data.get("identifier", ""))).lower()
        cmap_enum = CMAP_ENUMS.get(cmap_name) or self._matching_cmap_enum(channelviz)
        if cmap_enum:
            self.cmap = cmap_enum
        else:
            self.cmap = "SINGLE_COLOR"
            lut = [color for color in channelviz.cmap.lut(2) if list(color) != [0, 0, 0, 0]]
            if lut:
                self.single_color = tuple(lut[-1][:3])

    def _matching_cmap_enum(self, channelviz):
        from ..min_nodes.shader_nodes.handle_cmap import get_colormap

        target = channelviz.cmap.lut(8).tolist()
        for enum, cmap_name in CMAP_NAMES.items():
            if enum == "SINGLE_COLOR":
                continue
            try:
                if get_colormap(cmap_name).lut(8).tolist() == target:
                    return enum
            except Exception:
                pass
        return None

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

def set_channels(self, context):
    from .preferences import addon_preferences
    from ..data_model import ChannelVizModel

    bpy.context.scene.MiN_channelList.clear()
    preferences = addon_preferences(bpy.context)
    for ch in range(bpy.context.scene.MiN_channel_nr):
        channel = bpy.context.scene.MiN_channelList.add()
        if ch < len(preferences.channels):
            viz = preferences.channels[ch].to_channelviz()
        else:
            viz = ChannelVizModel(ix=ch)
        channel.from_channelviz(viz)
        
        

CLASSES = [ChannelDescriptor, SCENE_UL_Channels]
