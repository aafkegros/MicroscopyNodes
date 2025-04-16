from .arrayloading import ArrayLoader
from ..handle_blender_structs.progress_handling import log
import numpy as np
from zarr.core import Array as ZarrArray
import zarr
from zarr.storage import FSStore, LRUStoreCache
import json
import os
import bpy
from pathlib import Path
from urllib.parse import urljoin
from .arrayoptions import copy_array_option

OME_ZARR_V_0_4_KWARGS = dict(dimension_separator="/", normalize_keys=False)
OME_ZARR_V_0_1_KWARGS = dict(dimension_separator=".")


class ZarrLoader(ArrayLoader):
    suffixes = ['.zarr']

    def check_path(self):
        # .zarr can also not be the suffix
        super().check_path()
        return self.suffixes[0] in str(bpy.context.scene.MiN_input_file)

    def set_file_globals(self, input_file):
        try:
            file_globals, _ = self.parse_zattrs(input_file)
        except KeyError as e:
            log(f"Could not parse .zattrs, see print log for detail")
        self._set_axes_order(file_globals['axes_order'])
        self._set_unit(file_globals['unit'])
        self._set_ch_names(file_globals['ch_names'])
        return

    def fill_array_options(self, input_file):
        try:
            _, file_array_options = self.parse_zattrs(input_file)
        except KeyError as e:
            log(f"Could not parse .zattrs, see print log for detail")    
        
        for file_option in file_array_options:
            copy_array_option(file_option)

    def load_array(self, input_file, array_option):
        uncached_store = FSStore(append_uri(array_option.store, array_option.path), mode="r", **OME_ZARR_V_0_4_KWARGS)
        store = LRUStoreCache(uncached_store, max_size=5*(10**9))
        zarray = ZarrArray(store=store)
        return zarray

    def parse_zattrs(self, uri):
        if uri.startswith("file:"):
            # Primarily this is to deal with spaces in Windows paths (encoded as %20).
            uri = os.fsdecode(unquote_to_bytes(uri))
        uri = str(uri)
        
        uncached_store = FSStore(uri, mode="r", **OME_ZARR_V_0_4_KWARGS)
        ome_spec = json.loads(uncached_store[".zattrs"]) # this fails if .zattrs don't exist - intentionally
        
        if ome_spec.get("multiscales", [{}])[0].get("version") == "0.1":
            uncached_store = FSStore(uri, mode="r", **OME_ZARR_V_0_1_KWARGS)
        store = LRUStoreCache(uncached_store, max_size=10**9)
        file_globals = {}
        array_options = []
        file_globals['ch_names'] = [c.get('label') for c in ome_spec.get('omero', {}).get('channels', [])]
        for multiscale_spec in ome_spec["multiscales"]: # technically supports multiple multiscales, but as this is uncommon, some stuff may break with it (e.g. axis order)
            file_globals['axes_order'] =  _get_axes_order_from_spec(multiscale_spec)
            axes_order = file_globals['axes_order']
            datasets = multiscale_spec["datasets"]
            file_globals['unit'] = next(iter([axis['unit'] for axis in multiscale_spec["axes"] if axis['type'] == 'space']), None)
            for scale in datasets:  # OME-Zarr spec requires datasets ordered from high to low resolution
                array_options.append({})
                level  = array_options[-1]
                level['store'] = uri
                level['path'] =  scale['path']
                if "coordinateTransformations" in scale:
                    scaletransform = [transform for transform in scale['coordinateTransformations'] if transform['type'] == 'scale'][0]
                    level['xy_size'] = scaletransform['scale'][axes_order.find('x')]
                    if 'z' in axes_order:
                        level['z_size'] = scaletransform['scale'][axes_order.find('z')]
                zarray = ZarrArray(store=store, path=scale["path"])
                level['shape'] = zarray.shape
                if np.issubdtype(zarray.dtype,np.floating):
                    log("Floating point arrays cannot be loaded lazily, will use a lot of RAM")
        return file_globals, array_options


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

