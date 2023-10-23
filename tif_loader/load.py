import bpy
from bpy.props import (StringProperty, FloatProperty,
                        PointerProperty,
                        )

import subprocess
from pathlib import Path
import os
import pip
import numpy as np
import pyopenvdb as vdb
from mathutils import Color

def changePathTif(self, context):
    # infers metadata, resets to default if not found
    # the raise gets handled upstream, so only prints to cli, somehow.
    try: 
        import tifffile
        with tifffile.TiffFile(context.scene.path_tif) as ifstif:
            try:
                context.scene.axes_order = ifstif.series[0].axes.lower().replace('s', 'c')
            except Exception as e:
                print(e)
                context.scene.property_unset("axes_order")
            try:
                context.scene.xy_size = ifstif.pages[0].tags['XResolution'].value[1]/ifstif.pages[0].tags['XResolution'].value[0]
            except Exception as e:
                print(e)
                context.scene.property_unset("xy_size")
            try:
                context.scene.z_size = dict(ifstif.imagej_metadata)['spacing']
            except Exception as e:
                print(e)
                context.scene.property_unset("z_size")
    except Exception as e:
        context.scene.property_unset("axes_order")
        context.scene.property_unset("xy_size")
        context.scene.property_unset("z_size")
        raise
    return

bpy.types.Scene.path_tif = StringProperty(
        name="",
        description="tif file",
        update=changePathTif,
        options = {'TEXTEDIT_UPDATE'},
        default="",
        maxlen=1024,
        subtype='FILE_PATH')
    
bpy.types.Scene.axes_order = StringProperty(
        name="",
        description="axes order (only z is used currently)",
        default="zyx",
        maxlen=6)
    
bpy.types.Scene.xy_size = FloatProperty(
        name="",
        description="xy physical pixel size in micrometer",
        default=1.0)
    
bpy.types.Scene.z_size = FloatProperty(
        name="z_size",
        description="z physical pixel size in micrometer",
        default=1.0)



# note that this will write a dynamically linked vdb file, so rerunning the script on a file with the same name
# in the same folder, but with different data, will change the previously loaded data.

def make_and_load_vdb(imgdata, x_ix, y_ix, z_ix, axes_order, tif, z_scale, xy_scale):
    import tifffile
    chax =  axes_order.find('c')
    if chax == -1:
    #    if len(imgdata.shape) == len(axes_order):
        imgdata = imgdata[:,:,:,np.newaxis]
        axes_order = axes_order + "c"
        # break and try with last axis (works for RGB)

    grids = []
    for ch in range(imgdata.shape[chax]):
    #    chdata = imgdata[:,:,:,ch].astype(np.float64)
        chdata = imgdata.take(indices=ch,axis=chax)
        slice_axes = axes_order.replace("c","")
        # print(slice_axes)
        chdata = np.moveaxis(chdata, [slice_axes.find('x'),slice_axes.find('y'),slice_axes.find('z')],[0,1,2]).copy()
    #    chata = chdata
        
        grid = vdb.FloatGrid()
        grid.name = "channel " + str(ch)
        grid.copyFromArray(chdata)
        grids.append(grid)

    
    identifier = str(x_ix)+str(y_ix)+str(z_ix)
    (tif.parents[0] / "blender_volumes/").mkdir(exist_ok=True)
    fname = str(tif.parents[0] / f"blender_volumes/{tif.stem}_{identifier}.tif")
    vdb.write(fname, grids=grids)
    
    bpy.ops.object.volume_import(filepath=fname, align='WORLD', location=(0, 0, 0))
    # vdb.write(str(tif.with_name(tif.stem + identifier +".vdb")), grids=grids)
    
    # bpy.ops.object.volume_import(filepath=str(tif.with_name(tif.stem + identifier +".vdb")), align='WORLD', location=(0, 0, 0))
    return bpy.context.view_layer.objects.active

