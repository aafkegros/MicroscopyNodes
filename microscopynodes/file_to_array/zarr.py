import os
from pathlib import Path
from urllib.parse import unquote_to_bytes, urljoin

import dask.array as da
import numpy as np
import s3fs
import zarr

from ..data_model import ChannelDataModel, ChannelModel, ChannelVizModel, DatasetModel
from ..handle_blender_structs.progress_handling import log
from ..handle_blender_structs.units import unit_value

OME_ZARR_V_0_4_KWARGS = dict(dimension_separator="/", normalize_keys=False)
OME_ZARR_V_0_1_KWARGS = dict(dimension_separator=".")


class ZarrLoader:
    """Create DatasetModels for OME-Zarr inputs.

    native_options() returns one DatasetModel for each native multiscale level.
    Each dataset contains one ChannelModel per channel. The ChannelDataModels
    store the dask array for that scale, channel index, source axes, affine pixel
    scale, unit, source path, and native resolution id used by the importer.
    """

    suffixes = ['.zarr']

    def native_options(self, input_file, axes_order=None, unit=None, **data_kwargs):
        metadata = self.metadata(input_file)
        axes_order = axes_order or metadata["axes_order"]
        unit = unit_value(unit if unit is not None else metadata["unit"])

        datasets = []
        for option in metadata["options"]:
            array = self.load_array(option)
            imgdata = da.from_zarr(array)
            channel_count = imgdata.shape[axes_order.find('c')] if 'c' in axes_order else 1
            data_axes_order = axes_order.replace('c', '')
            data_scale = self._data_scale(option)
            affine = np.diag([*data_scale, 1]).tolist()

            channels = []
            for ch_ix in range(channel_count):
                channels.append(ChannelModel(
                    cache_path="",
                    data=ChannelDataModel(
                        dataset_resolution=option["identifier"],
                        ix=ch_ix,
                        data=imgdata,
                        axes_order=data_axes_order,
                        source_axes_order=axes_order,
                        affine=affine,
                        unit=unit,
                        source=str(input_file),
                        **data_kwargs,
                    ),
                    viz=ChannelVizModel(
                        ix=ch_ix,
                        name=self._channel_name(metadata["ch_names"], ch_ix),
                    ),
                ))

            datasets.append(DatasetModel(
                name=f"{Path(str(input_file)).name}:{option['path']}",
                channels=channels,
            ))

        return datasets

    def metadata(self, input_file):
        try:
            file_globals, options = self.parse_zattrs(input_file)
        except KeyError as e:
            print(f"key error: {e}")
            log("Could not parse .zattrs")
            return {
                "axes_order": "",
                "unit": None,
                "ch_names": [],
                "options": [],
            }
        return {
            **file_globals,
            "options": options,
        }

    def load_array(self, option):
        if "array" in option:
            return option["array"]
        return self.open_zarr(option["store"])[option["path"]]

    def open_zarr(self, uri):
        if uri.startswith("file:"):
            uri = os.fsdecode(unquote_to_bytes(uri))
        uri = str(uri)
        if uri.startswith("s3://"):
            store = s3fs.S3Map(root=uri, s3=s3fs.S3FileSystem(anon=True), check=False)
        else:
            store = uri
        return zarr.open_group(store, mode='r')

    def parse_zattrs(self, uri):
        group = self.open_zarr(uri)

        try:
            multiscale_spec = group.attrs['multiscales'][0]
        except Exception:
            multiscale_spec = group.attrs['ome']['multiscales'][0]

        file_globals = {
            "ch_names": [c.get('label') for c in group.attrs.get('omero', {}).get('channels', [])],
            "axes_order": _get_axes_order_from_spec(multiscale_spec),
        }
        axes_order = file_globals["axes_order"]

        try:
            file_globals["unit"] = next(iter([
                axis['unit']
                for axis in multiscale_spec["axes"]
                if axis['type'] == 'space'
            ]), None)
        except Exception:
            file_globals["unit"] = None

        options = []
        for scale in multiscale_spec["datasets"]:
            option = {
                "identifier": len(options),
                "store": uri,
                "path": scale["path"],
                "xy_size": 1.0,
                "z_size": 1.0,
            }
            if "coordinateTransformations" in scale:
                scaletransform = [
                    transform
                    for transform in scale['coordinateTransformations']
                    if transform['type'] == 'scale'
                ][0]
                option["xy_size"] = scaletransform['scale'][axes_order.find('x')]
                if 'z' in axes_order:
                    option["z_size"] = scaletransform['scale'][axes_order.find('z')]
                else:
                    option["z_size"] = option["xy_size"]

            zarray = zarr.open_array(store=group.store, path=scale["path"])
            option["array"] = zarray
            option["shape"] = zarray.shape
            if np.issubdtype(zarray.dtype, np.floating):
                log("Floating point arrays cannot be loaded lazily, will use a lot of RAM")
            options.append(option)

        return file_globals, options

    def _data_scale(self, option):
        return [option["xy_size"], option["xy_size"], option["z_size"]]

    def _channel_name(self, ch_names, ch_ix):
        if ch_ix < len(ch_names) and ch_names[ch_ix]:
            return ch_names[ch_ix]
        return None


def _get_axes_order_from_spec(validated_ome_spec):
    if "axes" in validated_ome_spec:
        ome_axes = validated_ome_spec["axes"]
        if "name" in ome_axes[0]:
            return "".join([d["name"] for d in ome_axes])
        return "".join(ome_axes)
    return "tczyx"


def append_uri(uri, append):
    if Path(uri).exists():
        return Path(uri) / append
    if uri[-1] != '/':
        uri += "/"
    return urljoin(uri, append)
