from .arrayloading import ArrayLoader
from zarr.core import Array as ZarrArray
from zarr.storage import FSStore, LRUStoreCache
from zarr.convenience import load
from collections import OrderedDict
import json
from aiohttp import ClientConnectorError
import os
import bpy
from pathlib import Path

OME_ZARR_V_0_4_KWARGS = dict(dimension_separator="/", normalize_keys=False)
OME_ZARR_V_0_1_KWARGS = dict(dimension_separator=".")

class ZarrLevelsGroup(bpy.types.PropertyGroup):
    level_descriptor: bpy.props.StringProperty(name='zarrlevel')
    xy_size: bpy.props.FloatProperty(name='zarr_xy_size')
    z_size: bpy.props.FloatProperty(name='zarr_z_size')
    axes_order: bpy.props.StringProperty(name='zarr_axes_order')
    path: bpy.props.StringProperty(name='zarr_path')
    store: bpy.props.StringProperty(name='zarr_store')
    channels : bpy.props.IntProperty()
    ch_names : bpy.props.StringProperty()
    # The scene collectionproperty is created in __init__ of the package due to registration issues:
    # bpy.types.Scene.MiN_zarrLevels = bpy.props.CollectionProperty(type=ZarrLevelsGroup)

class ZarrLoader(ArrayLoader):
    suffix = '.zarr'

    def checkPath(self):
        if self.suffix not in str(bpy.context.scene.MiN_input_file):
            bpy.context.scene.property_unset("MiN_selected_zarr_level")
        return self.suffix in str(bpy.context.scene.MiN_input_file)

    def load_array(self, input_file):
        
        for level in bpy.context.scene.MiN_zarrLevels:
            if level.level_descriptor == bpy.context.scene.MiN_selected_zarr_level:
                uncached_store = FSStore(level.store, mode="r", **OME_ZARR_V_0_4_KWARGS)
                store = LRUStoreCache(uncached_store, max_size=5*(10**9))
                zarray = ZarrArray(store=store, path=level.path)
                return zarray

    def changePath(self, context):
        bpy.context.scene.MiN_zarrLevels.clear()
        # infers metadata, resets to default if not found
        # the raise gets handled upstream, so only prints to cli, somehow.
        uri = context.scene.MiN_input_file
        if uri.startswith("file:"):
            # Zarr's FSStore implementation doesn't unescape file URLs before piping them to
            # the file system. We do it here the same way as in pathHelpers.uri_to_Path.
            # Primarily this is to deal with spaces in Windows paths (encoded as %20).
            uri = os.fsdecode(unquote_to_bytes(uri))
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
                return
            else: 
                raise e
        if ome_spec.get("multiscales", [{}])[0].get("version") == "0.1":
            uncached_store = FSStore(self.uri, mode="r", **OME_ZARR_V_0_1_KWARGS)
        store = LRUStoreCache(uncached_store, max_size=10**9)
        self.levels = {}

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
            dtype = None
            gui_scale_metadata = OrderedDict()  # Becomes slot metadata -> must be serializable (no ZarrArray allowed)
            
            for scale in datasets:  # OME-Zarr spec requires datasets ordered from high to low resolution
                level = bpy.context.scene.MiN_zarrLevels.add()
                # print(uri, context.scene.MiN_input_file, scale['name'])
                level.store = context.scene.MiN_input_file
                level.path =  scale['path']
                level.axes_order = axes_order
                if ch_names is not None:
                    level.ch_names = ch_names

                if "coordinateTransformations" in scale:
                    scaletransform = [transform for transform in scale['coordinateTransformations'] if transform['type'] == 'scale'][0]
                    level.xy_size = scaletransform['scale'][axes_order.find('x')]
                    if 'z' in axes_order:
                        level.z_size = scaletransform['scale'][axes_order.find('z')]

                
                # Loading a ZarrArray at this path is necessary to obtain the scale dimensions for the GUI.
                # As a bonus, this also validates all scale["path"] strings passed outside this class.
                zarray = ZarrArray(store=store, path=scale["path"])
                dtype = zarray.dtype.type
                estimated_max_size = zarray.shape[0]
                if 'c' in axes_order:
                    level.channels = zarray.shape[axes_order.find('c')]
                else:
                    level.channels = 1
                
                for dim in zarray.shape[1:]:
                    estimated_max_size *= dim
                estimated_max_size = human_size(estimated_max_size *4) # vdb's are 32 bit floats == 4 byte per voxel

                level.level_descriptor = f"{scale['path']}: {zarray.shape}, up to {estimated_max_size}"
                if len(ome_spec["multiscales"]) > 1:
                    level.level_descriptor = f"{multiscale_spec['name']}/{level.level_descriptor}"
                bpy.context.scene.MiN_selected_zarr_level = level.level_descriptor
        return


def change_zarr_level(self, context):
    for level in bpy.context.scene.MiN_zarrLevels:
        
        if level.level_descriptor == bpy.context.scene.MiN_selected_zarr_level:
            context.scene.property_unset('MiN_xy_size')
            context.scene.property_unset('MiN_z_size')
            if 'xy_size' in level:
                context.scene.MiN_xy_size = level['xy_size']
            if 'z_size' in level:
                context.scene.MiN_z_size = level['z_size']
            context.scene.MiN_axes_order = level['axes_order']

            if context.scene.MiN_channel_nr != level['channels']: # this updates n channels and resets names
                context.scene.MiN_channel_nr = level['channels']
                if 'ch_names' in level:
                    for ch, ch_name in zip(context.scene.MiN_channelList, level['ch_names'].split("|")):
                        ch['name'] = ch_name

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

