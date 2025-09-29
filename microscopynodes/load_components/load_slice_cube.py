import bpy
from .. import handle_blender_structs
import numpy as np

def load_slice_cube(size_px, scale, scale_factor, container, slicecube=None):
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
        if mat.node_tree.nodes.get("Principled BSDF") is None:
            mat.node_tree.nodes.new('ShaderNodeBsdfPrincipled')
        if mat.node_tree.nodes.get("Material Output") is None:
            out = mat.node_tree.nodes.new(type="ShaderNodeOutputMaterial")
            out.location = (400,0)
            mat.node_tree.links.new(
                mat.node_tree.nodes['Principled BSDF'].outputs['BSDF'],
                mat.node_tree.nodes['Material Output'].inputs['Surface']
            )
        mat.node_tree.nodes['Principled BSDF'].inputs.get("Alpha").default_value = 0
        slicecube.data.materials.append(mat)
    slicecube.parent = container
    slicecube.location =  np.array(slicecube.location)+ ( np.array(slicecube.location)*(scale_factor - 1))
    slicecube.scale = np.array(slicecube.scale)  * scale_factor
    return slicecube
