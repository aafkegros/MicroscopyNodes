from pathlib import Path

import dask.array as da
import numpy as np
import tifffile
import tifffile.zarr

from ..data_model import ChannelDataModel, ChannelModel, ChannelVizModel, DatasetModel
from ..handle_blender_structs.units import unit_value


class TifLoader:
    """Create DatasetModels for TIFF inputs.

    native_options() returns a list containing one DatasetModel for the TIFF
    series. The dataset contains one ChannelModel per channel. Each
    ChannelDataModel stores the dask array, channel index, source axes, affine
    pixel scale, unit, and source path needed by the importer.
    """

    suffixes = ['.tif', '.TIF', '.tiff', '.TIFF']

    def native_options(self, input_file, axes_order=None, unit=None, **data_kwargs):
        metadata = self.metadata(input_file)
        axes_order = axes_order or metadata["axes_order"]
        unit = unit_value(unit if unit is not None else metadata["unit"])

        imgdata = da.from_zarr(tifffile.imread(input_file, aszarr=True))
        channel_count = imgdata.shape[axes_order.find('c')] if 'c' in axes_order else 1
        data_axes_order = axes_order.replace('c', '')
        data_scale = [metadata["xy_size"], metadata["xy_size"], metadata["z_size"]]
        affine = np.diag([*data_scale, 1]).tolist()

        channels = []
        for ch_ix in range(channel_count):
            channels.append(ChannelModel(
                cache_path="",
                data=ChannelDataModel(
                    dataset_resolution=0,
                    ix=ch_ix,
                    data=imgdata,
                    axes_order=data_axes_order,
                    source_axes_order=axes_order,
                    affine=affine,
                    unit=unit,
                    source=str(input_file),
                    **data_kwargs,
                ),
                viz=ChannelVizModel(ix=ch_ix),
            ))

        return [DatasetModel(
            name=Path(input_file).name,
            channels=channels,
        )]

    def metadata(self, input_file):
        with tifffile.TiffFile(input_file) as tif:
            metadata = {
                "axes_order": tif.series[0].axes.lower().replace('s', 'c').replace('q', 'z'),
                "unit": None,
                "xy_size": self._xy_size(tif),
                "z_size": self._z_size(tif),
            }
            try:
                imagej_metadata = dict(tif.imagej_metadata)
                metadata["unit"] = imagej_metadata.get("unit")
            except TypeError:
                pass
        return metadata

    def _xy_size(self, tif):
        try:
            value = tif.pages[0].tags['XResolution'].value
            return value[1] / value[0]
        except Exception:
            return 1.0

    def _z_size(self, tif):
        try:
            return dict(tif.imagej_metadata)['spacing']
        except Exception:
            return 1.0
