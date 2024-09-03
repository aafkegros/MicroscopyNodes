import bpy
import numpy as np
from pathlib import Path

from ..handle_blender_structs import *
from .. import min_nodes



def load_axes(size_px, pixel_size, axes_obj=None):

    if axes_obj is not None:
        mod = get_min_gn(axes_obj)
        nodes = mod.node_group.nodes
        try:
            old_size_px = nodes['[Microscopy Nodes size_px]'].vector
            old_scale = nodes['[Microscopy Nodes scale]'].vector
            scale =  (np.array(old_size_px) / np.array(size_px)) * old_scale
        except KeyError as e:
            print(e)
            scale = default_scale(pixel_size)
        
        update_axes(nodes, size_px, pixel_size, scale)
        return axes_obj, scale

    center_loc = np.array([0.5,0.5,0]) # offset of center (center in x, y, z of obj)
    scale = default_scale(pixel_size)
    center =  tuple(center_loc * size_px*scale )
    axes_obj = init_axes(size_px, pixel_size, scale, center)
    return axes_obj,  scale

def default_scale(pixel_size):
    init_scale = 0.02
    scale =  np.array([1,1,pixel_size[-1]/pixel_size[0]])*init_scale
    return scale

def update_axes(nodes, size_px, pixel_size, scale):
    for k, v in zip(["size_px","pixel_size", "scale"], [size_px, pixel_size, scale]):
        nodes[f"[Microscopy Nodes {k}]"].vector = v
    return

