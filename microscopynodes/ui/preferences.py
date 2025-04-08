import bpy
from .. import __package__
from bpy.props import StringProperty, BoolProperty, EnumProperty
from pathlib import Path
import tempfile
import yaml


class MicroscopyNodesPreferences(bpy.types.AddonPreferences):
    from .ui.channel_list import ChannelDescriptor
    bl_idname = __package__

    def set_channels(self, context):
        while len(addon_preferences(bpy.context).channels)-1 < addon_preferences(bpy.context).n_default_channels:
            ch = len(addon_preferences(bpy.context).channels)
            channel = addon_preferences(bpy.context).channels.add()
            # This instantiates the keys!
            channel.ix = ch
            channel.volume = True
            channel.emission = True
            channel.surface = False
            channel.labelmask = False
            channel.materials = True
            channel.surf_resolution = 'ACTUAL'
            channel.threshold=-1
            channel.cmap='SINGLE_COLOR'
            channel.name = f"Channel {ch}"
            channel.single_color = INIT_COLORS[ch % len(INIT_COLORS)]
        while len(addon_preferences(bpy.context).channels)-1 >= addon_preferences(bpy.context).n_default_channels:
            addon_preferences(bpy.context).channels.remove(len(addon_preferences(bpy.context).channels)-1)

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
        default =6,
        update=set_channels
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
        if context.scene.MiN_yaml_preferences != "":
            row.label(text=f"Preferences are overriden from {context.scene.MiN_yaml_preferences}", icon="ERROR")
            row= layout.row()
            row.prop(bpy.context.scene, 'MiN_yaml_preferences', text="")
            row = layout.row()
            row.operator("microscopynodes.reset_yaml")
            return
        
        row.prop(self, 'cache_path', text='Data storage "Path" default:')
        row = layout.row()
        row.label(text='Data storage "Temporary" default:')
        row.label(text=tempfile.gettempdir())
        col = layout.column(align=True)
        col.label(text="Default channel settings to set for new files.")
        col.prop(self, "n_default_channels")
        col.template_list("SCENE_UL_Channels", "", self, "channels", bpy.context.scene, "MiN_ch_index", rows=6,sort_lock=True)
        col = layout.column()
        # col.label(text="Transformations upon import:")
        col.prop(self, "surf_resolution")
        col.prop(self, "invert_color")
        row = layout.row()
        row.prop(bpy.context.scene, 'MiN_remake', 
                        text = 'Overwrite files (debug, does not persist between sessions)', icon_value=0, emboss=True)


class ResetPreferenceYamlOperator(bpy.types.Operator):
    """ Unsets the preference yaml path """
    bl_idname ="microscopynodes.reset_yaml"
    bl_label = "Use Blender Preferences"

    def execute(self, context):
        context.scene.MiN_yaml_preferences = ""
        return {'FINISHED'}

class DictWithElements:
    # wraps a dictionary to access elements by dct.element - same method call as addonpreferences
    def __init__(self, dictionary):
        self.__dict__ = dictionary


def addon_preferences(context: bpy.types.Context | None = None):
    if context is None:
        context = bpy.context
    try:
        if hasattr(context, 'scene') and context.scene.MiN_yaml_preferences != "":
            with open(context.scene.MiN_yaml_preferences) as stream:
                return DictWithElements(yaml.safe_load(stream))
    except KeyError as e:
        print(e)
    try:
        return context.preferences.addons[__package__].preferences
    except KeyError:
        print('CANNOT FIND PREFERENCES')
        return None
    


INIT_COLORS = [
    (1.0, 1.0, 1.0),
    (0/255, 157/255, 224/255),
    (224/255, 0/255, 37/255),
    (224/255, 214/255, 0/255),
    (117/255, 0/255, 224/255),
    (0/255, 224/255, 87/255),
]


CLASSES = [MicroscopyNodesPreferences, ResetPreferenceYamlOperator]