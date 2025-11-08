import bpy
from mathutils import Color
from pathlib import Path
import numpy as np
import math
import itertools
import string

from .load_generic import *
from ..handle_blender_structs import *
from .. import min_nodes


NR_HIST_BINS = 2**16

from pathlib import Path
import string


def get_leading_trailing_zero_float(arr):
        min_val = max(np.argmax(arr > 0)-1, 0) / len(arr)
        max_val = min(len(arr) - (np.argmax(arr[::-1] > 0)-1), len(arr)) / len(arr)
        return min_val, max_val

class VolumeIO(DataIO):
    min_type = min_keys.VOLUME
    VDB_TEMPLATE = Path("{cache_dir}") / "{dataset_hash}" / "{scale}" / "x{x}y{y}z{z}_c{channel_ix}_t{t}.vdb"

    def generate_file_constructors(self, ch, cache_dir):
        """Purely generates file path metadata without writing."""
        file_constructors = []

        xyz_shape = [len_axis(dim, ch['axes_order'], ch['data'].shape) for dim in 'xyz']
        maxlen = np.inf
        if bpy.context.scene.MiN_chunk:
            maxlen = 2048
        slices_xyz = [self.split_axis_to_chunks(dimshape, ch['ix'], maxlen) for dimshape in xyz_shape]
        time_slices = [slice(t, t+1) for t in range(bpy.context.scene.MiN_load_start_frame, min(bpy.context.scene.MiN_load_end_frame + 1, len_axis('t', ch['axes_order'], ch['data'].shape)))]
        slices_xyzt = slices_xyz + [time_slices]

        for block in itertools.product(*slices_xyzt):
            file_constructors.append( {
                "cache_dir": cache_dir,
                "dataset_hash": ch['dataset_hash'],
                "scale": ch['dataset_scale'],
                'x': block[0].start, 'y': block[1].start, 'z': block[2].start,
                "x_end": block[0].stop, "y_end": block[1].stop, "z_end": block[2].stop,
                "t": block[3].start, "t_end": block[3].stop,
                "channel_ix": ch['ix'],
                "template_str" : str(self.VDB_TEMPLATE),
            })
        return file_constructors

    def export_ch(self, ch, file_constructors, remake):
        vdb_info = []
        for constructor in file_constructors:
            vdbfname = Path(str(self.VDB_TEMPLATE).format(**constructor))
            histfname = vdbfname.with_suffix('.npz')
            vdbfname.parent.mkdir(parents=True, exist_ok=True)
            
            if( not vdbfname.exists() or not histfname.exists()) or remake :
                vdbfname.unlink(missing_ok=True)
                histfname.unlink(missing_ok=True)
                log(f"loading chunk {Path(vdbfname).stem}")
                arr = ch['data'][tuple(
                    slice(constructor[dim], constructor[f"{dim}_end"]) for dim in ch['axes_order']
                )].compute()


                arr = to_xyz(arr, ch['axes_order']) # for 1D and 2D data, expand to 3D, squeeze the single time frame
                try:
                    max_val = min(np.iinfo(ch['data'].dtype).max, np.iinfo(np.int32).max)
                except ValueError:
                    max_val = ch['max_val'].compute()
                arr = arr.astype(np.float32) / max_val
                # hists could be done better with bincount, but this doesnqt work with floats and seems harder to maintain
                histogram = np.histogram(arr, bins=NR_HIST_BINS, range=(0.,1.)) [0]
                histogram[0] = 0
                np.savez(histfname, data=histogram, metadata={"data_max": max_val}, allow_pickle=False)
                log(f"write vdb {vdbfname.name}")
                self.make_vdb(vdbfname, arr)   
        
        return vdb_info

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


    def make_vdb(self, vdbfname, arr):
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


    def get_metadata(self, file_constructors):
        hist = np.zeros(NR_HIST_BINS)
        data_max = 1.0
        for constructor in file_constructors:
            histfname = Path(str(constructor['template_str']).format(**constructor)).with_suffix('.npz')
            try:
                hist += np.load(histfname, allow_pickle=False)['data']
                data_max = np.load(histfname, allow_pickle=True)['metadata'].item()['data_max']
            except Exception as e:
                print(e, " in reading histogram, skipping chunk")
                hist += np.zeros(NR_HIST_BINS)
        if not np.any(hist):
            return {"range": (0, 1), 'vdb_min': 0, 'vdb_max':1, "histogram": np.zeros(NR_HIST_BINS), "threshold": 0, "threshold_upper": 1.0}

        r0, r1 = get_leading_trailing_zero_float(hist)
        cropped = hist[int(r0 * NR_HIST_BINS): int(r1 * NR_HIST_BINS)]
        threshold = threshold_isodata(hist=cropped)

        cs = np.cumsum(cropped)
        threshold_upper = max(threshold+2,np.searchsorted(cs, np.percentile(cs, 70))) 

        if threshold < 30:
            threshold = 1
            threshold_upper = len(cropped)
        
        return {
            "range": (r0, r1), # legacy 
            "vdb_min" : r0,
            "vdb_max" : r1,
            "histogram": cropped,
            "threshold": threshold / len(cropped),
            "threshold_upper": threshold_upper / len(cropped),
            "data_max": data_max
        }


