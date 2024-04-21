import bpy
from mathutils import Color
from pathlib import Path
import numpy as np

from .load_generic import init_holder
from ..handle_blender_structs import *


def array_to_vdb_files(imgdata, test=False):
    # 2048 is maximum grid size for Eevee rendering, so grids are split for multiple
    axes_order = bpy.context.scene.axes_order
    n_splits = [(imgdata.shape[dim] // 2048)+ 1 for dim in [axes_order.find('x'),axes_order.find('y'),axes_order.find('z')]]
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
                directory, time_vdbs = make_vdb(c_chunk, a_ix, b_ix, c_ix, axes_order, test=test)
                vdb_files[(a_ix,b_ix,c_ix)] = {"directory" : directory, "files": time_vdbs}
    bbox_px = np.array([imgdata.shape[axes_order.find('x')], imgdata.shape[axes_order.find('y')], imgdata.shape[axes_order.find('z')]])//np.array(n_splits)
    return vdb_files, bbox_px

def make_vdb(imgdata, x_ix, y_ix, z_ix, axes_order_in, test=False):
    if test: 
        # pyopenvdb is not available outside of blender; for tests tifs are written
        # moving writing to a separate function would induce a very high RAM cost
        import tifffile
    else:
        import pyopenvdb as vdb
    origfname = Path(bpy.context.scene.path_tif).stem

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
        (Path(bpy.context.scene.T2B_cache_dir)/f"{identifier}").mkdir(exist_ok=True,parents=True)
        fname = (Path(bpy.context.scene.T2B_cache_dir)/f"{identifier}"/f"{origfname}t_{t_ix}.vdb")
        entry = {"name":f"{origfname}t_{t_ix}.vdb"}
        timefiles.append(entry)
        if not fname.exists() or bpy.context.scene.TL_remake:
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
                vdb.write(str(fname), grids=grids)
    directory = str(Path(bpy.context.scene.T2B_cache_dir)/f"{identifier}")
    return directory, timefiles

def volume_material(volumes, ch_names, otsus):
    # do not check whether it exists, so a new load will force making a new mat
    mat = bpy.data.materials.new('volume')
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    if nodes.get("Principled BSDF") is not None:
        nodes.remove(nodes.get("Principled BSDF"))
    if nodes.get("Principled Volume") is not None:
        nodes.remove(nodes.get("Principled Volume"))

    lastnode, finalnode = None, None
    channels = len(otsus)
    if bpy.context.scene.axes_order.find('c') == -1:
        channels = 1
    
    for channel in ch_names:
        node_attr = nodes.new(type='ShaderNodeAttribute')
        node_attr.location = (-500,-400*channel)
        node_attr.attribute_name = "channel " + str(channel)

        map_range = nodes.new(type='ShaderNodeMapRange')
        map_range.location = (-230, -400*channel)
        # best threshold is the one minimizing the Otsu criteria
        map_range.inputs[1].default_value = otsus[channel]
        map_range.inputs[4].default_value = 0.1
        
        links.new(node_attr.outputs.get("Fac"), map_range.inputs.get("Value"))
        princ_vol = nodes.new(type='ShaderNodeVolumePrincipled')
        princ_vol.inputs.get("Emission Color").default_value = get_cmap('hue-wheel', maxval=channels)[channel]
        princ_vol.inputs.get("Color").default_value = get_cmap('hue-wheel', maxval=channels)[channel]
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
                
    # Assign it to volumes - not fully necessary, but nice to have if people want to mess around in the cache
    for vol in volumes:
        if vol.data.materials:
            vol.data.materials[0] = mat
        else:
            vol.data.materials.append(mat)

    return mat


def load_volume(volume_array, otsus, scale, cache_coll, base_coll):
    # consider checking whether all channels are present in vdb for remaking?
    collection_activate(*cache_coll)
    vol_collection, _ = make_subcollection('volumes')
    volumes = []

    ch_names = [ix for ix, val in enumerate(otsus) if val > -1]

    vdb_files, bbox_px = array_to_vdb_files(volume_array)
    
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
        vol.data.frame_start = 0
        volumes.append(vol)
    
    collection_activate(*base_coll)
    vol_obj = init_holder('volume',[vol_collection], [volume_material(volumes, ch_names, otsus)])
    return vol_obj, vol_collection
