import bpy


class ArrayOption(bpy.types.PropertyGroup):
    identifier: bpy.props.IntProperty()
    xy_size: bpy.props.FloatProperty()
    z_size: bpy.props.FloatProperty()

    # for generated scales
    is_rescaled: bpy.props.FloatProperty()

    # UI
    icon: bpy.props.StringProperty()
    ui_text: bpy.props.StringProperty()
    description: bpy.props.StringProperty()

    # zarr
    path: bpy.props.StringProperty() # internal path
    store: bpy.props.StringProperty() # zarr store

    # |-separated lists
    ch_names : bpy.props.StringProperty() # optional
    shape_str : bpy.props.StringProperty()

    def len_axis(self, dim='c'):
        if dim not in bpy.context.scene.MiN_axes_order:
            return 1
        return self.shape()[bpy.context.scene.MiN_axes_order.find(dim)]

    def shape(self):
        return [int(dim) for dim in self.shape_str.split("|")]
    
    def set_shape(self, shape):
        self.shape_str = "|".join([str(dim) for dim in shape])

def get_array_options(scene, context):
    items = []
    for ix, option in enumerate(context.scene.MiN_array_options):
        items.append((
            str(ix),
            option.ui_text,
            option.description,
            option.icon,
            ix
        ))
    return items

