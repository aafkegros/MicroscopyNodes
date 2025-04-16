import bpy
import numpy as np


class ArrayOption(bpy.types.PropertyGroup):
    identifier: bpy.props.IntProperty()
    # NOTE: rescaled xy_size and z_size by MiN rescaling is done elsewhere.
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
    shape_str : bpy.props.StringProperty() # has getters and setters to map to tuple
    scale_str : bpy.props.StringProperty() # has getters and setters to map to tuple

    def len_axis(self, dim='c'):
        if dim not in bpy.context.scene.MiN_axes_order:
            return 1
        return self.shape()[bpy.context.scene.MiN_axes_order.find(dim)]

    def shape(self):
        return [int(dim) for dim in self.shape_str.split("|")]
    
    def set_shape(self, shape):
        self.shape_str = "|".join([str(dim) for dim in shape])

    def scale(self):
        return [int(dim) for dim in self.scale_str.split("|")]
    
    def set_scale(self, scale):
        self.scale_str = "|".join([str(dim) for dim in scale])


    def resize(self, scaling_vector):
        # resizes the description of the scale only - resizing of array is called in unpack_array
        self.is_rescaled = True

        newshape = []
        for dim, axislen in zip(bpy.context.scene.MiN_axes_order, self.shape()):
            if dim in 'xyz':
                newshape.append(int(axislen // scaling_vector['xyz'.find(dim)]))
            else:
                newshape.append(axislen)
        self.set_scale(np.array(self.scale()) * scaling_vector)
        self.set_shape(newshape)
    
    def size_bytes(self, exclude_dims=''):
        estimated_max_size = 1
        for dim in self.shape():
            estimated_max_size *= dim
        for dim in exclude_dims:
            estimated_max_size /= self.len_axis(dim)
        return estimated_max_size *4 # vdb's are 32 bit floats == 4 byte per voxel
    
    def size_gibibytes(self, exclude_dims=''):
        return self.size_bytes(exclude_dims) /  2**30

    def human_size(self, exclude_dims=''):
        return _human_size(self.size_bytes(exclude_dims))

def _human_size(bytes, units=[' bytes', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB', 'EiB']):
    return f"{bytes:.2f} {units[0]}" if bytes < 1024 else _human_size(bytes / 1024, units[1:])

def selected_array_option():
    try:
        return bpy.context.scene.MiN_array_options[int(bpy.context.scene.MiN_selected_array_option)]
    except IndexError:
        # retunadd_array_option(shape=(0,0,0))
        return None

def get_array_options(scene, context):
    # callback for enum
    if len(context.scene.MiN_array_options) == 0:
        return [('0','','','',0)]
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

def copy_array_option(copy_from):
    level = add_array_option()
    if 'shape' in copy_from: # shape is multivalue saved into a string
        level.set_shape(copy_from['shape'])
        copy_from.pop('shape')
    for key in copy_from.keys():
        try:
            setattr(level, key, getattr(copy_from, key))
        except AttributeError:
            setattr(level, key, copy_from[key])
    level.identifier = len(bpy.context.scene.MiN_array_options) - 1
    return level

def add_array_option(xy_size=1.0, z_size=1.0, shape=(1,1,1), copy_from=None, path="", store=""):
    level = bpy.context.scene.MiN_array_options.add()
    # make sure keys exist
    level.identifier = len(bpy.context.scene.MiN_array_options) - 1
    level.xy_size = xy_size
    level.z_size = z_size
    level.set_shape(shape)
    
    level.path = path
    level.store = store

    level.is_rescaled = False
    level.icon = ""
    level.ui_text = ""
    level.description = ""
    level.scale_str = "1|1|1"
    return level



