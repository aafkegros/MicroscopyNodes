import os
from pathlib import Path
from urllib.parse import unquote_to_bytes, urljoin

import numpy as np

from ..data_model import ChannelDataModel, ChannelModel, ChannelVizModel, DatasetModel
from ..handle_blender_structs.progress_handling import log
from ..handle_blender_structs.units import unit_value

class ZarrLoader:
    """Create DatasetModels for OME-Zarr inputs.

    native_options() returns one DatasetModel for each native multiscale level.
    Each dataset contains one ChannelModel per channel. The ChannelDataModels
    store the dask array for that scale, channel index, source axes, affine pixel
    scale, unit, source path, and native resolution id used by the importer.
    """

    suffixes = ['.zarr']

    def native_options(self, input_file, axes_order=None, unit=None, **data_kwargs):

        import bpy, obstore, zarrista, ngff_zarr
        from ngff_zarr._remote_reader import remote_read_available

        print(bpy.app.version_string, ngff_zarr.__file__, remote_read_available())
        metadata = self.metadata(input_file)
        axes_order = axes_order or metadata["axes_order"]
        unit = unit_value(unit if unit is not None else metadata["unit"])

        datasets = []
        for option in metadata["options"]:
            array = option["array"]
            channel_count = array.shape[axes_order.find('c')] if 'c' in axes_order else 1
            data_axes_order = axes_order.replace('c', '')
            affine = option["affine"]

            channels = []
            for ch_ix in range(channel_count):
                channels.append(ChannelModel(
                    cache_path="",
                    source_name=self._channel_name(metadata["ch_names"], ch_ix),
                    data=ChannelDataModel(
                        dataset_resolution=option["identifier"],
                        ix=ch_ix,
                        axes_order=data_axes_order,
                        source_axes_order=axes_order,
                        internal_path=option["path"],
                        affine=affine,
                        unit=unit,
                        source=str(input_file),
                        **data_kwargs,
                    ),
                    viz=ChannelVizModel(ix=ch_ix),
                ))

            datasets.append(DatasetModel(
                name=f"{Path(str(input_file)).name}:{option['path']}",
                channels=channels,
            ))

        return datasets

    def metadata(self, input_file):
        from ngff_zarr import from_ome_zarr

        uri = str(input_file)
        if uri.startswith("file:"):
            uri = os.fsdecode(unquote_to_bytes(uri.removeprefix("file:")))
        storage_options = {"anon": True} if uri.startswith("s3://") else None
        multiscales = from_ome_zarr(uri, storage_options=storage_options)
        metadata = multiscales.metadata
        intrinsic = getattr(metadata, "intrinsic_coordinate_system", None)
        axes = intrinsic.axes if intrinsic is not None else metadata.axes
        omero = metadata.omero
        options = []
        for index, (image, dataset) in enumerate(zip(multiscales.images, metadata.datasets, strict=True)):
            xy_size = image.scale.get("x", 1.0)
            z_size = image.scale.get("z", xy_size)
            options.append({
                "identifier": index,
                "path": dataset.path,
                "array": image.data,
                "shape": image.data.shape,
                "affine": np.diag([xy_size, xy_size, z_size, 1]).tolist(),
                "xy_size": xy_size,
                "z_size": z_size,
            })
            if np.issubdtype(image.data.dtype, np.floating):
                log("Floating point arrays cannot be loaded lazily, will use a lot of RAM")

        return {
            "axes_order": "".join(multiscales.images[0].dims),
            "unit": next((axis.unit for axis in axes if axis.type == "space" and axis.unit), None),
            "ch_names": [channel.label for channel in omero.channels] if omero else [],
            "options": options,
        }

    def _channel_name(self, ch_names, ch_ix):
        if ch_ix < len(ch_names) and ch_names[ch_ix]:
            return ch_names[ch_ix]
        return None


def append_uri(uri, append):
    if Path(uri).exists():
        return Path(uri) / append
    if uri[-1] != '/':
        uri += "/"
    return urljoin(uri, append)
