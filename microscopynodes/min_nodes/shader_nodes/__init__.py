print('importing shader nodes')
# from .cmap_nodes import *
# from .ops import *
from . import cmap_menus
# from .cmap_nodes import *
from . import ops
import bpy

print('hsould have imported')

def MIN_add_shader_node_menu(self, context):
    if "ShaderNodeTree" == bpy.context.area.spaces[0].tree_type:
        layout = self.layout
        layout.menu("MIN_MT_CMAPS", text="LUTs", icon="COLOR")


CLASSES = cmap_menus.CLASSES + ops.CLASSES