def load_tif(input_file, xy_scale, z_scale, axes_order):
    import tifffile
    tif = Path(input_file)
    init_scale = 0.02

    with tifffile.TiffFile(input_file) as ifstif:
        imgdata = ifstif.asarray()
        # metadata = dict(ifstif.imagej_metadata)
    if len(axes_order) != len(imgdata.shape):
        raise ValueError("axes_order length does not match data shape: " + str(imgdata.shape))

    imgdata = imgdata.astype(np.float64)
    # normalize entire space per axis
    if 'c' in axes_order:
        ch_first = np.moveaxis(imgdata, axes_order.find('c'), 0)
        for chix, chdata in enumerate(ch_first):
            ch_first[chix] /= np.max(chdata)
    else:
        imgdata /= np.max(imgdata)
    # raise Exception
    # (tif.parents[0] / "tmp_zstacker/").mkdir(exist_ok=True)

    # 2048 is maximum grid size for Eevee rendering, so grids are split for multiple
    xyz = [axes_order.find('x'),axes_order.find('y'),axes_order.find('z')]
    n_splits = [(imgdata.shape[dim] // 2048)+ 1 for dim in xyz]
    arrays = [imgdata]


    # Loops over all axes and splits based on length
    # reassembles in negative coordinates, parents all to a parent at (half_x, half_y, bottom) that is then translated to (0,0,0)
    volumes =[]
    a_chunks = np.array_split(imgdata, n_splits[0], axis=axes_order.find('x'))
    for a_ix, a_chunk in enumerate(a_chunks):
        b_chunks = np.array_split(a_chunk, n_splits[1], axis=axes_order.find('y'))
        for b_ix, b_chunk in enumerate(b_chunks):
            c_chunks = np.array_split(b_chunk, n_splits[2], axis=axes_order.find('z'))
            for c_ix, c_chunk in enumerate(reversed(c_chunks)):
                vol = make_and_load_vdb(c_chunk, a_ix, b_ix, c_ix, axes_order, tif, z_scale, xy_scale)
                bbox = np.array([c_chunk.shape[xyz[0]],c_chunk.shape[xyz[1]],c_chunk.shape[xyz[2]]])
                scale = np.array([1,1,z_scale/xy_scale])*init_scale
                vol.scale = scale
                print(c_ix, b_ix, a_ix)
                offset = np.array([a_ix,b_ix,c_ix])
                
                vol.location = tuple(offset*bbox*scale)
                volumes.append(vol)


    # recenter x, y, keep z at bottom
    center = np.array([0.5,0.5,0]) * np.array([c_chunk.shape[xyz[0]] * (len(a_chunks)), c_chunk.shape[xyz[1]] * (len(b_chunks)), c_chunk.shape[xyz[2]] * (len(c_chunks)*(z_scale/xy_scale))])
    container = bpy.ops.mesh.primitive_cube_add(location=tuple(center*init_scale))

    container = bpy.context.view_layer.objects.active
    container = init_container(container, volumes, imgdata, tif, xy_scale, z_scale, axes_order, init_scale)

    add_init_material(str(tif.name), volumes, imgdata, axes_order)
    
    print('done')
    return


def init_container(container, volumes, imgdata, tif, xy_scale, z_scale, axes_order, init_scale):
    container.name = str(tif.name) + " container" 
    container.data.name = str(tif.name) + " container" 

    for vol in volumes:
        vol.parent = container
        vol.matrix_parent_inverse = container.matrix_world.inverted()
    
    container.location = (0,0,0)
    bpy.ops.object.modifier_add(type='NODES')
    node_group = bpy.data.node_groups.new('GeometryNodes', 'GeometryNodeTree')  
    outnode = node_group.nodes.new('NodeGroupOutput')
    outnode.location = (800,0)
    container.modifiers[-1].node_group = node_group
    nodes = node_group.nodes
    links = node_group.links

    axnode = nodes.new('FunctionNodeInputVector')
    axnode.name = "n pixels"
    axnode.label = "n pixels"
    axnode.location = (-200, 100)
    for axix, ax in enumerate('xyz'):
        axnode.vector[axix] = imgdata.shape[axes_order.find(ax)]
    
    initscale_node = nodes.new('FunctionNodeInputVector')
    initscale_node.name = 'init_scale'
    initscale_node.label = "Scale on load"
    initscale_node.location = (-600, 150)
    initscale_node.vector = np.array([1,1,z_scale/xy_scale])*init_scale

    curscale_node = nodes.new("GeometryNodeObjectInfo")
    curscale_node.inputs[0].default_value = container
    curscale_node.location = (-600, -50)

    scale_node = nodes.new('FunctionNodeInputVector')
    scale_node.name = 'input_scale'
    scale_node.label = 'scale (µm/px)'
    scale_node.vector[0] = xy_scale
    scale_node.vector[1] = xy_scale
    scale_node.vector[2] = z_scale
    scale_node.location = (-400, -200)
    
    m_px_node = nodes.new('ShaderNodeVectorMath')
    m_px_node.operation = "MULTIPLY"
    m_px_node.name = 'm per px'
    m_px_node.label = 'm per pixel'
    m_px_node.location = (-400, 150)
    links.new(initscale_node.outputs[0], m_px_node.inputs[0])
    links.new(curscale_node.outputs[2], m_px_node.inputs[1])

    m_um_node = nodes.new('ShaderNodeVectorMath')
    m_um_node.operation = "DIVIDE"
    m_um_node.name = 'm per um'
    m_um_node.label = 'm per µm'
    m_um_node.location = (-400, 0)
    links.new(m_px_node.outputs[0], m_um_node.inputs[0])
    links.new(scale_node.outputs[0], m_um_node.inputs[1])

    axnode_um = nodes.new('ShaderNodeVectorMath')
    axnode_um.operation = "MULTIPLY"
    axnode_um.name = "size (µm)"
    axnode_um.label = "size (µm)"
    axnode_um.location = (0, 100)
    links.new(axnode.outputs[0], axnode_um.inputs[0])
    links.new(scale_node.outputs[0], axnode_um.inputs[1])
    
    axnode_bm = nodes.new('ShaderNodeVectorMath')
    axnode_bm.operation = "MULTIPLY"
    axnode_bm.name = "size (m)"
    axnode_bm.label = "size (m)"
    axnode_bm.location = (0, -50)
    links.new(axnode.outputs[0], axnode_bm.inputs[0])
    links.new(m_px_node.outputs[0], axnode_bm.inputs[1])

    return container


def add_init_material(name, volumes, imgdata, axes_order):
    # do not check whether it exists, so a new load will force making a new mat
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.remove(nodes.get("Principled BSDF"))

    lastnode, finalnode = None, None
    channels = imgdata.shape[axes_order.find('c')]
    if axes_order.find('c') == -1:
        channels = 1
    for channel in range(channels):
        node_attr = nodes.new(type='ShaderNodeAttribute')
        node_attr.location = (-500,-400*channel)
        #print(node_attr.outputs[0].default_value)
        node_attr.attribute_name = "channel " + str(channel)

        map_range = nodes.new(type='ShaderNodeMapRange')
        map_range.location = (-230, -400*channel)
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
            mix_shader = nodes.new('ShaderNodeMixShader')
            mix_shader.inputs.get("Fac").default_value = 1 - (channel/channels)
            mix_shader.location = (250 + 150 * channel,-400*channel)
            links.new(lastnode, mix_shader.inputs[1])
            links.new(princ_vol.outputs[0], mix_shader.inputs[2])
            lastnode = mix_shader.outputs[0]
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
