import importlib.util
import os
from pathlib import Path
from urllib.parse import unquote_to_bytes, urljoin

import clearscale as cs
import numpy as np
import zarr

from ..data_model import ChannelDataModel, ChannelModel, ChannelVizModel, DatasetModel
from ..handle_blender_structs.progress_handling import log
from ..handle_blender_structs.units import unit_value

OME_ZARR_V_0_4_KWARGS = dict(dimension_separator="/", normalize_keys=False)
OME_ZARR_V_0_1_KWARGS = dict(dimension_separator=".")
MAX_LOGGED_ERROR_LENGTH = 160


class OmeZarrLoadError(ValueError):
    """The zarr group does not hold a valid OME-Zarr image that can be loaded."""


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
            channel_count = array.shape[axes_order.find('c')] if 'c' in axes_order else 1
            data_axes_order = axes_order.replace('c', '')

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
                        affine=option["affine"],
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
        try:
            file_globals, options = self.parse_zattrs(input_file)
        except OmeZarrLoadError as e:
            print(f"Could not load OME-Zarr: {e}")
            log(_shortened(str(e)))
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
        store = _s3_store(uri) if uri.startswith("s3://") else uri
        try:
            return zarr.open_group(store, mode='r')
        except ModuleNotFoundError as e:
            if "fsspec" not in str(e):
                raise
            raise ModuleNotFoundError(f"Could not import fsspec dependency ({_fsspec_info()})") from e

    def parse_zattrs(self, uri):
        group = self.open_zarr(uri)

        zarrays = {}

        def array_shape(path):
            """Callback to cache zarray handles while from_attrs uses them to obtain array shapes"""
            zarrays[path] = zarr.open_array(store=group.store, path=path)
            return zarrays[path].shape

        multiscale = _loadable_multiscale(cs.OmeZarrGroup.from_attrs(group.attrs, shape_source=array_shape))

        omero = multiscale.ome.omero
        file_globals = {
            "ch_names": [channel.label or "" for channel in (omero.channels if omero else ())],
            "axes_order": "".join(str(axis) for axis in multiscale.axes),
            "unit": _first_space_unit(multiscale),
        }

        space_axes = _space_axes(multiscale)
        options = []
        for path, scale in multiscale.items():
            scale = _in_unit_of_first_axis(scale, space_axes)
            pixel_size = scale.pixel_size
            default_size = pixel_size.get("x", 1.0)
            sizes = [pixel_size.get(axis, default_size) for axis in "xyz"]
            affine = np.diag([*sizes, 1.0])
            affine[:3, 3] = [scale.translation.get(axis, 0.0) for axis in "xyz"]
            zarray = zarrays[path]
            option = {
                "identifier": len(options),
                "store": uri,
                "path": path,
                "affine": affine.tolist(),
                "array": zarray,
                "shape": zarray.shape,
            }
            if np.issubdtype(zarray.dtype, np.floating):
                log("Floating point arrays cannot be loaded lazily, will use a lot of RAM")
            options.append(option)

        return file_globals, options

    def _channel_name(self, ch_names, ch_ix):
        if ch_ix < len(ch_names) and ch_names[ch_ix]:
            return ch_names[ch_ix]
        return None


def _loadable_multiscale(ome_group) -> cs.Multiscale:
    """The first valid multiscale of the group, or an OmeZarrLoadError that says why there is none."""
    if ome_group.multiscales:
        return ome_group.multiscales[0]
    if ome_group.kind is None:
        raise OmeZarrLoadError("No OME-Zarr image found at this path.")
    if ome_group.kind is cs.GroupKind.INVALID:
        raise OmeZarrLoadError(f"Found invalid or unsupported OME-Zarr: {ome_group.invalid_objects[0].error}")
    hint = f" (e.g. '{ome_group.children[0].path}')" if ome_group.children else ""
    raise OmeZarrLoadError(
        f"This {ome_group.kind.value} group holds no image itself, try a path of an image inside it{hint}."
    )


def _space_axes(multiscale: cs.Multiscale):
    return [axis for axis, ome_axis in multiscale.ome_zarr_axes.items() if ome_axis.type == "space"]


def _first_space_unit(multiscale):
    for axis in _space_axes(multiscale):
        return multiscale.unit[axis] or None
    return None


def _in_unit_of_first_axis(scale: cs.Scale, space_axes):
    """Pixel sizes of the space axes expressed in the unit of the first one, so that their sizes can be compared.
    A Scale whose units can not be converted (e.g. unspecified or unrecognized) is kept as it is."""
    if not space_axes or len({scale.unit[axis] for axis in space_axes}) == 1:
        return scale
    try:
        return scale.with_unit_converted({axis: scale.unit[space_axes[0]] for axis in space_axes})
    except ValueError:
        return scale


def _shortened(message):
    if len(message) <= MAX_LOGGED_ERROR_LENGTH:
        return message
    return message[:MAX_LOGGED_ERROR_LENGTH].rstrip() + "…"


def append_uri(uri, append):
    if Path(uri).exists():
        return Path(uri) / append
    if uri[-1] != '/':
        uri += "/"
    return urljoin(uri, append)


def _s3_store(uri):
    try:
        import s3fs
    except ModuleNotFoundError as e:
        raise ModuleNotFoundError(f"s3 zarr requires s3fs ({_fsspec_info()})") from e
    return s3fs.S3Map(root=uri, s3=s3fs.S3FileSystem(anon=True), check=False)


def _fsspec_info():
    try:
        import fsspec
    except ModuleNotFoundError:
        return "missing"

    chained = importlib.util.find_spec("fsspec.implementations.chained") is not None
    return (
        f"{getattr(fsspec, '__version__', 'unknown')} "
        f"at {getattr(fsspec, '__file__', 'unknown')}, chained={chained}"
    )
