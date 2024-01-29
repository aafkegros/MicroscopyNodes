import bpy
import bpy
from bpy.props import (StringProperty, FloatProperty,
                        PointerProperty
                        )

from mathutils import Color
import numpy as np

from . import t2b_nodes
# print(dir(t2b_nodes))

def init_container(container, volumes, size_px, tif, xy_scale, z_scale, axes_order, init_scale):
    container.name = "container of " + str(tif.name) 
    container.data.name = "container of " + str(tif.name) 

    for vol in volumes:
        vol.parent = container
        vol.matrix_parent_inverse = container.matrix_world.inverted()
    
    container.location = (0,0,0)
    bpy.ops.object.modifier_add(type='NODES')
    node_group = bpy.data.node_groups.new('Container of ' + str(tif.name) , 'GeometryNodeTree')  
    container.modifiers[-1].node_group = node_group
    nodes = node_group.nodes
    links = node_group.links

    axnode = nodes.new('FunctionNodeInputVector')
    axnode.name = "n pixels"
    axnode.label = "n pixels"
    axnode.location = (-400, 200)
    for axix in range(len(size_px)):
        axnode.vector[axix] = size_px[axix]
    
    initscale_node = nodes.new('FunctionNodeInputVector')
    initscale_node.name = 'init_scale'
    initscale_node.label = "Scale transform on load"
    initscale_node.location = (-400, 0)
    initscale_node.vector = np.array([1,1,z_scale/xy_scale])*init_scale

    scale_node = nodes.new('FunctionNodeInputVector')
    scale_node.name = 'input_scale'
    scale_node.label = 'scale (µm/px)'
    scale_node.vector[0] = xy_scale
    scale_node.vector[1] = xy_scale
    scale_node.vector[2] = z_scale
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
    crosshatch.node_tree = t2b_nodes.crosshatch_node_group()
    crosshatch.location = (-50, -140)

    axes_select = nodes.new('GeometryNodeGroup')
    axes_select.node_tree = t2b_nodes.axes_multiplexer_node_group()
    axes_select.label = "Subselect axes"
    axes_select.width = 150
    axes_select.location = (-50, -320)

    scale_node = nodes.new('GeometryNodeGroup')
    scale_node.node_tree = t2b_nodes.scale_node_group()
    scale_node.width = 300
    scale_node.location = (200, 100)
    links.new(axnode_bm.outputs[0], scale_node.inputs.get('Size (m)'))
    links.new(axnode_um.outputs[0], scale_node.inputs.get('Size (µm)'))
    links.new(axes_select.outputs[0], scale_node.inputs.get('Axis Selection'))
    links.new(crosshatch.outputs[0], scale_node.inputs.get('Tick Geometry'))
    scale_node.inputs.get("Material").default_value = init_material_scalebar()
    
    node_group.interface.new_socket("Geometry",in_out="OUTPUT", socket_type='NodeSocketGeometry')
    outnode = nodes.new('NodeGroupOutput')
    outnode.location = (800,0)
    links.new(scale_node.outputs[0], outnode.inputs[0])

    return container


def add_init_material(name, volumes, otsus, axes_order):
    # do not check whether it exists, so a new load will force making a new mat
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.remove(nodes.get("Principled BSDF"))

    lastnode, finalnode = None, None
    channels = len(otsus)
    if axes_order.find('c') == -1:
        channels = 1
    
    for channel in range(channels):
        node_attr = nodes.new(type='ShaderNodeAttribute')
        node_attr.location = (-500,-400*channel)
        #print(node_attr.outputs[0].default_value)
        node_attr.attribute_name = "channel " + str(channel)

        map_range = nodes.new(type='ShaderNodeMapRange')
        map_range.location = (-230, -400*channel)

        # best threshold is the one minimizing the Otsu criteria
        map_range.inputs[1].default_value = otsus[channel]
        
        map_range.inputs[4].default_value = 0.1
        
        links.new(node_attr.outputs.get("Fac"), map_range.inputs.get("Value"))
        princ_vol = nodes.new(type='ShaderNodeVolumePrincipled')
        if channels > 1:
            c = Color()
            c.hsv = (channel/channels + 1/6) % 1, 1, 1
            princ_vol.inputs.get("Emission Color").default_value = (c.r, c.g, c.b, 1.0)
            
        princ_vol.inputs.get("Density").default_value = 0
        princ_vol.location = (0,-400*channel)
        links.new(map_range.outputs[0], princ_vol.inputs.get("Emission Strength"))

        if channel > 0: # last channel
            add_shader = nodes.new('ShaderNodeAddShader')
            # mix_shader.inputs.get("Fac").default_value = 1 - (channel/channels)
            add_shader.location = (250 + 150 * channel,-400*channel)
            links.new(lastnode, add_shader.inputs[0])
            links.new(princ_vol.outputs[0], add_shader.inputs[1])
            lastnode = add_shader.outputs[0]
        else:
            lastnode = princ_vol.outputs[0]

    nodes.get("Material Output").location = (350 + 150 * channels,-400*channel)
    links.new(lastnode, nodes.get("Material Output").inputs[1])
                
    # Assign it to object
    for vol in volumes:
        if vol.data.materials:
            vol.data.materials[0] = mat
        else:
            vol.data.materials.append(mat)

    return volumes

def init_material_scalebar():
    mat = bpy.data.materials.get("Scalebar")
    if mat:
        print('material already exists for scalebars')
        return mat
    mat = bpy.data.materials.new('Scalebar')
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

    out = nodes.get("Material Output")
    out.location = (650, 0)
    links.new(mix.outputs[0], out.inputs[0])
    return mat

# adapted from https://en.wikipedia.org/wiki/Otsu%27s_method
def compute_otsu_criteria(im, th):
    """Otsu's method to compute criteria."""
    # create the thresholded image
    # print(th)
    thresholded_im = np.zeros(im.shape)
    thresholded_im[im >= th] = 1

    # compute weights
    nb_pixels = im.size
    nb_pixels1 = np.count_nonzero(thresholded_im)
    weight1 = nb_pixels1 / nb_pixels
    weight0 = 1 - weight1

    # if one of the classes is empty, eg all pixels are below or above the threshold, that threshold will not be considered
    # in the search for the best threshold
    if weight1 == 0 or weight0 == 0:
        return np.inf

    # find all pixels belonging to each class
    val_pixels1 = im[thresholded_im == 1]
    val_pixels0 = im[thresholded_im == 0]

    # compute variance of these classes
    var1 = np.var(val_pixels1) if len(val_pixels1) > 0 else 0
    var0 = np.var(val_pixels0) if len(val_pixels0) > 0 else 0

    return weight0 * var0 + weight1 * var1
