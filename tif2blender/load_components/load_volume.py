import bpy
from mathutils import Color
from pathlib import Path
import numpy as np

from .load_generic import init_holder
from ..handle_blender_structs import *
from .. import t2b_nodes


def arrays_to_vdb_files(volume_arrays, axes_order, remake, cache_dir):
    # 2048 is maximum grid size for Eevee rendering, so grids are split for multiple
    # Loops over all axes and splits based on length
    # reassembles in negative coordinates, parents all to a parent at (half_x, half_y, bottom) that is then translated to (0,0,0)

    for ch in volume_arrays:
        volume_arrays[ch]['vdbs'] = []
        imgdata = volume_arrays[ch]['data']
        n_splits = [(imgdata.shape[dim] // 50)+ 1 for dim in [axes_order.find('x'),axes_order.find('y'),axes_order.find('z')]]
        a_chunks = np.array_split(imgdata, n_splits[0], axis=axes_order.find('x'))
        for a_ix, a_chunk in enumerate(a_chunks):
            b_chunks = np.array_split(a_chunk, n_splits[1], axis=axes_order.find('y'))
            for b_ix, b_chunk in enumerate(b_chunks):
                c_chunks = np.array_split(b_chunk, n_splits[2], axis=axes_order.find('z'))
                for c_ix, c_chunk in enumerate(reversed(c_chunks)):
                    directory, time_vdbs = make_vdb(c_chunk, (a_ix, b_ix, c_ix), axes_order, remake, cache_dir, ch)
                    volume_arrays[ch]['vdbs'].append({"directory" : directory, "files": time_vdbs, 'pos':(a_ix,b_ix,c_ix)})
        del volume_arrays[ch]['data']
    bbox_px = np.array([imgdata.shape[axes_order.find('x')], imgdata.shape[axes_order.find('y')], imgdata.shape[axes_order.find('z')]])//np.array(n_splits)
    
    return volume_arrays, bbox_px

def make_vdb(imgdata, chunk_ix, axes_order, remake, cache_dir, ch):
    import pyopenvdb as vdb
    x_ix, y_ix, z_ix = chunk_ix
    timefiles = []

    if axes_order != 'txyz':
        print(imgdata.shape, axes_order)
        imgdata = np.moveaxis(imgdata, [axes_order.find('t'),axes_order.find('x'),axes_order.find('y'),axes_order.find('z')],[0,1,2,3]).copy()

    identifier = "x"+str(x_ix)+"y"+str(y_ix)+"z"+str(z_ix)
    (Path(cache_dir)/f"{identifier}").mkdir(exist_ok=True,parents=True)
    for t, frame in enumerate(imgdata):
        fname = (Path(cache_dir)/f"{identifier}"/f"Channel {ch}_{t}.vdb")
        timefiles.append({"name":str(fname.name)})
        if not fname.exists() or remake:
            grid = vdb.FloatGrid()
            grid.name = f"data_channel_{ch}"
            grid.copyFromArray(frame)
            vdb.write(str(fname), grids=[grid])

    directory = str(Path(cache_dir)/f"{identifier}")
    return directory, timefiles



def volume_materials(volume_inputs, emission_setting):
    mats = []
    # do not check whether it exists, so a new load will force making a new mat
    for ix, ch in enumerate(volume_inputs):
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

        ramp_node = nodes.new(type="ShaderNodeValToRGB")
        ramp_node.location = (-300, 0)
        ramp_node.color_ramp.elements[0].position = volume_inputs[ch]['otsu']
        color = get_cmap('hue-wheel', maxval=len(volume_inputs))[ix]
        ramp_node.color_ramp.elements[1].color = (color[0],color[1],color[2],color[3])  
        links.new(node_attr.outputs.get("Fac"), ramp_node.inputs.get("Fac"))  

        scale = nodes.new(type='ShaderNodeVectorMath')
        scale.location = (0,-150)
        scale.operation = "SCALE"
        links.new(ramp_node.outputs[0], scale.inputs.get("Vector"))
        scale.inputs.get('Scale').default_value = 1
        
        emit = nodes.new(type='ShaderNodeEmission')
        emit.location = (250,0)
        links.new(ramp_node.outputs[0], emit.inputs.get('Color'))
        
        adsorb = nodes.new(type='ShaderNodeVolumeAbsorption')
        adsorb.location = (250,-200)
        links.new(ramp_node.outputs[0], adsorb.inputs.get('Color'))
        links.new(scale.outputs[0], adsorb.inputs.get('Density'))
        scatter = nodes.new(type='ShaderNodeVolumeScatter')
        scatter.location = (250,-300)
        links.new(ramp_node.outputs[0], scatter.inputs.get('Color'))
        links.new(scale.outputs[0], scatter.inputs.get('Density'))

        add = nodes.new(type='ShaderNodeAddShader')
        add.location = (450, -300)
        links.new(adsorb.outputs[0], add.inputs[0])
        links.new(scatter.outputs[0], add.inputs[1])
        
        if nodes.get("Material Output") is None:
            outnode = nodes.new(type='ShaderNodeOutputMaterial')
            outnode.name = 'Material Output'
        nodes.get("Material Output").location = (700,00)
        if emission_setting:
            links.new(emit.outputs[0], nodes.get("Material Output").inputs.get('Volume'))
        else:
            links.new(add.outputs[0], nodes.get("Material Output").inputs.get('Volume'))
        
        mats.append(mat)
    return mats


def load_volume(volume_inputs, bbox_px, scale, cache_coll, base_coll, emission_setting):
    # consider checking whether all channels are present in vdb for remaking?
    collection_activate(*cache_coll)
    vol_collection, vol_lcoll = make_subcollection('volumes')
    volumes = []
    print(volume_inputs)
    # necessary to support multi-file import
    bpy.types.Scene.files: CollectionProperty(
        type=bpy.types.OperatorFileListElement,
        options={'HIDDEN', 'SKIP_SAVE'},
    )
    
    for ch in volume_inputs:
        ch_collection, ch_lcoll = make_subcollection(f'channel {ch}')
        volume_inputs[ch]['collection'] = ch_collection
        for chunk in volume_inputs[ch]['vdbs']:
            bpy.ops.object.volume_import(filepath=chunk['files'][0]['name'],directory=chunk['directory'], files=chunk['files'],use_sequence_detection=True , align='WORLD', location=(0, 0, 0))
            vol = bpy.context.view_layer.objects.active
            vol.scale = scale
            vol.name = vol.name[:-2]
            vol.location = tuple(np.array(chunk['pos']) * bbox_px *scale)
            vol.data.frame_start = 0
        collection_activate(vol_collection, vol_lcoll)

    collection_activate(*base_coll)
    
    materials = volume_materials(volume_inputs, emission_setting) 
    volume_colls = [volume_inputs[ch]['collection'] for ch in volume_inputs]
    vol_obj = init_holder('volume',volume_colls, materials)
    for mat in vol_obj.data.materials:
        # make sure color ramp is immediately visibile under Volume shader
        # mat.node_tree.nodes["Slice Cube"].inputs[0].show_expanded = True
        mat.node_tree.nodes["Emission"].inputs[0].show_expanded = True

    return vol_obj, volume_inputs
