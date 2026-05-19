import bpy


class ArrayOption(bpy.types.PropertyGroup):
    identifier: bpy.props.IntProperty()
    xy_size: bpy.props.FloatProperty()
    z_size: bpy.props.FloatProperty()
    is_rescaled: bpy.props.BoolProperty(default=False)
    icon: bpy.props.StringProperty()
    ui_text: bpy.props.StringProperty()
    description: bpy.props.StringProperty()
    shape_str: bpy.props.StringProperty()
    human_size: bpy.props.StringProperty()
    path: bpy.props.StringProperty()

    def len_axis(self, dim='c'):
        axes_order = bpy.context.scene.MiN_axes_order
        if dim not in axes_order:
            return 1
        return self.shape()[axes_order.find(dim)]

    def shape(self):
        if not self.shape_str:
            return [1]
        return [int(dim) for dim in self.shape_str.split("|")]

    def set_shape(self, shape):
        self.shape_str = "|".join([str(int(dim)) for dim in shape])

    def scale(self):
        return [1, 1, 1]

    def from_dataset(self, dataset_model, identifier=0, axes_order=None):
        channel_data = dataset_model.channels[0].data
        axes_order = axes_order or channel_data.axes_order
        data_shape = dict(zip(channel_data.axes_order, channel_data.data_shape))
        shape = []
        for dim in axes_order:
            if dim == 'c':
                shape.append(len(dataset_model.channels))
            else:
                shape.append(data_shape.get(dim, 1))

        affine = channel_data.affine_matrix
        self.identifier = identifier
        self.xy_size = float(affine[0][0])
        self.z_size = float(affine[2][2])
        self.is_rescaled = _is_rescaled(channel_data)
        self.path = dataset_model.name or ""
        self.set_shape(shape)
        self.human_size = _human_dataset_size(dataset_model)
        self.refresh_ui()
        return self

    def refresh_ui(self):
        self.ui_text = f"{self.shape()} (up to {self.human_size})"
        if self.path:
            self.ui_text = f"{self.path}: {self.ui_text}"
        self.description = "Native dataset option."
        self.icon = 'VOLUME_DATA' if self.is_rescaled else 'OUTLINER_OB_VOLUME'
        return self


def selected_array_option():
    try:
        return bpy.context.scene.MiN_array_options[int(bpy.context.scene.MiN_selected_array_option)]
    except (IndexError, ValueError):
        return None


def get_array_options(scene, context):
    if len(context.scene.MiN_array_options) == 0:
        return [('0', '', '', '', 0)]
    return [
        (
            str(ix),
            option.ui_text,
            option.description,
            option.icon,
            ix,
        )
        for ix, option in enumerate(context.scene.MiN_array_options)
    ]


def _human_dataset_size(dataset_model):
    return _human_size(sum(_channel_size_bytes(channel) for channel in dataset_model.channels))


def _is_rescaled(channel_data):
    return tuple(channel_data.min_rescale_xyz) != (1.0, 1.0, 1.0)


def _channel_size_bytes(channel_model):
    dtype_size = getattr(channel_model.data.data_dtype, "itemsize", 4)
    size = dtype_size
    for dim in channel_model.data.data_shape:
        size *= dim
    return size


def _human_size(size_bytes, units=('bytes', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB')):
    size = float(size_bytes)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.2f} {unit}"
        size /= 1024
