from .base import *
from pathlib import Path
from ..handle_blender_structs.props import min_keys

class Holder(MiNObject):
    min_type = min_keys.HOLDER

    def set_settings(self, dataset_model):
        self.object.name = dataset_model.name
