import bpy
from .. import __package__
from bpy.props import StringProperty, BoolProperty, EnumProperty

def addon_preferences(
    context: bpy.types.Context | None = None,
) -> bpy.types.AddonPreferences:
    if context is None:
        context = bpy.context
    return context.preferences.addons[__package__].preferences

class MicroscopyNodesPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    import_scale_no_unit_spoof : EnumProperty(
        name = 'Microscopy -> Blender scale (needs metric pixel unit)',
        items=[
            ("DEFAULT", "px -> cm","Scales to 0.01 blender-m/pixel " ,"", 0),
        ],
        description= "Defines the scale transform from input space to Blender meters, pixel space is rescaled to isotropic in Z from relative pixel size.",
        default='DEFAULT',
    )
    import_scale : EnumProperty(
        name = "Microscopy -> Blender scale",
        items=[
            ("DEFAULT", "px -> cm","Scales to 0.01 blender-m/pixel " ,"", 0),
            ("NANOMETER_SCALE", "nm -> m", "Scales to 1 nm/blender-meter" ,"", 1),
            ("MICROMETER_SCALE", "µm -> m", "Scales to 1 µm/blender-meter" ,"", 2),
            ("MILLIMETER_SCALE", "mm -> m", "Scales to 1 mm/blender-meter " ,"", 3),
            ("METER_SCALE", "m -> m", "Scales to 1 m/blender-meter " ,"", 4),
            ("MOLECULAR_NODES", "nm -> cm (Molecular Nodes)", "Scales to 1 nm/blender-centimeter " ,"", 5),
        ], 
        description= "Defines the scale transform from input space to Blender meters, pixel space is rescaled to isotropic in Z from relative pixel size.",
        default='DEFAULT',
    )

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

    def draw(self, context):
        layout = self.layout
        # col = layout.column()
        # col.label(text="Transformations upon import:")
        # col.prop(self, "import_scale", emboss=False)
        # col.prop(self, "import_loc", emboss=False)

        


CLASSES = [MicroscopyNodesPreferences]