from .arrayloading import ArrayLoader
from ..handle_blender_structs.progress_handling import log
import numpy as np
from zarr.core import Array as ZarrArray
from zarr.storage import FSStore, LRUStoreCache
from collections import OrderedDict
import json
from aiohttp import ClientConnectorError
import os
import bpy
from pathlib import Path
from urllib.parse import urljoin

OME_ZARR_V_0_4_KWARGS = dict(dimension_separator="/", normalize_keys=False)
OME_ZARR_V_0_1_KWARGS = dict(dimension_separator=".")

class ZarrLevelsGroup(bpy.types.PropertyGroup):
    level_descriptor: bpy.props.StringProperty(name='zarrlevel')
    xy_size: bpy.props.FloatProperty(name='zarr_xy_size')
    z_size: bpy.props.FloatProperty(name='zarr_z_size')
    axes_order: bpy.props.StringProperty(name='zarr_axes_order')
    path: bpy.props.StringProperty(name='zarr_path')
    store: bpy.props.StringProperty(name='zarr_store')
    arraychannels : bpy.props.IntProperty() # without masks

    # |-separated lists
    ch_names : bpy.props.StringProperty()
    shape : bpy.props.StringProperty() # without masks
    # The scene collectionproperty is created in __init__ of the package due to registration issues:
    # bpy.types.Scene.MiN_zarrLevels = bpy.props.CollectionProperty(type=ZarrLevelsGroup)

class ZarrLoader(ArrayLoader):
    suffixes = ['.zarr']

    def checkPath(self):
        if self.suffixes[0] not in str(bpy.context.scene.MiN_input_file):
            bpy.context.scene.property_unset("MiN_selected_zarr_level")
        return self.suffixes[0] in str(bpy.context.scene.MiN_input_file)

    def load_array(self, input_file):
        uncached_store = FSStore(input_file, mode="r", **OME_ZARR_V_0_4_KWARGS)
        store = LRUStoreCache(uncached_store, max_size=5*(10**9))
        zarray = ZarrArray(store=store)
        return zarray
    
    def shape(self):
        # no solution for mask channels in channel-less images for now.
        for level in bpy.context.scene.MiN_zarrLevels:
            if level.level_descriptor == bpy.context.scene.MiN_selected_zarr_level:
                shape = [int(dim) for dim in level.shape.split("|")]
                if bpy.context.scene.MiN_axes_order == level.axes_order and 'c' in level.axes_order:
                    shape[level.axes_order.find('c')] += len(get_label_channels(level))
                return shape
                    

    def unpack_array(self, input_file, axes_order, ch_dicts):
        for level in bpy.context.scene.MiN_zarrLevels:
            if level.level_descriptor == bpy.context.scene.MiN_selected_zarr_level:
                super().unpack_array(append_uri(level.store, level.path), axes_order, ch_dicts)
                if bpy.context.scene.MiN_axes_order == level.axes_order:
                    for labellevel in get_label_channels(level)[0]:
                        super().unpack_array(append_uri(labellevel.store, labellevel.path), axes_order, ch_dicts)


    def changePath(self, context):
        bpy.context.scene.MiN_zarrLevels.clear()
        bpy.context.scene.MiN_zarrLabelLevels.clear()

        uri = context.scene.MiN_input_file
        if uri.startswith("file:"):
            # Primarily this is to deal with spaces in Windows paths (encoded as %20).
            uri = os.fsdecode(unquote_to_bytes(uri))
        
        try:
            label_uri = append_uri(uri, 'labels')
            uncached_store = FSStore(label_uri, mode="r", **OME_ZARR_V_0_4_KWARGS)
            label_names = json.loads(uncached_store[".zattrs"])['labels']
            for label_ch in label_names:
                parse_zattrs(append_uri(label_uri, label_ch), bpy.context.scene.MiN_zarrLabelLevels)
        except KeyError as e:
            print(e)
            print('no labels found')

        try:
            parse_zattrs(uri, bpy.context.scene.MiN_zarrLevels)
        except KeyError as e:
            if str(e) == "'multiscales'" and str(Path(uri).stem) != '0':
                context.scene.MiN_input_file = append_uri(uri, '0')
                self.changePath(context)
            else:
                bpy.context.scene.MiN_selected_zarr_level = f"Could not parse .zattrs, see print log for detail"
                print(e)
        return

def append_uri(uri, append):
    if Path(uri).exists():
        return Path(uri) / append
    if uri[-1] != '/':
        uri += "/"
    return urljoin(uri, append)

