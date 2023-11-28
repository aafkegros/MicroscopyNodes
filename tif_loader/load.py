import bpy
from bpy.props import (StringProperty, FloatProperty,
                        PointerProperty
                        )

import subprocess
from pathlib import Path
import os
import pip
import numpy as np

from mathutils import Color
# try from . import nodes
from .nodes.nodeScale import scale_node_group
from .nodes.nodesBoolmultiplex import axes_multiplexer_node_group
from .nodes.nodeCrosshatch import crosshatch_node_group

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

bpy.types.Scene.TL_remake = bpy.props.BoolProperty(
    name = "TL_remake", 
    description = "Force remaking vdb files",
    default = False
    )

bpy.types.Scene.TL_preset_environment = bpy.props.BoolProperty(
    name = "TL_preset_environment", 
    description = "Set environment variables",
    default = True
    )

bpy.types.Scene.TL_otsu = bpy.props.BoolProperty(
    name = "TL_otsu", 
    description = "Otsu on load (slow for big data)",
    default = True
    )

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
        name="",
        description="z physical pixel size in micrometer",
        default=1.0)



# note that this will write a dynamically linked vdb file, so rerunning the script on a file with the same name
# in the same folder, but with different data, will change the previously loaded data.

def make_vdb(imgdata, x_ix, y_ix, z_ix, axes_order_in, tif, test=False):
    if test: 
        # pyopenvdb is not available outside of blender; for tests tifs are written
        # moving writing to a separate function would induce a very high RAM cost
        import tifffile
    else:
        import pyopenvdb as vdb

    
    axes_order = axes_order_in
    if axes_order.find('c') == -1:
        imgdata =  np.expand_dims(imgdata, axis=-1)
        axes_order = axes_order + "c"
    if axes_order.find('t') == -1:
        imgdata =  np.expand_dims(imgdata, axis=-1)
        axes_order = axes_order + "t"
    timefiles = []

    for t_ix, t in enumerate(range(imgdata.shape[axes_order.find('t')])):
        identifier = "x"+str(x_ix)+"y"+str(y_ix)+"z"+str(z_ix)
        (tif.parents[0] / f"blender_volumes/{identifier}/").mkdir(exist_ok=True,parents=True)
        fname = str(tif.parents[0] / f"blender_volumes/{identifier}/{tif.stem}t_{t_ix}.vdb")
        entry = {"name":f"{tif.stem}t_{t_ix}.vdb"}
        timefiles.append(entry)
        if (not os.path.isfile(fname)) or bpy.context.scene.TL_remake:
            frame = imgdata.take(indices=t,axis=axes_order.find('t'))
            channels = []
            for ch in range(imgdata.shape[axes_order.find('c')]):
                frame_axes = axes_order.replace("t","")
                chdata = frame.take(indices=ch,axis=frame_axes.find('c'))
                slice_axes = frame_axes.replace("c","")
                chdata = np.moveaxis(chdata, [slice_axes.find('x'),slice_axes.find('y'),slice_axes.find('z')],[0,1,2]).copy()
                channels.append(chdata)
            if test: 
                tifffile.imwrite(fname[:-4]+".tif", np.array(channels).astype(np.uint8) ,metadata={"axes":'cxyz'},photometric='minisblack', planarconfig='separate')
            else:
                grids = []
                for ch, chdata in enumerate(channels):
                    grid = vdb.FloatGrid()
                    grid.name = "channel " + str(ch)
                    grid.copyFromArray(chdata)
                    grids.append(grid)
                vdb.write(fname, grids=grids)
    directory = str(tif.parents[0] / f"blender_volumes/{identifier}")
    return directory, timefiles
    # bpy.ops.object.volume_import(filepath=fname,directory=str(tif.parents[0] / f"blender_volumes/{identifier}"), files=timefiles,use_sequence_detection=True , align='WORLD', location=(0, 0, 0))
    # return bpy.context.view_layer.objects.active

