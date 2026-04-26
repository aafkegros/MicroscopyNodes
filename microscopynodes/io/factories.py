from ..handle_blender_structs.props import min_keys
from .labelmask import LabelmaskIO
from .volume import VolumeIO


IO_MAP = {
    min_keys.VOLUME: VolumeIO,
    min_keys.SURFACE: VolumeIO,
    min_keys.LABELMASK: LabelmaskIO,
}


def DataIOFactory(min_key):
    cls = IO_MAP.get(min_key)
    if cls is None:
        raise ValueError(f"No IO class defined for {min_key}")
    return cls()
