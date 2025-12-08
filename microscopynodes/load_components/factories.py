from ..handle_blender_structs.props import min_keys
from .load_volume import VolumeObject, VolumeIO
from .load_surfaces import SurfaceObject
from .load_labelmask import LabelmaskObject, LabelmaskIO


print('importing from factories')
from .test import Test
from .axes import Axes
from .holder_object import Holder
from .slice_cube_object import SliceCubeObject



OBJECT_MAP = {
    min_keys.HOLDER: Holder,
    min_keys.AXES: Axes,
    min_keys.VOLUME: VolumeObject,
    min_keys.SURFACE: SurfaceObject,
    min_keys.LABELMASK: LabelmaskObject,
    min_keys.SLICECUBE: SliceCubeObject,
}

IO_MAP = {
    min_keys.VOLUME: VolumeIO,
    min_keys.SURFACE: VolumeIO,
    min_keys.LABELMASK: LabelmaskIO,
}

def MinObjectFactory(min_key, obj=None):
    cls = OBJECT_MAP.get(min_key)
    if cls is None:
        raise ValueError(f"No object class defined for {min_key}")
    return cls(obj)

def DataIOFactory(min_key):
    cls = IO_MAP.get(min_key)
    if cls is None:
        raise ValueError(f"No IO class defined for {min_key}")
    return cls()


