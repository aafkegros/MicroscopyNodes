import bpy
from mathutils import Color
from pathlib import Path
import numpy as np
import math
import itertools
import skimage
import scipy

from .load_generic import init_holder
from ..handle_blender_structs import *
from .. import min_nodes


NR_HIST_BINS = 2**16

def split_axis_to_chunks(length, split_to):
    n_splits = int((length // split_to)+ 1)
    splits = [length/n_splits * split for split in range(n_splits + 1)]
    splits[-1] = math.ceil(splits[-1])
    splits = [math.floor(split) for split in splits]
    slices = [slice(start, end) for start, end in zip(splits[:-1], splits[1:])]
    return list(zip(slices, list(range(n_splits))))

def arrays_to_vdb_files(volume_arrays, axes_order, remake, cache_dir):
    # 2048 is maximum grid size for Eevee rendering, so grids are split for multiple
    # Loops over all axes and splits based on length
    # reassembles in negative coordinates, parents all to a parent at (half_x, half_y, bottom) that is then translated to (0,0,0)
    for ch in volume_arrays:
        volume_arrays[ch]['local_files'] = []
        imgdata = volume_arrays[ch]['data']
        
        slices = []
        dims = []

        for it, dim in enumerate(axes_order): 
            # xyz are chunked to max 2048, otherwise Eevee cannot handle it
            if dim in 'xyz':
                slices.append(split_axis_to_chunks(imgdata.shape[it], 2049))
            else:
                slices.append(split_axis_to_chunks(imgdata.shape[it], np.inf))
        
        for block in itertools.product(*slices):
            
            # block_ix may contain duplicates if one of the axes does not exist, but this is not an issue
            block_ix = list(np.array([sl[1] for sl in block])[[axes_order.find('x'),axes_order.find('y'),axes_order.find('z')]])
            chunk = imgdata
            for dim, sl in enumerate(block): # dask-equivalent of imgdata[*listofslices] 
                chunk = np.take(chunk, indices = np.arange(sl[0].start, sl[0].stop), axis=dim)
            directory, time_vdbs, time_hists = make_vdb(chunk, block_ix, axes_order, remake, cache_dir, ch)
            volume_arrays[ch]['local_files'].append({"directory" : directory, "vdbfiles": time_vdbs, 'histfiles' : time_hists, 'pos':(block[0][1], block[1][1], block[2][1])})
        del volume_arrays[ch]['data']
    bbox_px = np.array([slices[axes_order.find(dim)][0][0].stop if dim in axes_order else 0 for dim in 'xyz'])
    # bbox_px = np.array([imgdata.shape[axes_order.find('x')], imgdata.shape[axes_order.find('y')], imgdata.shape[axes_order.find('z')]])//np.array(n_splits)
    
    return volume_arrays, bbox_px

def make_vdb(imgdata, chunk_ix, axes_order, remake, cache_dir, ch):
    # non-lazy functions are allowed on only single time-frames
    import pyopenvdb as vdb
    x_ix, y_ix, z_ix = chunk_ix
    # these are split for Blender
    time_vdbs = [] 
    time_hists = []
    if 't' not in axes_order: 
        # this is not lazy, but if there is no time axis, it is already chunked to small.
        imgdata = np.expand_dims(imgdata,axis=0)
        axes_order = 't' + axes_order
    
    identifier3d = f"x{x_ix}y{y_ix}z{z_ix}"
    dirpath = Path(cache_dir)/f"{identifier3d}"
    dirpath.mkdir(exist_ok=True,parents=True)
    for t in range(imgdata.shape[axes_order.find('t')]):
        identifier5d = f"{identifier3d}c{ch}t{t}"
        frame = np.take(imgdata, indices=t, axis=axes_order.find('t'))
        frame_axes_order = axes_order.replace('t',"")

        frame = np.moveaxis(frame, [frame_axes_order.find('x'),frame_axes_order.find('y'),frame_axes_order.find('z')],[0,1,2]).copy()
        
        vdbfname = dirpath / f"{identifier5d}.vdb"
        histfname = dirpath / f"{identifier5d}_hist.npy"
        time_vdbs.append({"name":str(vdbfname.name)})
        time_hists.append({"name":str(histfname.name)})
        if not vdbfname.exists() or not histfname.exists() or remake :
            print('remaking')
            if vdbfname.exists():
                vdbfname.unlink()
            if histfname.exists():
                histfname.unlink()
            # frame.visualize(filename=f'/Users/oanegros/Documents/screenshots/stranspose-hlg{x_ix}_{y_ix}_{z_ix}.svg', engine='cytoscape')

            frame = frame.astype(np.float32) / np.iinfo(imgdata.dtype).max # scale between 0 and 1
            arr = frame.compute()
            # hists could be done better with bincount, but this doesnt work with floats and seems harder to maintain
            histogram = np.histogram(arr, bins=NR_HIST_BINS, range=(0.,1.)) [0]
            histogram[0] = 0
            np.save(histfname, histogram, allow_pickle=False)
            # np.savetxt(histfname.with_suffix('csv'), histogram[0])

            grid = vdb.FloatGrid()
            grid.name = f"data_channel_{ch}"
            
            grid.copyFromArray(arr.astype(np.float32))
            vdb.write(str(vdbfname), grids=[grid])

    return str(dirpath), time_vdbs, time_hists

def get_leading_trailing_zero_float(arr):
    min_val = max(np.argmax(arr > 0)-1, 0) / len(arr)
    max_val = min(len(arr) - (np.argmax(arr[::-1] > 0)-1), len(arr)) / len(arr)
    return min_val, max_val

def shader_histogram(nodes, links, in_node, loc_x, hist, threshold):
    min_val = threshold
    max_val = 1

    ramp_node = nodes.new(type="ShaderNodeValToRGB")
    ramp_node.location = (loc_x, 0)
    ramp_node.width = 1000
    ramp_node.color_ramp.elements[0].position = min_val
    ramp_node.color_ramp.elements[1].position = max_val
    links.new(in_node, ramp_node.inputs.get("Fac"))  

    histnode =nodes.new(type="ShaderNodeFloatCurve")
    histnode.location = (loc_x, 300)
    histmap = histnode.mapping
    histnode.width = 1000
    histnode.label = 'Histogram (non-interactive)' 
    histnode.inputs.get('Factor').hide = True
    histnode.inputs.get('Value').hide = True
    histnode.outputs.get('Value').hide = True

    histnorm = hist / np.max(hist)
    if len(histnorm) > 150:
        histnorm = scipy.stats.binned_statistic(np.arange(len(histnorm)), histnorm, bins=150,statistic='sum')[0]
        histnorm /= np.max(histnorm) 
    for ix, val in enumerate(histnorm):
        if ix == 0:
            histmap.curves[0].points[-1].location = ix/len(histnorm), val
            histmap.curves[0].points.new((ix + 0.9)/len(histnorm), val)
        if ix==len(histnorm)-1:
            histmap.curves[0].points[-1].location = ix/len(histnorm), val
        else:
            histmap.curves[0].points.new(ix/len(histnorm), val)
            histmap.curves[0].points.new((ix + 0.9)/len(histnorm), val)
        histmap.curves[0].points[ix].handle_type = 'VECTOR'
    return ramp_node, histnode
        


def volume_materials(volume_inputs, emission_setting):
    mats = []
    # do not check whether it exists, so a new load will force making a new mat
    for vol_ix, ch in enumerate(volume_inputs):
        mat = bpy.data.materials.new(f'channel {ch}')
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        if nodes.get("Principled BSDF") is not None:
            nodes.remove(nodes.get("Principled BSDF"))
        if nodes.get("Principled Volume") is not None:
            nodes.remove(nodes.get("Principled Volume"))

        node_attr = nodes.new(type='ShaderNodeAttribute')
        node_attr.location = (-1400, 0)
        node_attr.attribute_name = f'data_channel_{ch}'

        normnode = nodes.new(type="ShaderNodeMapRange")
        normnode.location = (-1200, 0)
        normnode.label = "Normalize data"
        normnode.inputs[1].default_value = volume_inputs[ch]['min_val']       
        normnode.inputs[2].default_value = volume_inputs[ch]['max_val']    
        links.new(node_attr.outputs.get("Fac"), normnode.inputs[0])  
        normnode.hide = True

        ramp_node, hist_node2 = shader_histogram(nodes, links, normnode.outputs.get('Result'), -1000, volume_inputs[ch]['histnorm'], volume_inputs[ch]['threshold'])
        color = get_cmap('hue-wheel', maxval=len(volume_inputs))[vol_ix]
        ramp_node.color_ramp.elements[1].color = (color[0],color[1],color[2],color[3])  

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
        histtotal = np.zeros(NR_HIST_BINS)
        for chunk in volume_inputs[ch]['local_files']:
            already_loaded = list(ch_collection.all_objects)

            bpy.ops.object.volume_import(filepath=chunk['vdbfiles'][0]['name'],directory=chunk['directory'], files=chunk['vdbfiles'], align='WORLD', location=(0, 0, 0))
            # vol = bpy.context.view_layer.objects.active
            for vol in ch_collection.all_objects:
                if vol not in already_loaded:   
                    pos = chunk['pos']
                    strpos = f"{pos[0]}{pos[1]}{pos[2]}"
                
                    vol.scale = scale
                    vol.data.frame_offset = -1
                    
                    vol.location = tuple(np.array(chunk['pos']) * bbox_px *scale)

                    vol.data.frame_start = 0
            for hist in chunk['histfiles']:
                histtotal += np.load(Path(chunk['directory'])/hist['name'], allow_pickle=False)
        
        volume_inputs[ch]['min_val'],volume_inputs[ch]['max_val'] = get_leading_trailing_zero_float(histtotal)
        volume_inputs[ch]['histnorm'] = histtotal[int(volume_inputs[ch]['min_val'] * NR_HIST_BINS): int(volume_inputs[ch]['max_val'] * NR_HIST_BINS)]
        volume_inputs[ch]['threshold'] = skimage.filters.threshold_isodata(hist=volume_inputs[ch]['histnorm'] )/len(volume_inputs[ch]['histnorm'] )
        collection_activate(vol_collection, vol_lcoll)

    collection_activate(*base_coll)
    
    materials = volume_materials(volume_inputs, emission_setting) 
    volume_colls = [volume_inputs[ch]['collection'] for ch in volume_inputs]
    vol_obj = init_holder('volume',volume_colls, materials)
    for mat in vol_obj.data.materials:
        # make sure color ramp is immediately visibile under Volume shader
        # mat.node_tree.nodes["Slice Cube"].inputs[0].show_expanded = True
        try:
            mat.node_tree.nodes["Emission"].inputs[0].show_expanded = True
        except:
            pass
    return vol_obj, volume_inputs