def init_axes(size_px, pixel_size, scale, location):
    axes_obj = bpy.ops.mesh.primitive_cube_add(location=location)
    axes_obj = bpy.context.view_layer.objects.active
    axes_obj.data.name = 'axes'
    axes_obj.name = 'axes'

    bpy.ops.object.modifier_add(type='NODES')
    node_group = bpy.data.node_groups.new(f'axes', 'GeometryNodeTree')  
    axes_obj.modifiers[-1].name = f"[Microscopy Nodes axes]"
    axes_obj.modifiers[-1].node_group = node_group
    nodes = node_group.nodes
    links = node_group.links

    axnode = nodes.new('FunctionNodeInputVector')
    axnode.name = '[Microscopy Nodes size_px]'
    axnode.label = "n pixels"
    axnode.location = (-400, 200)
    for axix in range(len(size_px)):
        axnode.vector[axix] = size_px[axix]
    
    initscale_node = nodes.new('FunctionNodeInputVector')
    initscale_node.name = '[Microscopy Nodes scale]'
    initscale_node.label = "Scale transform on load"
    initscale_node.location = (-400, 0)
    initscale_node.vector = scale

    scale_node = nodes.new('FunctionNodeInputVector')
    scale_node.label = 'scale (µm/px)'
    scale_node.name = '[Microscopy Nodes pixel_size]'
    scale_node.vector = pixel_size
    scale_node.location = (-400, -200)

    axnode_um = nodes.new('ShaderNodeVectorMath')
    axnode_um.operation = "MULTIPLY"
    axnode_um.name = "size (µm)"
    axnode_um.label = "size (µm)"
    axnode_um.location = (-50, 200)
    links.new(axnode.outputs[0], axnode_um.inputs[0])
    links.new(scale_node.outputs[0], axnode_um.inputs[1])
    
    axnode_bm = nodes.new('ShaderNodeVectorMath')
    axnode_bm.operation = "MULTIPLY"
    axnode_bm.name = "size (m)"
    axnode_bm.label = "size (m)"
    axnode_bm.location = (-50, 50)
    links.new(axnode.outputs[0], axnode_bm.inputs[0])
    links.new(initscale_node.outputs[0], axnode_bm.inputs[1])

    crosshatch = nodes.new('GeometryNodeGroup')
    crosshatch.node_tree = min_nodes.crosshatch_node_group()
    crosshatch.location = (-50, -140)

    axes_select = nodes.new('GeometryNodeGroup')
    axes_select.node_tree = min_nodes.axes_multiplexer_node_group()
    axes_select.label = "Subselect axes"
    axes_select.name = "Axis Selection"
    axes_select.width = 150
    axes_select.location = (-50, -320)

    scale_node = nodes.new('GeometryNodeGroup')
    scale_node.node_tree = min_nodes.scale_node_group()
    scale_node.width = 300
    scale_node.location = (200, 100)
    scale_node.inputs.get("µm per tick").default_value = max(1, size_px[0]//10)
    links.new(axnode_bm.outputs[0], scale_node.inputs.get('Size (m)'))
    links.new(axnode_um.outputs[0], scale_node.inputs.get('Size (µm)'))
    links.new(axes_select.outputs[0], scale_node.inputs.get('Axis Selection'))
    # links.new(crosshatch.outputs[0], scale_node.inputs.get('Tick Geometry'))
    scale_node.inputs.get("Material").default_value = init_material_axes()
    
    node_group.interface.new_socket("Geometry",in_out="OUTPUT", socket_type='NodeSocketGeometry')
    outnode = nodes.new('NodeGroupOutput')
    outnode.location = (800,0)
    links.new(scale_node.outputs[0], outnode.inputs[0])

    if axes_obj.data.materials:
        axes_obj.data.materials[0] = init_material_axes()
    else:
        axes_obj.data.materials.append(init_material_axes())

    for dim in range(3):
        axes_obj.lock_location[dim] = True
        axes_obj.lock_rotation[dim] = True
        axes_obj.lock_scale[dim] = True
    return axes_obj

def init_material_axes():
    mat = bpy.data.materials.get("axes")
    if mat:
        return mat
    mat = bpy.data.materials.new('axes')
    mat.blend_method = "BLEND"
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    nodes.remove(nodes.get("Principled BSDF"))

    gridnormal =  nodes.new("ShaderNodeAttribute")
    gridnormal.attribute_name = 'orig_normal'
    gridnormal.location = (-800, -100)
    
    viewvec =  nodes.new("ShaderNodeCameraData")
    viewvec.location = (-800, -300)

    vectransform =  nodes.new("ShaderNodeVectorTransform")
    vectransform.location = (-600, -300)
    vectransform.vector_type = 'VECTOR'
    vectransform.convert_from = "CAMERA"
    vectransform.convert_to = "OBJECT"
    links.new(viewvec.outputs[0], vectransform.inputs[0])

    dot = nodes.new("ShaderNodeVectorMath")
    dot.operation = "DOT_PRODUCT"
    dot.location = (-400, -200)
    links.new(gridnormal.outputs[1], dot.inputs[0])
    links.new(vectransform.outputs[0], dot.inputs[1])

    lesst = nodes.new("ShaderNodeMath")
    lesst.operation = "LESS_THAN"
    lesst.location =(-200, -200)
    links.new(dot.outputs.get("Value"), lesst.inputs[0])
    lesst.inputs[1].default_value = 0
    
    culling_bool =  nodes.new("ShaderNodeAttribute")
    culling_bool.attribute_name = 'frontface culling'
    culling_bool.location = (-200, -400)
    
    comb = nodes.new("ShaderNodeMath")
    comb.operation = "ADD"
    comb.location =(0, -300)
    links.new(lesst.outputs[0], comb.inputs[0])
    links.new(culling_bool.outputs[2], comb.inputs[1])

    and_op = nodes.new("ShaderNodeMath")
    and_op.operation = "COMPARE"
    and_op.location =(200, -300)
    links.new(comb.outputs[0], and_op.inputs[0])
    and_op.inputs[1].default_value = 2.0
    and_op.inputs[2].default_value = 0.01
    
    colorattr =  nodes.new("ShaderNodeAttribute")
    colorattr.attribute_name = 'color_scale_bar'
    colorattr.location = (200, 150)
    
    trbsdf = nodes.new("ShaderNodeBsdfTransparent")
    trbsdf.location = (200, -100)

    mix = nodes.new("ShaderNodeMixShader")
    mix.location = (450, 0)
    links.new(colorattr.outputs[0], mix.inputs[1])
    links.new(trbsdf.outputs[0], mix.inputs[2])
    links.new(and_op.outputs[0], mix.inputs[0])

    if nodes.get("Material Output") is None:
            outnode = nodes.new(type='ShaderNodeOutputMaterial')
            outnode.name = 'Material Output'
    out = nodes.get("Material Output")
    out.location = (650, 0)
    links.new(mix.outputs[0], out.inputs[0])

    return mat
