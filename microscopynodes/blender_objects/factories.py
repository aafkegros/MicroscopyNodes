from ..handle_blender_structs.props import min_keys
from .axes import Axes
from .holder import Holder
from .labelmask import LabelmaskObject
from .slice_cube import SliceCubeObject
from .surface import SurfaceObject
from .volume import VolumeObject

OBJECT_MAP = {
    min_keys.HOLDER: Holder,
    min_keys.AXES: Axes,
    min_keys.VOLUME: VolumeObject,
    min_keys.SURFACE: SurfaceObject,
    min_keys.LABELMASK: LabelmaskObject,
    min_keys.SLICECUBE: SliceCubeObject,
}

def MinObjectFactory(min_key, obj=None):
    cls = OBJECT_MAP.get(min_key)
    if cls is None:
        raise ValueError(f"No object class defined for {min_key}")
    return cls(obj)
