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


class ZarrLoader(ArrayLoader):
    suffixes = ['.zarr']

    def check_path(self):
        super().check_path()
        return self.suffixes[0] in str(bpy.context.scene.MiN_input_file)

    def load_array(self, input_file, array_option):
        uncached_store = FSStore(input_file, mode="r", **OME_ZARR_V_0_4_KWARGS)
        store = LRUStoreCache(uncached_store, max_size=5*(10**9))
        zarray = ZarrArray(store=store)
        return zarray
    
    # def shape(self):
    #     # no solution for mask channels in channel-less images for now.
    #     for level in bpy.context.scene.MiN_zarrLevels:
    #         if level.level_descriptor == bpy.context.scene.MiN_selected_zarr_level:
    #             shape = [int(dim) for dim in level.shape.split("|")]
    #             if bpy.context.scene.MiN_axes_order == level.axes_order and 'c' in level.axes_order:
    #                 shape[level.axes_order.find('c')] += len(get_label_channels(level))
    #             return shape
                    

    def unpack_array(self, input_file, axes_order, ch_dicts):
        level = selected_array_scale()
        super().unpack_array(append_uri(level.store, level.path), axes_order, ch_dicts)

    def fill_scales(self):
        uri = context.scene.MiN_input_file
        if uri.startswith("file:"):
            # Primarily this is to deal with spaces in Windows paths (encoded as %20).
            uri = os.fsdecode(unquote_to_bytes(uri))

        try:
            self.parse_zattrs(uri, bpy.context.scene.MiN_zarrLevels)
        except KeyError as e:
            if str(e) == "'multiscales'" and str(Path(uri).stem) != '0':
                context.scene.MiN_input_file = append_uri(uri, '0')
                self.changePath(context)
            else:
                bpy.context.scene.MiN_selected_zarr_level = f"Could not parse .zattrs, see print log for detail"
                print(e)


    def parse_zattrs(self, uri, level_list):
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
            try:
                unit = [axis['unit'] for axis in multiscale_spec["axes"] if axis['type'] == 'space'][0]
                bpy.context.scene.MiN_unit = self.parse_unit(unit)
            except Exception as e:
                print(e)
                print('cannot read unit - may be Zarr <= 0.3')
                pass
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

                # level.arraychannels = channels
                    
                # estimated_max_size = channels
                # for dim in totalshape_no_ch:
                #     estimated_max_size *= dim
                # estimated_max_size = human_size(estimated_max_size *4) # vdb's are 32 bit floats == 4 byte per voxel

                level.level_descriptor = f"{scale['path']}: {zarray.shape}, up to {estimated_max_size}"
                bpy.context.scene.MiN_selected_zarr_level = level.level_descriptor
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


def append_uri(uri, append):
    if Path(uri).exists():
        return Path(uri) / append
    if uri[-1] != '/':
        uri += "/"
    return urljoin(uri, append)

