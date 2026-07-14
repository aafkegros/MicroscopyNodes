import bpy
from bpy.props import StringProperty, BoolProperty, EnumProperty
from pathlib import Path
import tempfile
from types import SimpleNamespace

ADDON_PACKAGE = __package__.rsplit(".", 1)[0]


class MicroscopyNodesPreferences(bpy.types.AddonPreferences):
    from .channel_list import ChannelDescriptor
    bl_idname = ADDON_PACKAGE

    def set_channels(self, context):
        prefs = addon_preferences(bpy.context)
        while len(prefs.channels)-1 < prefs.n_default_channels:
            ch = len(prefs.channels)
            channel = prefs.channels.add()
            from ..data_model import ChannelVizModel
            from .channel_list import surf_resolution_value

            viz = ChannelVizModel(
                ix=ch,
                surf_resolution=surf_resolution_value(prefs.surf_resolution),
            )
            channel.from_channelviz(viz)
        while len(prefs.channels)-1 >= prefs.n_default_channels:
            prefs.channels.remove(len(prefs.channels)-1)

    n_default_channels : bpy.props.IntProperty(
        name = 'Defined default channels',
        min= 1,
        max=20,
        default =8,
        update=set_channels
    )
    extra_channel_slots : bpy.props.IntProperty(
        name='Extra channel slots',
        description='Additional channel slots to reserve beyond the current dataset channel count',
        min=0,
        max=20,
        default=2,
    )
    slice_cube_mode: EnumProperty(
        name="Slice cube mode",
        items=[
            (
                "GEOMETRY",
                "Geometry",
                "Slice cube masks data in Geometry Nodes. This is more flexible and allows for easy reloading of visible data. May cause jagged edges in dense renders.",
                "GEOMETRY_NODES",
                0,
            ),
            (
                "SHADER",
                "Shader",
                "Clip rendered materials with the Slice Cube shader node. More accurate box slicing, but strictly only on bounding boxes.",
                "MATERIAL",
                1,
            ),
        ],
        default="GEOMETRY",
    )

    
    cache_path: StringProperty(
        description = 'Only used if cache option is PATH',
        options = {'TEXTEDIT_UPDATE'},
        default = str(Path('~', '.microscopynodes').expanduser()),
        subtype = 'DIR_PATH',
    )
    cache_option: bpy.props.EnumProperty(
        name = "Data storage",
        items=[
            ("TEMPORARY", "Temporary","See the current temp path in Addon Preferences" ,"", 0),
            ("PATH", "Path", "","", 1),
            ("WITH_PROJECT", "With Project","", "", 2),
        ], 
        description= "Data is resaved into vdb files (large 32bit volume files) for volumes and isosurfaces, and smaller abc mesh files for labelmasks. Microscopy Nodes does not clean out the files.",
        default='TEMPORARY',
    )

    channels : bpy.props.CollectionProperty(type=ChannelDescriptor)
    
    surf_resolution : bpy.props.EnumProperty(
        name = "Meshing density of surfaces and masks",
        items=[
            ("0", "Actual","Takes the actual grid size, most accurate, but heavy on RAM." ,"EVENT_A", 0),
            ("1", "Fine", "Close to actual grid meshing, but more flexible" ,"EVENT_F", 1),
            ("2", "Medium", "Medium density mesh","EVENT_M", 2),
            ("3", "Coarse","Coarse mesh minimizes the RAM usage of surface encoding.", "EVENT_C", 3),
        ], 
        description= "Coarser will be less RAM intensive",
        default='0',
    )
    invert_color : bpy.props.BoolProperty(
        name="Invert Color",
        description = "Invert color lookup tables on load",
        default = False
    )

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        row.prop(self, 'cache_path', text='Data storage "Path" default:')
        row = layout.row()
        row.label(text='Data storage "Temporary" default:')
        row.label(text=tempfile.gettempdir())
        col = layout.column(align=True)
        col.label(text="Default channel settings to set for new files.")
        col.prop(self, "n_default_channels")
        col.prop(self, "extra_channel_slots")
        col.prop(self, "slice_cube_mode")
        col.template_list("SCENE_UL_Channels", "", self, "channels", bpy.context.scene, "MiN_ch_index", rows=6,sort_lock=True)
        col = layout.column()
        # col.label(text="Transformations upon import:")
        col.prop(self, "surf_resolution")
        col.prop(self, "invert_color")
        row = layout.row()
        row.prop(bpy.context.scene, 'MiN_remake', 
                        text = 'Overwrite files (debug, does not persist between sessions)', icon_value=0, emboss=True)


def addon_preferences(context: bpy.types.Context | None = None):
    global DEFAULT_PREFERENCES
    if context is None:
        context = bpy.context
    try:
        return context.preferences.addons[ADDON_PACKAGE].preferences
    except (AttributeError, KeyError):
        if DEFAULT_PREFERENCES is None:
            DEFAULT_PREFERENCES = SimpleNamespace(
                surf_resolution="0",
                invert_color=False,
                n_default_channels=8,
                extra_channel_slots=2,
                slice_cube_mode="GEOMETRY",
                cache_option="TEMPORARY",
                cache_path=str(Path("~", "microscopynodes_cache").expanduser()),
                channels=[default_channel(ix) for ix in range(8)],
            )
        return DEFAULT_PREFERENCES


def default_channel(ix=0):
    from ..data_model import ChannelVizModel
    viz = ChannelVizModel(ix=ix)
    return SimpleNamespace(
        ix=ix,
        name=viz.name,
        to_channelviz=lambda: ChannelVizModel(ix=ix),
    )


DEFAULT_PREFERENCES = None
    
CLASSES = [MicroscopyNodesPreferences]
