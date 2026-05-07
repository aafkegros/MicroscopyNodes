import bpy
from .. import __package__
from bpy.props import StringProperty, BoolProperty, EnumProperty
from pathlib import Path
import tempfile
from types import SimpleNamespace


class MicroscopyNodesPreferences(bpy.types.AddonPreferences):
    from .ui.channel_list import ChannelDescriptor
    bl_idname = __package__

    def set_channels(self, context):
        prefs = addon_preferences(bpy.context)
        while len(prefs.channels)-1 < prefs.n_default_channels:
            ch = len(prefs.channels)
            channel = prefs.channels.add()
            from .data_model import ChannelVizModel
            from .ui.channel_list import surf_resolution_value

            viz = ChannelVizModel(
                ix=ch,
                surf_resolution=surf_resolution_value(prefs.surf_resolution),
            )
            channel.from_channelviz(viz)
        while len(prefs.channels)-1 >= prefs.n_default_channels:
            prefs.channels.remove(len(prefs.channels)-1)

    import_scale_no_unit_spoof : EnumProperty(
        name = 'Microscopy scale -> Blender scale (needs metric pixel unit)',
        items=[
            ("DEFAULT", "px -> cm","Scales to 0.01 blender-m/pixel in XY, rescales Z to isotropic pixel size" ,"", 0),
        ],
        description= "Defines the scale transform from input space to Blender meters, pixel space is rescaled to isotropic in Z from relative pixel size.",
        default='DEFAULT',
    )
    import_scale : EnumProperty(
        name = "Microscopy scale -> Blender scale",
        items=[
            ("DEFAULT", "px -> cm","Scales to 0.01 blender-m/pixel in XY, rescales Z to isotropic pixel size" ,"", 0),
            ("NANOMETER_SCALE", "nm -> m", "Scales to 1 nm/blender-meter" ,"", 1),
            ("MICROMETER_SCALE", "µm -> m", "Scales to 1 µm/blender-meter" ,"", 2),
            ("MILLIMETER_SCALE", "mm -> m", "Scales to 1 mm/blender-meter " ,"", 3),
            ("METER_SCALE", "m -> m", "Scales to 1 m/blender-meter " ,"", 4),
            ("MOLECULAR_NODES", "nm -> cm (Molecular Nodes)", "Scales to 1 nm/blender-centimeter " ,"", 5),
        ], 
        description= "Defines the scale transform from input space to Blender meters, pixel space is rescaled to isotropic in Z from relative pixel size.",
        default='DEFAULT',
    )
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
    
    import_loc : EnumProperty(
        name = 'Import location',
        items=[
            ("XY_CENTER", "XY Center","Center volume in XY" ,"", 0),
            ("XYZ_CENTER", "XYZ Center","Center volume in XYZ" ,"", 1),
            ("ZERO", "Origin"," Volume origin at world origin" ,"", 2),
        ], 
        description= "Defines the coordinate translation after import from input space to Blender meters",
        default='XY_CENTER',
    )
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
        return context.preferences.addons[__package__].preferences
    except (AttributeError, KeyError):
        print('CANNOT FIND PREFERENCES')
        if DEFAULT_PREFERENCES is None:
            DEFAULT_PREFERENCES = SimpleNamespace(
                import_scale="DEFAULT",
                import_scale_no_unit_spoof="DEFAULT",
                import_loc="XY_CENTER",
                surf_resolution="0",
                invert_color=False,
                n_default_channels=8,
                extra_channel_slots=2,
                cache_option="TEMPORARY",
                cache_path=str(Path("~", ".microscopynodes").expanduser()),
                channels=[default_channel(ix) for ix in range(8)],
            )
        return DEFAULT_PREFERENCES


def default_channel(ix=0):
    from .data_model import ChannelVizModel
    viz = ChannelVizModel(ix=ix)
    return SimpleNamespace(
        ix=ix,
        name=viz.name,
        to_channelviz=lambda: ChannelVizModel(ix=ix),
    )


DEFAULT_PREFERENCES = None
    
CLASSES = [MicroscopyNodesPreferences]
