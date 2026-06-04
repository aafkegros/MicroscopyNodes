UNIT_VALUES = {
    "ANGSTROM": 1e-10,
    "NANOMETER": 1e-9,
    "MICROMETER": 1e-6,
    "MILLIMETER": 1e-3,
    "METER": 1.0,
    "AU": 1.0,
}

AUTO_IMPORT_SCALE = "AUTO_SCALE"
DEFAULT_IMPORT_SCALE = "MICROMETER_SCALE"
AUTO_TARGET_EXTENT_METERS = 10

IMPORT_SCALE_ITEMS = [
    ("NANOMETER_SCALE", "nm -> m", "Scales to 1 nm/blender-meter", "", 0),
    ("NANOMETER_DECIMETER_SCALE", "nm -> dm", "Scales to 1 nm/blender-decimeter", "", 1),
    ("NANOMETER_CENTIMETER_SCALE", "nm -> cm (Molecular Nodes)", "Scales to 1 nm/blender-centimeter", "", 2),
    ("MICROMETER_SCALE", "µm -> m", "Scales to 1 µm/blender-meter", "", 3),
    ("MICROMETER_DECIMETER_SCALE", "µm -> dm", "Scales to 1 µm/blender-decimeter", "", 4),
    ("MICROMETER_CENTIMETER_SCALE", "µm -> cm", "Scales to 1 µm/blender-centimeter", "", 5),
    ("MILLIMETER_SCALE", "mm -> m", "Scales to 1 mm/blender-meter", "", 6),
    ("MILLIMETER_DECIMETER_SCALE", "mm -> dm", "Scales to 1 mm/blender-decimeter", "", 7),
    ("MILLIMETER_CENTIMETER_SCALE", "mm -> cm", "Scales to 1 mm/blender-centimeter", "", 8),
    ("METER_SCALE", "m -> m", "Scales to 1 m/blender-meter", "", 9),
    ("METER_DECIMETER_SCALE", "m -> dm", "Scales to 1 m/blender-decimeter", "", 10),
    ("METER_CENTIMETER_SCALE", "m -> cm", "Scales to 1 m/blender-centimeter", "", 11),
    (AUTO_IMPORT_SCALE, "(auto)", "Chooses a scale from loaded datasets so they fit within a few Blender meters", "", -1),
]

IMPORT_SCALE_OUTPUT_SCALES = {
    "NANOMETER_SCALE": 1e-9,
    "NANOMETER_DECIMETER_SCALE": 1e-8,
    "NANOMETER_CENTIMETER_SCALE": 1e-7,
    "MICROMETER_SCALE": 1e-6,
    "MICROMETER_DECIMETER_SCALE": 1e-5,
    "MICROMETER_CENTIMETER_SCALE": 1e-4,
    "MILLIMETER_SCALE": 1e-3,
    "MILLIMETER_DECIMETER_SCALE": 1e-2,
    "MILLIMETER_CENTIMETER_SCALE": 1e-1,
    "METER_SCALE": 1.0,
    "METER_DECIMETER_SCALE": 1e1,
    "METER_CENTIMETER_SCALE": 1e2,
}


def import_scale_items():
    return list(IMPORT_SCALE_ITEMS)


def _holder_extent_units(holder):
    from mathutils import Vector

    corners = []
    for child in holder.children:
        child_corners = getattr(child, "bound_box", None)
        if not child_corners:
            continue
        for corner in child_corners:
            corners.append(child.matrix_local @ Vector(corner))

    if not corners:
        return 0.0

    return max(
        max(corner[axis] for corner in corners) - min(corner[axis] for corner in corners)
        for axis in range(3)
    )


def auto_import_scale_for_scene(scene):
    input_extents = []
    for obj in scene.objects:
        if "_MiN_dataset_input_scale" not in obj:
            continue
        extent_units = _holder_extent_units(obj)
        if extent_units > 0:
            input_extents.append(extent_units * float(obj["_MiN_dataset_input_scale"]))

    if not input_extents:
        return None

    return import_scale_for_extent(max(input_extents))


