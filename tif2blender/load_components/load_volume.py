import bpy
from mathutils import Color
from pathlib import Path
import numpy as np

from .load_generic import init_holder
from ..handle_blender_structs import *
from .. import t2b_nodes


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
                vdb_files[(a_ix,b_ix,c_ix)] = {"directory" : directory, "channels": time_vdbs}
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
    for ch in range(imgdata.shape[axes_order.find('c')]):
        timefiles.append([])

    for t_ix, t in enumerate(range(imgdata.shape[axes_order.find('t')])):
        identifier = "x"+str(x_ix)+"y"+str(y_ix)+"z"+str(z_ix)
        (Path(bpy.context.scene.T2B_cache_dir)/f"{identifier}").mkdir(exist_ok=True,parents=True)
        frame = imgdata.take(indices=t,axis=axes_order.find('t'))
        channels = []
        for ch in range(imgdata.shape[axes_order.find('c')]):
            fname = (Path(bpy.context.scene.T2B_cache_dir)/f"{identifier}"/f"Channel {ch}_{t}.vdb")
            entry = {"name":str(fname.name)}
            timefiles[ch].append(entry)
            if not fname.exists() or bpy.context.scene.TL_remake:
                frame_axes = axes_order.replace("t","")
                chdata = frame.take(indices=ch,axis=frame_axes.find('c'))

                slice_axes = frame_axes.replace("c","")
                chdata = np.moveaxis(chdata, [slice_axes.find('x'),slice_axes.find('y'),slice_axes.find('z')],[0,1,2]).copy()
                
                grid = vdb.FloatGrid()
                grid.name = f"data_channel_{ch}"
                grid.copyFromArray(chdata)
                vdb.write(str(fname), grids=[grid])

    directory = str(Path(bpy.context.scene.T2B_cache_dir)/f"{identifier}")
    return directory, timefiles



def volume_material(vol, otsus, ch, channels):
    # do not check whether it exists, so a new load will force making a new mat
    mat = bpy.data.materials.new(f'channel {ch}')
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    if nodes.get("Principled BSDF") is not None:
        nodes.remove(nodes.get("Principled BSDF"))
    if nodes.get("Principled Volume") is not None:
        nodes.remove(nodes.get("Principled Volume"))

    node_attr = nodes.new(type='ShaderNodeAttribute')
    node_attr.location = (-500, 0)
    node_attr.attribute_name = f'data_channel_{ch}'

    bound_map_range_node = nodes.new('ShaderNodeGroup')
    bound_map_range_node.node_tree = t2b_nodes.bounded_map_range_node_group()
    bound_map_range_node.width = 300
    bound_map_range_node.location = (-250, 0)
    bound_map_range_node.label = "Brightness & Contrast"
    # best threshold is the one minimizing the Otsu criteria
    bound_map_range_node.inputs.get('Minimum').default_value = otsus[ch]
    links.new(node_attr.outputs.get("Fac"), bound_map_range_node.inputs.get("Data"))

    color = nodes.new("ShaderNodeRGB")
    color.outputs[0].default_value = get_cmap('hue-wheel', maxval=channels)[ch]
    color.location = (-250, 200)

    emit = nodes.new(type='ShaderNodeEmission')
    emit.location = (150,0)
    links.new(color.outputs[0], emit.inputs.get('Color'))
    links.new(bound_map_range_node.outputs[0], emit.inputs.get('Strength'))


    adsorb = nodes.new(type='ShaderNodeVolumeAbsorption')
    adsorb.location = (150,-200)
    links.new(color.outputs[0], adsorb.inputs.get('Color'))
    links.new(bound_map_range_node.outputs[0], adsorb.inputs.get('Density'))
    scatter = nodes.new(type='ShaderNodeVolumeScatter')
    scatter.location = (150,-300)
    links.new(color.outputs[0], scatter.inputs.get('Color'))
    links.new(bound_map_range_node.outputs[0], scatter.inputs.get('Density'))

    add = nodes.new(type='ShaderNodeAddShader')
    add.location = (350, -300)
    links.new(adsorb.outputs[0], add.inputs[0])
    links.new(scatter.outputs[0], add.inputs[1])

    nodes.get("Material Output").location = (400,00)
    links.new(emit.outputs[0], nodes.get("Material Output").inputs.get('Volume'))
    
    # Assign it to volume - not fully necessary, but nice to have if people want to mess around in the cache
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
    print('made vdb files')
    # necessary to support multi-file import
    bpy.types.Scene.files: CollectionProperty(
        type=bpy.types.OperatorFileListElement,
        options={'HIDDEN', 'SKIP_SAVE'},
    )
    
    for pos, vdbs in vdb_files.items():
        for ch_files in vdbs['channels']:
            bpy.ops.object.volume_import(filepath=ch_files[0]['name'],directory=vdbs['directory'], files=ch_files,use_sequence_detection=True , align='WORLD', location=(0, 0, 0))
            vol = bpy.context.view_layer.objects.active
            vol.scale = scale
            vol.name = vol.name[:-2]
            vol.location = tuple(np.array(pos) * bbox_px *scale)
            vol.data.frame_start = 0
            volumes.append(vol)
    print('imported volumes')
    collection_activate(*base_coll)
    volumes = [vol for ix, vol in enumerate(vol_collection.all_objects) if ix in ch_names]
    materials = [volume_material(volumes[ix], otsus,  channel, len(otsus)) for ix, channel in enumerate(ch_names)]
    vol_obj = init_holder('volume',volumes, materials)
    for mat in vol_obj.data.materials:
        mat.node_tree.nodes["Emission"].inputs[1].show_expanded = True
    print('made volume holder')
    return vol_obj, vol_collection
