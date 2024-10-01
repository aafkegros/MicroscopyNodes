import bpy
from .. import handle_blender_structs

def load_slice_cube(size_px, scale, slicecube=None):
    if slicecube is None:
        bpy.ops.mesh.primitive_cube_add(location=size_px*scale/2)
        slicecube = bpy.context.active_object
        slicecube.name = "slice cube"
        slicecube.scale = size_px * scale /2 

        bpy.ops.object.modifier_add(type='NODES')
        # slicecube.modifiers[-1].name = f"Slice cube empty modifier (for reloading)"
        slicecube.modifiers[-1].name = f"[Microscopy Nodes slicecube]"

        mat = bpy.data.materials.new(f'Slice Cube')
        mat.blend_method = "HASHED"
        mat.use_nodes = True
        mat.node_tree.nodes['Principled BSDF'].inputs.get("Alpha").default_value = 0
        slicecube.data.materials.append(mat)
    
    return slicecube