def update_import_scale(self, context):
    # This is essentially a placeholder for a more developed Scene Object that actually knows of its data
    from ..blender_objects.factories import MinObjectFactory
    from ..data_model import SceneModel
    from .min_keys import min_keys
    from .node_handling import get_min_gn

    if self.MiN_import_scale == AUTO_IMPORT_SCALE:
        import_scale = auto_import_scale_for_scene(context.scene)
        if import_scale is not None:
            self.MiN_import_scale = import_scale
        return

    scene_model = SceneModel(
        output_scale=self.MiN_import_scale,
        import_transform=self.MiN_import_loc,
    )
    for obj in context.scene.objects:
        if "_MiN_dataset_input_scale" not in obj:
            continue
        MinObjectFactory(min_keys.HOLDER, obj=obj).set_scene(scene_model)
        for child in obj.children:
            min_gn = get_min_gn(child)
            if min_gn is None or "axes" not in min_gn.name.lower():
                continue
            MinObjectFactory(min_keys.AXES, obj=child).set_scene(scene_model)


def import_scale_property(update=update_import_scale):
    from bpy.props import EnumProperty

    return EnumProperty(
        name="Microscopy scale -> Blender scale",
        items=import_scale_items(),
        description="Defines the scale transform from physical dataset units to Blender meters.",
        default=AUTO_IMPORT_SCALE,
        update=update,
    )


def register_import_scale_property(scene_type):
    scene_type.MiN_import_scale = import_scale_property()


def concrete_import_scale_items():
    return [item for item in IMPORT_SCALE_ITEMS if item[0] != AUTO_IMPORT_SCALE]


def output_scale_for_import_scale(import_scale):
    if isinstance(import_scale, (int, float)):
        return float(import_scale)
    if import_scale == AUTO_IMPORT_SCALE:
        return IMPORT_SCALE_OUTPUT_SCALES[DEFAULT_IMPORT_SCALE]
    if import_scale in IMPORT_SCALE_OUTPUT_SCALES:
        return IMPORT_SCALE_OUTPUT_SCALES[import_scale]
    return unit_value(import_scale.removesuffix("_SCALE"))


def import_scale_for_extent(input_extent_meters, target_extent_meters=AUTO_TARGET_EXTENT_METERS):
    if input_extent_meters <= 0:
        return DEFAULT_IMPORT_SCALE
    for name, *_ in concrete_import_scale_items():
        if input_extent_meters / IMPORT_SCALE_OUTPUT_SCALES[name] <= target_extent_meters:
            return name
    return concrete_import_scale_items()[-1][0]


def unit_label_from_value(unit):
    labels = {
        1e-10: "Å",
        1e-9: "nm",
        1e-6: "µm",
        1e-3: "mm",
        1.0: "m",
    }
    unit = float(unit)
    for value, label in labels.items():
        if abs(unit - value) <= abs(value) * 1e-6:
            return label
    return None


def unit_value(unit):
    if isinstance(unit, (int, float)):
        return float(unit)
    return UNIT_VALUES[parse_unit(unit)]


def unit_name(unit):
    value = unit_value(unit)
    for name, candidate in UNIT_VALUES.items():
        if candidate == value:
            return name
    return "AU"


def parse_unit(unit):
    if unit in ['A', 'Å', '\\u00C5', 'ANGSTROM', 'ÅNGSTROM', 'ÅNGSTRÖM', 'Ångstrom', 'angstrom', 'ångström', 'ångstrom']:
        return "ANGSTROM"
    if unit in ['nm', 'nanometer', 'NM', 'NANOMETER']:
        return "NANOMETER"
    if unit in ['\\u00B5m', 'micron', 'micrometer', 'microns', 'um', 'µm', 'MICROMETER']:
        return "MICROMETER"
    if unit in ['mm', 'millimeter', 'MM', 'MILLIMETER']:
        return "MILLIMETER"
    if unit in ['m', 'meter', 'M', 'METER']:
        return "METER"
    return "AU"
