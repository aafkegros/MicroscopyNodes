import bpy
from bpy.props import BoolProperty, EnumProperty, IntProperty, PointerProperty, StringProperty

from ..file_to_array import (
    change_array_option,
    change_channel_ax,
    change_path,
    get_array_options,
    selected_array_option,
)
from ..ui.channel_list import set_channels


def poll_empty(self, object):
    from .node_handling import get_min_gn

    try:
        if object is None:
            return False
        if object.type != 'EMPTY':
            return False
        scene = self if isinstance(self, bpy.types.Scene) else bpy.context.scene
        if scene.objects.get(object.name) != object:
            return False
        return any(get_min_gn(child) is not None for child in object.children)
    except (ReferenceError, AttributeError, TypeError):
        return False


def valid_reload_object(object, scene=None):
    try:
        scene = scene or bpy.context.scene
        return (
            object is not None
            and bpy.data.objects.get(object.name) == object
            and scene.objects.get(object.name) == object
            and poll_empty(scene, object)
        )
    except (ReferenceError, AttributeError, TypeError):
        return False


def ensure_valid_reload_object(scene=None):
    scene = scene or bpy.context.scene
    try:
        reload_object = scene.MiN_reload
    except ReferenceError:
        scene.MiN_reload = None
        return None
    if reload_object is not None and not valid_reload_object(reload_object, scene=scene):
        scene.MiN_reload = None
        return None
    return reload_object


def update_reload(self, context):
    ensure_valid_reload_object(self)


def switch_pixel_size(self, context):
    if bpy.context.scene.MiN_pixel_sizes_are_rescaled:
        bpy.context.scene.MiN_xy_size *= selected_array_option().scale()[0]
        bpy.context.scene.MiN_z_size *= selected_array_option().scale()[2]
    else:
        bpy.context.scene.MiN_xy_size /= selected_array_option().scale()[0]
        bpy.context.scene.MiN_z_size /= selected_array_option().scale()[2]


def register_scene_props():
    bpy.types.Scene.MiN_input_file = StringProperty(
        name="",
        description="image path, either to tif file, zarr root folder or zarr URL",
        update=change_path,
        options={'TEXTEDIT_UPDATE'},
        default="",
        maxlen=1024,
    )
    bpy.types.Scene.MiN_axes_order = StringProperty(
        name="",
        description="axes order (out of tzcyx)",
        default="",
        update=change_channel_ax,
        maxlen=6,
    )
    bpy.types.Scene.MiN_selected_array_option = EnumProperty(
        name="",
        description="Select the imported array or transform",
        items=get_array_options,
        update=change_array_option,
    )
    bpy.types.Scene.MiN_channel_nr = IntProperty(
        name="",
        default=0,
        update=set_channels,
    )
    bpy.types.Scene.MiN_reload = PointerProperty(
        name="",
        description="Reload data of Microscopy Nodes object.\nCan be used to replace deleted (temp) files, change resolution, or channel settings.\nUsage: Point to previously loaded microscopy data.",
        type=bpy.types.Object,
        poll=poll_empty,
        update=update_reload,
    )
    bpy.types.Scene.MiN_pixel_sizes_are_rescaled = BoolProperty(
        name="Show rescaled pixel size.",
        default=False,
        update=switch_pixel_size,
    )


def unregister_scene_props():
    for prop in (
        "MiN_input_file",
        "MiN_axes_order",
        "MiN_selected_array_option",
        "MiN_channel_nr",
        "MiN_reload",
        "MiN_pixel_sizes_are_rescaled",
    ):
        try:
            delattr(bpy.types.Scene, prop)
        except AttributeError:
            pass