def unpack_tif(input_file, axes_order, test=False):
    import tifffile
    with tifffile.TiffFile(input_file) as ifstif:
        imgdata = ifstif.asarray()

    if len(axes_order) != len(imgdata.shape):
        raise ValueError("axes_order length does not match data shape: " + str(imgdata.shape))

    imgdata = imgdata.astype(np.float64)
    # normalize entire space per axis
    if 'c' in axes_order:
        ch_first = np.moveaxis(imgdata, axes_order.find('c'), 0)
        for chix, chdata in enumerate(ch_first):
            ch_first[chix] /= np.max(chdata)
        channels = imgdata.shape[axes_order.find('c')]
    else:
        imgdata /= np.max(imgdata)
        channels = 1

    # 2048 is maximum grid size for Eevee rendering, so grids are split for multiple
    xyz = [axes_order.find('x'),axes_order.find('y'),axes_order.find('z')]
    n_splits = [(imgdata.shape[dim] // 2048)+ 1 for dim in xyz]
    # otsu compute in z MIP
    otsus = [0] * channels
    if bpy.context.scene.TL_otsu:
        for channel in range(channels):
            if channels > 1:
                im = imgdata.take(indices=channel, axis=axes_order.find('c'))
            else:
                im = imgdata
            ch_axes = axes_order.replace("c","")
            z_MIP = np.amax(im, axis = ch_axes.find('z'))
            threshold_range = np.linspace(0,1,101)
            criterias = [compute_otsu_criteria(z_MIP, th) for th in threshold_range]
            otsus[channel] = threshold_range[np.argmin(criterias)]

    # Loops over all axes and splits based on length
    # reassembles in negative coordinates, parents all to a parent at (half_x, half_y, bottom) that is then translated to (0,0,0)
    volumes =[]
    vdb_files = {}
    a_chunks = np.array_split(imgdata, n_splits[0], axis=axes_order.find('x'))
    for a_ix, a_chunk in enumerate(a_chunks):
        b_chunks = np.array_split(a_chunk, n_splits[1], axis=axes_order.find('y'))
        for b_ix, b_chunk in enumerate(b_chunks):
            c_chunks = np.array_split(b_chunk, n_splits[2], axis=axes_order.find('z'))
            for c_ix, c_chunk in enumerate(reversed(c_chunks)):
                directory, time_vdbs = make_vdb(c_chunk, a_ix, b_ix, c_ix, axes_order, Path(input_file), test=test)
                vdb_files[(a_ix,b_ix,c_ix)] = {"directory" : directory, "files": time_vdbs}
    size_px = np.array([imgdata.shape[xyz[0]], imgdata.shape[xyz[1]], imgdata.shape[xyz[2]]])
    bbox_px = size_px//np.array(n_splits)
    return vdb_files, bbox_px, size_px, otsus

# currently not easily testable
def import_volumes(vdb_files, scale, bbox_px):
    volumes = []
    # necessary to support multi-file import
    bpy.types.Scene.files: CollectionProperty(
        type=bpy.types.OperatorFileListElement,
        options={'HIDDEN', 'SKIP_SAVE'},
    )
    for pos, vdbs in vdb_files.items():
        fname = str(Path(vdbs['directory'])/Path(vdbs['files'][0]['name']))
        bpy.ops.object.volume_import(filepath=fname,directory=vdbs['directory'], files=vdbs['files'],use_sequence_detection=True , align='WORLD', location=(0, 0, 0))
        vol = bpy.context.view_layer.objects.active
        vol.scale = scale
        vol.location = tuple(np.array(pos) * bbox_px *scale)
        for dim in range(3):
            vol.lock_location[dim] = True
            vol.lock_rotation[dim] = True
            vol.lock_scale[dim] = True
        volumes.append(vol)
    return volumes

def load(input_file, xy_scale, z_scale, axes_order):
    
    if bpy.context.scene.TL_preset_environment:
        preset_environment()
            
    tif = Path(input_file)

    vdb_files, bbox_px, size_px, otsus = unpack_tif(input_file, axes_order)

    init_scale = 0.02
    scale =  np.array([1,1,z_scale/xy_scale])*init_scale

    volumes = import_volumes(vdb_files, scale, bbox_px)

    # recenter x, y, keep z at bottom
    center = np.array([0.5,0.5,0]) * size_px
    container = bpy.ops.mesh.primitive_cube_add(location=tuple(center*scale))

    container = bpy.context.view_layer.objects.active
    container = init_container(container, volumes, size_px, tif, xy_scale, z_scale, axes_order, init_scale)

    add_init_material(str(tif.name), volumes, otsus, axes_order)
    return

def preset_environment():
    bpy.context.scene.eevee.volumetric_tile_size = '2'
    bpy.context.scene.cycles.preview_samples = 32
    bpy.context.scene.cycles.samples = 64
    bpy.context.scene.view_settings.view_transform = 'Standard'
    bpy.context.scene.eevee.volumetric_end = 500
    bpy.context.scene.eevee.taa_samples = 64

    # bpy.context.space_data.shading.use_scene_world = True

    try:
        bpy.data.worlds["World"].node_tree.nodes["Background"].inputs[0].default_value = (0, 0, 0, 1)
    except:
        pass
    return

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
    crosshatch.node_tree = crosshatch_node_group()
    crosshatch.location = (-50, -140)

    axes_select = nodes.new('GeometryNodeGroup')
    axes_select.node_tree = axes_multiplexer_node_group()
    axes_select.label = "Subselect axes"
    axes_select.width = 150
    axes_select.location = (-50, -320)

    scale_node = nodes.new('GeometryNodeGroup')
    scale_node.node_tree = scale_node_group()
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