def parse_zattrs(uri, level_list):
    uri = str(uri)
    uncached_store = FSStore(uri, mode="r", **OME_ZARR_V_0_4_KWARGS)
    try:
        ome_spec = json.loads(uncached_store[".zattrs"])
    except Exception as e:
        # Connection problems on FSSpec side raise a ClientConnectorError wrapped in a KeyError
        if isinstance(e.__context__, ClientConnectorError):
            bpy.context.scene.MiN_selected_zarr_level = f"Could not connect to {e.__context__.host}:{e.__context__.port}"
            return
        elif isinstance(e, KeyError):
            bpy.context.scene.MiN_selected_zarr_level = f"Could not find .zattrs at this address"
            raise e
        else: 
            raise e
    if ome_spec.get("multiscales", [{}])[0].get("version") == "0.1":
        uncached_store = FSStore(uri, mode="r", **OME_ZARR_V_0_1_KWARGS)
    store = LRUStoreCache(uncached_store, max_size=10**9)

    ch_names = None
    if "omero" in ome_spec:
        try:
            ch_names = [omerosettings['label'] for omerosettings in ome_spec['omero']['channels']]
            ch_names = "|".join(ch_names)
        except KeyError as e:
            print(f'could not read channel names {e}')
    for multiscale_spec in ome_spec["multiscales"]:
        axes_order =  _get_axes_order_from_spec(multiscale_spec)
        datasets = multiscale_spec["datasets"]
        gui_scale_metadata = OrderedDict()  # Becomes slot metadata -> must be serializable (no ZarrArray allowed)
        
        for scale in datasets:  # OME-Zarr spec requires datasets ordered from high to low resolution
            level = level_list.add()
            level.store = uri
            level.path =  scale['path']
            level.axes_order = axes_order
            

            if "coordinateTransformations" in scale:
                scaletransform = [transform for transform in scale['coordinateTransformations'] if transform['type'] == 'scale'][0]
                level.xy_size = scaletransform['scale'][axes_order.find('x')]
                if 'z' in axes_order:
                    level.z_size = scaletransform['scale'][axes_order.find('z')]

            # Loading a ZarrArray at this path is necessary to obtain the scale dimensions for the GUI.
            # As a bonus, this also validates all scale["path"] strings passed outside this class.
            zarray = ZarrArray(store=store, path=scale["path"])
            
            level.shape = "|".join([str(dim) for dim in zarray.shape])
            if np.issubdtype(zarray.dtype,np.floating):
                log("Floating point arrays cannot be loaded lazily, will use a lot of RAM")

            totalshape_no_ch = list(zarray.shape)
            level.ch_names = ""
            channels = 1
            if 'c' in axes_order:
                channels = zarray.shape[axes_order.find('c')]
                level.ch_names = "|".join([""] * channels)
                del totalshape_no_ch[axes_order.find('c')]
            if ch_names is not None:
                level.ch_names = ch_names
            level.arraychannels = channels


            label_levels, label_names = [], []
            if level_list == bpy.context.scene.MiN_zarrLevels:
                label_levels, label_names = get_label_channels(level)
                channels += len(label_names)
                level.ch_names = "|".join([level.ch_names, *label_names])
                
            estimated_max_size = channels
            for dim in totalshape_no_ch:
                estimated_max_size *= dim
            estimated_max_size = human_size(estimated_max_size *4) # vdb's are 32 bit floats == 4 byte per voxel

            level.level_descriptor = f"{scale['path']}: {zarray.shape}, up to {estimated_max_size}"
            if len(label_names) > 1:
                level.level_descriptor = f"{scale['path']}: {zarray.shape} + {len(label_names)} masks, up to {estimated_max_size}"
            bpy.context.scene.MiN_selected_zarr_level = level.level_descriptor
    return

def get_label_channels(level):
    names = []
    label_levels = []
    ch_axis = None
    if 'c' in level.axes_order:
        ch_axis = level.axes_order.find('c')
    
    for label_level in bpy.context.scene.MiN_zarrLabelLevels:
        name = Path(label_level.store).stem
        if name in names:
            continue
        equalshape = [dim1 == dim2 for dim1, dim2 in zip(label_level.shape.split("|"), level.shape.split("|"))]
        if 'c' in level.axes_order:
            del equalshape[level.axes_order.find('c')]
        if all(equalshape):
            names.append(name)
            label_levels.append(label_level)
    return label_levels, names


def change_zarr_level(self, context):
    for level in bpy.context.scene.MiN_zarrLevels:
        
        if level.level_descriptor == bpy.context.scene.MiN_selected_zarr_level:
            context.scene.property_unset('MiN_xy_size')
            context.scene.property_unset('MiN_z_size')
            if 'xy_size' in level:
                context.scene.MiN_xy_size = level['xy_size']
            if 'z_size' in level:
                context.scene.MiN_z_size = level['z_size']
            
            channels = level.ch_names.split("|")
            if context.scene.MiN_channel_nr != len(channels) or context.scene.MiN_axes_order != level['axes_order']: # this updates n channels and resets names
                context.scene.MiN_axes_order = level['axes_order']
                context.scene.MiN_channel_nr = len(channels)
                
                for ix, ch in enumerate(context.scene.MiN_channelList):
                    if channels[ix] != "":
                        ch['name'] = channels[ix]
                    if ix >= level.arraychannels:
                        ch['volume'] = False
                        ch['surface'] = True
                        ch['threshold'] = 0
            return


def _get_axes_order_from_spec(validated_ome_spec):
    if "axes" in validated_ome_spec:
        ome_axes = validated_ome_spec["axes"]
        if "name" in ome_axes[0]:
            # v0.4: spec["axes"] requires name, recommends type and unit; like:
            # [
            #   {'name': 'c', 'type': 'channel'},
            #   {'name': 'y', 'type': 'space', 'unit': 'nanometer'},
            #   {'name': 'x', 'type': 'space', 'unit': 'nanometer'}
            # ]
            axes_order = "".join([d["name"] for d in ome_axes])
        else:
            # v0.3: ['t', 'c', 'y', 'x']
            axes_order = "".join(ome_axes)

    else:
        # v0.1 and v0.2 did not allow variable axes
        axes_order = "tczyx"
    return axes_order

# from https://stackoverflow.com/questions/1094841/get-a-human-readable-version-of-a-file-size
def human_size(bytes, units=[' bytes','KB','MB','GB','TB', 'PB', 'EB']):
    """ Returns a human readable string representation of bytes """
    return str(bytes) + units[0] if bytes < 1024 else human_size(bytes>>10, units[1:])

CLASSES = [ZarrLevelsGroup]