class VolumeObject(ChannelObject):
    min_type = min_keys.VOLUME
    import_node_name = "Import Microscopy Volume"    

    def update_import_node(self, import_node, file_constructors, ch):
        super().update_import_node(import_node, file_constructors, ch)
        ch_to_node = {"VDB Maximum":"vdb_max","VDB Minimum":"vdb_min", "Original Maximum":"data_max"}
        for key, val in ch_to_node.items():
            import_node.inputs.get(key).default_value = ch['metadata'][self.min_type][val]
        import_node.inputs.get('Grid Name').default_value = 'data' # TEMPORARY
        return
    
    def channel_nodes(self, x, y, ch, in_ch, out_ch):
        mat_in, mat_out = super().channel_nodes(x, y, ch, in_ch, out_ch)
        g2i = self.node_group.nodes.new('GeometryNodeGeometryToInstance')
        g2i.location = (x + 500, y)
        self.node_group.links.new(in_ch, g2i.inputs.get('Geometry'))
        self.node_group.links.new(g2i.outputs.get('Instances'), mat_in)
        return g2i.inputs.get('Geometry'), mat_out

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
            histnorm = binned_statistic_sum(np.arange(len(histnorm)), histnorm, bins=150)
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

        if nodes.get('[color_lut]') is not None:
            min_nodes.shader_nodes.set_color_ramp_from_ch(ch, nodes['[color_lut]'])

        if self.min_type in ch['metadata']:
            if ch['metadata'][self.min_type] is not None and nodes.get('[Histogram]') is not None:
                histnode= nodes["[Histogram]"]
                self.draw_histogram(nodes, histnode.location,histnode.width, ch['metadata'][self.min_type]['histogram'])
                nodes.remove(histnode)

        if nodes.get('[switch]') is not None:
            nodes['[switch]'].inputs[0].default_value = ['Emission', 'Scattering'][int(not ch['emission'])]

        for node in nodes:
            if (len(node.inputs) > 0 and not node.hide) and node.type != 'VALTORGB':
                node.inputs[0].show_expanded = True # traces through
                for key in ['Strength', 'Density', 'Emission']: # non-first key
                    if (inp := node.inputs.get(key)) is not None:
                        inp.show_expanded = True
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

        node_attr.attribute_name = 'data'

        node_attr.label = ch['name']
        node_attr.hide =True

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
        links.new(node_attr.outputs.get('Fac'), ramp_node.inputs.get("Fac"))  

        self.draw_histogram(nodes, (-1200, 300), 1000, ch['metadata'][self.min_type]['histogram'])

        alphanode =  nodes.new('ShaderNodeGroup')
        alphanode.node_tree = min_nodes.shader_nodes.volume_alpha_node()
        alphanode.name = '[volume_alpha]'
        alphanode.location = (-300, -120)
        alphanode.show_options = False
        alphanode.outputs.get("Alpha Baseline").default_value = 0
        alphanode.outputs.get("Alpha Multiplier").default_value = 1
        links.new(ramp_node.outputs.get('Alpha'), alphanode.inputs.get("Value"))
        alphanode.width = 300


        color_lut = nodes.new(type="ShaderNodeValToRGB")
        color_lut.location = (-300, 120)
        color_lut.width = 300
        color_lut.name = "[color_lut]"
        color_lut.outputs[1].hide = True
        links.new(ramp_node.outputs[1], color_lut.inputs[0])

        ac_linear = node_handling.nodegroup_from_blend("Normalize Luminance", nodes, "ShaderNodeGroup")
        ac_linear.location = (150, 0)
        links.new(color_lut.outputs[0],ac_linear.inputs[0])
        links.new(alphanode.outputs.get("Alpha Baseline"),ac_linear.inputs.get("Alpha Baseline"))
        links.new(alphanode.outputs.get("Alpha Multiplier"),ac_linear.inputs.get("Alpha Multiplier"))
        ac_linear.hide =True

        shader_nodes = {'ShaderNodeEmission': None, 'ShaderNodeVolumeAbsorption': None, 'ShaderNodeVolumeScatter':None}

        for i, node_type in enumerate(shader_nodes):
            node = nodes.new(type=node_type)
            node.location = (350, 100 - 150 * i)
            links.new(ac_linear.outputs[0], node.inputs.get("Color"))
            links.new(alphanode.outputs[0], node.inputs[1])
            shader_nodes[node_type] = node

        div = nodes.new(type='ShaderNodeMath')
        div.operation = 'DIVIDE'
        div.inputs[1].default_value = 10
        div.location = (150, 100)
        div.label = 'Divide by 10'
        links.new(alphanode.outputs[0], div.inputs[0])
        links.new(div.outputs[0], shader_nodes["ShaderNodeEmission"].inputs[1])
        div.hide=True

        add = nodes.new(type="ShaderNodeAddShader")
        add.location = (550, -150)
        links.new(shader_nodes["ShaderNodeVolumeAbsorption"].outputs[0], add.inputs[0])
        links.new(shader_nodes["ShaderNodeVolumeScatter"].outputs[0], add.inputs[1])

        menuswitch = nodes.new(type="GeometryNodeMenuSwitch")
        menuswitch.name = "[switch]"
        menuswitch.label = "Emission Switch"
        menuswitch.data_type = 'SHADER'
        menuswitch.location = (800, 0)
        menuswitch.enum_items.clear()
        menuswitch.enum_items.new("Emission")
        menuswitch.enum_items.new("Scattering")
        
        links.new(shader_nodes["ShaderNodeEmission"].outputs[0], menuswitch.inputs[1])
        links.new(add.outputs[0], menuswitch.inputs[2])
        

        if nodes.get("Material Output") is None:
            outnode = nodes.new(type='ShaderNodeOutputMaterial')
            outnode.name = 'Material Output'

        nodes.get("Material Output").location = (1200,00)
        links.new(menuswitch.outputs[0], nodes.get("Material Output").inputs[1])
        return mat

