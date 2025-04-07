import bpy
from mathutils import Color
from pathlib import Path
import numpy as np
import math
import itertools
import skimage
import scipy

from .load_generic import *
from ..handle_blender_structs import *
from .. import min_nodes

NR_HIST_BINS = 2**16


def get_leading_trailing_zero_float(arr):
        min_val = max(np.argmax(arr > 0)-1, 0) / len(arr)
        max_val = min(len(arr) - (np.argmax(arr[::-1] > 0)-1), len(arr)) / len(arr)
        return min_val, max_val

class VolumeIO(DataIO):
    min_type = min_keys.VOLUME

    def export_ch(self, ch, cache_dir, remake, axes_order):
        file_meta = []

        xyz_shape = [len_axis(dim, axes_order, ch['data'].shape) for dim in 'xyz']
        maxlen = np.inf
        if bpy.context.scene.MiN_chunk:
            maxlen = 2048
        slices = [self.split_axis_to_chunks(dimshape, ch['ix'], maxlen) for dimshape in xyz_shape]
        for block in itertools.product(*slices):
            chunk = ch['data']
            for dim, sl in zip('xyz', block): 
                chunk = take_index(chunk, indices = np.arange(sl.start, sl.stop), dim=dim, axes_order=axes_order)
            directory, time_vdbs, time_hists = self.make_vdbs(chunk, block, axes_order, remake, cache_dir, ch)
            file_meta.append({"directory" : directory, "vdbfiles": time_vdbs, 'histfiles' : time_hists, 'pos':(block[0].start, block[1].start, block[2].start)})
        return file_meta

    def split_axis_to_chunks(self, length, ch_ix, maxlen):
        # chunks to max 2048 length, with ch_ix dependent offsets
        offset = 0
        if length > maxlen:
            offset = (300 * ch_ix) % 2048
        n_splits = int((length // (maxlen+1))+ 1)
        splits = [length/n_splits * split for split in range(n_splits + 1)]
        splits[-1] = math.ceil(splits[-1]) 
        splits = [math.floor(split) + offset for split in splits]
        if offset > 0:
            splits.insert(0, 0)
        while splits[-2] > length:
            del splits[-1]
        splits[-1] = length 
        slices = [slice(start, end) for start, end in zip(splits[:-1], splits[1:])]
        return slices

    
    def make_vdbs(self, imgdata, block, axes_order, remake, cache_dir, ch):
        # non-lazy functions are allowed on only single time-frames
        x_ix, y_ix, z_ix = [sl.start for sl in block]

        # imgdata = imgdata.compute()
        time_vdbs = [] 
        time_hists = []

        identifier3d = f"x{x_ix}y{y_ix}z{z_ix}"
        dirpath = Path(cache_dir)/f"{identifier3d}"
        dirpath.mkdir(exist_ok=True,parents=True)
        for t in range(0, bpy.context.scene.MiN_load_end_frame+1):
            if t >= len_axis('t', axes_order, imgdata.shape):
                break

            identifier5d = f"{identifier3d}c{ch['ix']}t{t:04}"
            frame = take_index(imgdata, t, 't', axes_order)
            frame_axes_order = axes_order.replace('t',"")

            vdbfname = dirpath / f"{identifier5d}.vdb"
            histfname = dirpath / f"{identifier5d}_hist.npy"

            if t < bpy.context.scene.MiN_load_start_frame and not vdbfname.exists():
                # Makes dummy vdb files to keep sequence reading of Blender correct if the loaded frames are offset
                # existence of histogram file is then used to see if this is a dummy
                open(vdbfname, 'a').close()
                continue
            
            time_vdbs.append({"name":str(vdbfname.name)})
            time_hists.append({"name":str(histfname.name)})
            if( not vdbfname.exists() or not histfname.exists()) or remake :
                if vdbfname.exists():
                    vdbfname.unlink()
                if histfname.exists():
                    histfname.unlink()
                log(f"loading chunk {identifier5d}")
                arr = frame.compute()
                
                arr = expand_to_xyz(arr, frame_axes_order) 
                try:
                    arr = arr.astype(np.float32) / min(np.iinfo(imgdata.dtype).max, np.iinfo(np.int32).max) # scale between 0 and 1, capped to allow uint32 to at least not break
                except ValueError as e:
                    arr = arr.astype(np.float32) / ch['max_val'].compute()

                # hists could be done better with bincount, but this doesnt work with floats and seems harder to maintain
                histogram = np.histogram(arr, bins=NR_HIST_BINS, range=(0.,1.)) [0]
                histogram[0] = 0
                np.save(histfname, histogram, allow_pickle=False)
                log(f"write vdb {identifier5d}")
                self.make_vdb(vdbfname, arr, f"c{ch['ix']}")   

        return str(dirpath), time_vdbs, time_hists

    def make_vdb(self, vdbfname, arr, gridname):
        try:
            import openvdb as vdb
        except:
            bpy.utils.expose_bundled_modules()
            import openvdb as vdb
            pass
        grid = vdb.FloatGrid()
        grid.name = f"data"
        grid.copyFromArray(arr)
        # For future OME-Zarr transforms - something like this:
        # grid.transform = vdb.createLinearTransform(np.array([[ 2. ,  0. ,  0. , 8.5],[ 0. ,  2. ,  0. ,  8.5],[ 0. ,  0. ,  2. ,  10.5],[ 0. ,  0. ,  0. ,  1. ]]).T)
        vdb.write(str(vdbfname), grids=[grid])
        return

    def import_data(self, ch, scale):
        vol_collection, vol_lcoll = make_subcollection(f"{ch['name']} {'volume'}", duplicate=True)
        metadata = {}
        collection_activate(vol_collection, vol_lcoll)
        histtotal = np.zeros(NR_HIST_BINS)
        for chunk in ch['local_files'][self.min_type]:
            bpy.ops.object.volume_import(filepath=chunk['vdbfiles'][0]['name'],directory=chunk['directory'], files=chunk['vdbfiles'], align='WORLD', location=(0, 0, 0))
            vol = bpy.context.active_object
            pos = chunk['pos']
            strpos = f"{pos[0]}{pos[1]}{pos[2]}"
        
            vol.scale = scale
            vol.data.frame_offset = -1 + bpy.context.scene.MiN_load_start_frame
            vol.data.frame_start = bpy.context.scene.MiN_load_start_frame
            vol.data.frame_duration = bpy.context.scene.MiN_load_end_frame - bpy.context.scene.MiN_load_start_frame + 1
            vol.data.render.clipping =0
            # vol.data.display.density = 1e-5
            # vol.data.display.interpolation_method = 'CLOSEST'

            
            vol.location = tuple((np.array(chunk['pos']) * scale))  
        
            for hist in chunk['histfiles']:
                histtotal += np.load(Path(chunk['directory'])/hist['name'], allow_pickle=False)
        
        # defaults
        metadata['range'] = (0, 1)
        metadata['histogram'] = np.zeros(NR_HIST_BINS)
        metadata['datapointer'] = vol.data

        if np.sum(histtotal)> 0:
            metadata['range'] = get_leading_trailing_zero_float(histtotal)
            metadata['histogram'] = histtotal[int(metadata['range'][0] * NR_HIST_BINS): int(metadata['range'][1] * NR_HIST_BINS)]
            threshold = skimage.filters.threshold_isodata(hist=metadata['histogram'] )
            metadata['threshold'] = threshold/len(metadata['histogram'] )  
            cs = np.cumsum(metadata['histogram'])
            percentile = np.searchsorted(cs, np.percentile(cs, 90))
            if percentile > threshold:
                metadata['threshold_upper'] = percentile / len(metadata['histogram'] )  
        elif ch['threshold'] != -1: # THIS IS TO BE DEPRECATED - LABEL SUPPORT FOR ZARR
            metadata['threshold'] = ch['threshold']
        else:
            # this is for 0,1 range int32 data
            metadata['range'] = (0, 1e-9)
            metadata['threshold'] = 0.3
            metadata['threshold_upper'] = 1
        return vol_collection, metadata


class VolumeObject(ChannelObject):
    min_type = min_keys.VOLUME
    
    def draw_histogram(self, nodes, loc, width, hist):
        histnode =nodes.new(type="ShaderNodeFloatCurve")
        histnode.location = loc
        histmap = histnode.mapping
        histnode.width = width
        histnode.label = 'Histogram (non-interactive)' 
        histnode.name = '[Histogram]'
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
        return histnode

    def update_material(self, mat, ch):
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links

        node_names = [node.name for node in nodes]

        if self.min_type in ch['metadata']:
            if '[Histogram]' in node_names and ch['metadata'][self.min_type] is not None:
                histnode= nodes["[Histogram]"]
                self.draw_histogram(nodes, histnode.location,histnode.width, ch['metadata'][self.min_type]['histogram'])
                nodes.remove(histnode)

        try:
            ch_load = nodes[f"[channel_load_{ch['identifier']}]"]
            shader_in_color = nodes['[shader_in_color]']
            shader_in_alpha = nodes['[shader_in_alpha]']
            shader_out = nodes['[shader_out]']
            lut = nodes['[color_lut]']
        except KeyError as e:
            print(e, " skipping update of shader")
            return

        min_nodes.shader_nodes.set_color_ramp_from_ch(ch, lut)


        if '[shaderframe]' not in node_names:
            shaderframe = nodes.new('NodeFrame')
            shaderframe.name = '[shaderframe]'
            shaderframe.use_custom_color = True
            shaderframe.color = (0.2,0.2,0.2)
            shader_in_color.parent = shaderframe
            shader_in_alpha.parent = shaderframe
            shader_out.parent = shaderframe
        else:
            shaderframe = nodes['[shaderframe]']

        ch_load.label = ch['name']
        # removes of other type, if any of current type exist, don't update
        setting, remove = 'absorb', 'emit'
        if ch['emission']:
            setting, remove = 'emit', 'absorb'

        for node in nodes:
            if remove in node.name:
                nodes.remove(node)
            elif setting in node.name:
                return
        
        if ch['emission']:
            emit = nodes.new(type='ShaderNodeEmission')
            emit.name = '[emit]'
            emit.location = (250,0)
            links.new(shader_in_color.outputs[0], emit.inputs.get('Color'))
            links.new(shader_in_alpha.outputs[0], emit.inputs[1])
            links.new(emit.outputs[0], shader_out.inputs[0])
            emit.parent=shaderframe
        else:
            
            adsorb = nodes.new(type='ShaderNodeVolumeAbsorption')
            adsorb.name = 'absorb [absorb]'
            adsorb.location = (50,-100)
            links.new(shader_in_color.outputs[0], adsorb.inputs.get('Color'))
            links.new(shader_in_alpha.outputs[0], adsorb.inputs.get('Density'))
            scatter = nodes.new(type='ShaderNodeVolumeScatter')
            scatter.name = 'scatter absorb'
            scatter.location = (250,-200)
            links.new(shader_in_color.outputs[0], scatter.inputs.get('Color'))
            links.new(shader_in_alpha.outputs[0], scatter.inputs.get('Density'))
            scatter.parent=shaderframe

            add = nodes.new(type='ShaderNodeAddShader')
            add.name = 'add [absorb]'
            add.location = (450, -100)
            links.new(adsorb.outputs[0], add.inputs[0])
            links.new(scatter.outputs[0], add.inputs[1])
            links.new(add.outputs[0], shader_out.inputs[0])
            add.parent=shaderframe


        try:
            for node in nodes:
                if (len(node.inputs) > 0 and not node.hide) and node.type != 'VALTORGB':
                    node.inputs[0].show_expanded = True
                    if node.inputs.get('Strength') is not None:
                        node.inputs.get('Strength').show_expanded= True
                    if node.inputs.get('Density') is not None:
                        node.inputs.get('Density').show_expanded= True
            shader_in_alpha.inputs[0].show_expanded=True
            nodes['[volume_alpha]'].inputs[0].show_expanded = True
        except:
            print('could not set outliner options expanded in shader')
        return

    def add_material(self, ch):
        mat = super().add_material(ch)
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        if nodes.get("Principled BSDF") is not None:
            nodes.remove(nodes.get("Principled BSDF"))
        if nodes.get("Principled Volume") is not None:
            nodes.remove(nodes.get("Principled Volume"))

        node_attr = nodes.new(type='ShaderNodeAttribute')
        node_attr.location = (-1600, 0)
        node_attr.name = f"[channel_load_{ch['identifier']}]"

        try:
            ch['metadata'][self.min_type]['datapointer'].grids.load()
            node_attr.attribute_name = ch['metadata'][self.min_type]['datapointer'].grids[0].name
        except Exception:
            node_attr.attribute_name = f"data"

        node_attr.label = ch['name']
        node_attr.hide =True

        normnode = nodes.new(type="ShaderNodeMapRange")
        normnode.location = (-1400, 0)
        normnode.label = "Normalize data"
        normnode.inputs[1].default_value = ch['metadata'][self.min_type]['range'][0]       
        normnode.inputs[2].default_value = ch['metadata'][self.min_type]['range'][1]    
        links.new(node_attr.outputs.get("Fac"), normnode.inputs[0])  
        normnode.hide = True

        ramp_node = nodes.new(type="ShaderNodeValToRGB")
        ramp_node.location = (-1200, 0)
        ramp_node.width = 1000
        ramp_node.color_ramp.elements[0].position = ch['metadata'][self.min_type]['threshold']
        

        ramp_node.color_ramp.elements[0].color = (1,1,1,0)
        ramp_node.color_ramp.elements[1].color = (1,1,1,1)
        ramp_node.color_ramp.elements[1].position = 1
        ramp_node.name = '[alpha_ramp]'
        ramp_node.label = "Pixel Intensities"
        if 'threshold_upper' in ch['metadata'][self.min_type]:
            ramp_node.color_ramp.elements[1].position = ch['metadata'][self.min_type]['threshold_upper']
        ramp_node.outputs[0].hide = True
        links.new(normnode.outputs.get('Result'), ramp_node.inputs.get("Fac"))  

        self.draw_histogram(nodes, (-1200, 300), 1000, ch['metadata'][self.min_type]['histogram'])

        alphanode =  nodes.new('ShaderNodeGroup')
        alphanode.node_tree = min_nodes.shader_nodes.volume_alpha_node()
        alphanode.name = '[volume_alpha]'
        alphanode.location = (-300, -120)
        alphanode.show_options = False
        links.new(ramp_node.outputs.get('Alpha'), alphanode.inputs.get("Value"))
        alphanode.width = 300


        color_lut = nodes.new(type="ShaderNodeValToRGB")
        color_lut.location = (-300, 120)
        color_lut.width = 300
        color_lut.name = "[color_lut]"
        color_lut.outputs[1].hide = True
        links.new(ramp_node.outputs[1], color_lut.inputs[0])
        

        shader_in_color = nodes.new('NodeReroute')
        shader_in_color.name = f"[shader_in_color]"
        shader_in_color.location = (100, 0)
        links.new(color_lut.outputs[0], shader_in_color.inputs[0])

        shader_in_alpha = nodes.new('NodeReroute')
        shader_in_alpha.name = f"[shader_in_alpha]"
        shader_in_alpha.location = (100, -50)
        links.new(alphanode.outputs[0], shader_in_alpha.inputs[0])
        
        shader_out = nodes.new('NodeReroute')
        shader_out.location = (600, 0)
        shader_out.name = f"[shader_out]"

        if nodes.get("Material Output") is None:
            outnode = nodes.new(type='ShaderNodeOutputMaterial')
            outnode.name = 'Material Output'
        links.new(shader_out.outputs[0], nodes.get("Material Output").inputs.get('Volume'))
        nodes.get("Material Output").location = (700,00)

        return mat