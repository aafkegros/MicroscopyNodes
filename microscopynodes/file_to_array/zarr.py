from .arrayloading import ArrayLoader
from ..handle_blender_structs.progress_handling import log
import numpy as np
import zarr
import json
import os
import bpy
from pathlib import Path
from urllib.parse import urljoin
from .arrayoptions import copy_array_option
import s3fs

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
            print(f"key error: {e}")
            log(f"Could not parse .zattrs")
        self._set_axes_order(file_globals['axes_order'])
        if 'unit' in file_globals:
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
        return self.open_zarr(array_option.store)[array_option.path]

    def open_zarr(self, uri):
        if uri.startswith("file:"):
            # Primarily this is to deal with spaces in Windows paths (encoded as %20).
            uri = os.fsdecode(unquote_to_bytes(uri))
        uri = str(uri)
        if uri.startswith("s3://"):
            store = s3fs.S3Map(root=uri, s3=s3fs.S3FileSystem(anon=True), check=False)
        else:
            store=uri
            # store = FSStore(uri, mode="r")
        return zarr.open_group(store, mode='r')

    def parse_zattrs(self, uri):
        group = self.open_zarr(uri)
        try:
            multiscale_spec = group.attrs['multiscales'][0]
        except:
            multiscale_spec = group.attrs['ome']['multiscales'][0]

        file_globals = {}
        array_options = []
        file_globals['ch_names'] = [c.get('label') for c in group.attrs.get('omero', {}).get('channels', [])]
        file_globals['axes_order'] =  _get_axes_order_from_spec(multiscale_spec)
        # print(file_globa)
        axes_order = file_globals['axes_order']
        datasets = multiscale_spec["datasets"]
        try:
            file_globals['unit'] = next(iter([axis['unit'] for axis in multiscale_spec["axes"] if axis['type'] == 'space']), None)
        except:
            pass
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
            zarray = zarr.open_array(store=group.store, path=scale["path"])
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