# Simplified rewrite of skimage.filters.threshold_isodata from
# https://github.com/scikit-image/scikit-image/blob/v0.25.2/skimage/filters/thresholding.py
# avoids packaging all of skimage for just this function
def threshold_isodata(image=None, nbins=256, return_all=False, hist=None):
    if hist is None:
        hist, edges = np.histogram(image.ravel(), bins=nbins)
        bin_centers = (edges[:-1] + edges[1:]) / 2
    else:
        if isinstance(hist, tuple):
            hist, bin_centers = hist
        else:
            bin_centers = np.arange(len(hist))
    if len(bin_centers) == 1:
        return bin_centers if return_all else bin_centers[0]

    counts = hist.astype(float)
    csuml = np.cumsum(counts)
    csumh = csuml[-1] - csuml
    intensity_sum = counts * bin_centers
    csum_intensity = np.cumsum(intensity_sum)
    lower = csum_intensity[:-1] / csuml[:-1]
    higher = (csum_intensity[-1] - csum_intensity[:-1]) / csumh[:-1]
    all_mean = (lower + higher) / 2.0
    bin_width = bin_centers[1] - bin_centers[0]
    distances = all_mean - bin_centers[:-1]
    thresholds = bin_centers[:-1][(distances >= 0) & (distances < bin_width)]
    return thresholds if return_all else thresholds[0]

# simplified version of https://github.com/scipy/scipy/blob/v1.16.2/scipy/stats/_binned_statistic.py
def binned_statistic_sum(x, values, bins):
    x = np.asarray(x)
    values = np.asarray(values)
    bins = np.linspace(x.min(), x.max(), bins + 1)  # bin edges
    bin_indices = np.searchsorted(bins, x, side='right') - 1
    bin_indices = np.clip(bin_indices, 0, bins.size - 2)
    
    sums = np.zeros(bins.size - 1, dtype=values.dtype)
    np.add.at(sums, bin_indices, values)  # sum values in each bin
    return sums
    
