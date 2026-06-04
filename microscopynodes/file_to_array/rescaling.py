from copy import copy

import numpy as np

from ..data_model import ChannelModel, DatasetModel

DEFAULT_RESCALE_VECTORS = (
    (2, 2, 1),
    (2, 2, 2),
    (4, 4, 1),
    (4, 4, 2),
)
DEFAULT_TRIGGER_GIB = 1


def with_default_rescalings(dataset_models):
    if not dataset_models:
        return []

    source_dataset = dataset_models[-1]
    if _dataset_size_gib(source_dataset) <= DEFAULT_TRIGGER_GIB:
        return dataset_models

    next_resolution = len(dataset_models)
    rescaled = [
        rescale_dataset(source_dataset, rescale_xyz, next_resolution + ix)
        for ix, rescale_xyz in enumerate(DEFAULT_RESCALE_VECTORS)
    ]
    return dataset_models + rescaled


def rescale_dataset(dataset_model, rescale_xyz, dataset_resolution=None):
    rescale_xyz = normalize_rescale_xyz(rescale_xyz)
    channels = [
        _rescale_channel(channel, rescale_xyz, dataset_resolution)
        for channel in dataset_model.channels
    ]
    return DatasetModel(
        name=_rescaled_name(dataset_model.name, rescale_xyz),
        channels=channels,
        local_files_exist=dataset_model.local_files_exist,
    )


def rescale_dataset_to_target_shape(dataset_model, target_shape_xyz, dataset_resolution=None):
    rescale_xyz = _rescale_from_target_shape(dataset_model, target_shape_xyz)
    return rescale_dataset(dataset_model, rescale_xyz, dataset_resolution)


def normalize_rescale_xyz(rescale_xyz):
    if len(rescale_xyz) != 3:
        raise ValueError("rescale_xyz must contain x, y, and z factors.")
    normalized = tuple(max(int(value), 1) for value in rescale_xyz)
    return normalized


def _rescale_channel(channel_model, rescale_xyz, dataset_resolution):
    data = channel_model.data.model_copy(deep=False)
    data.source_data = _stride_rescale(
        data.source_data,
        data.source_axes_order or data.axes_order,
        rescale_xyz,
    )
    data._data_cache = None
    data.affine = _rescale_affine(data.affine, rescale_xyz)
    data.min_rescale_xyz = tuple(float(value) for value in rescale_xyz)
    if dataset_resolution is not None:
        data.dataset_resolution = dataset_resolution

    return ChannelModel(
        data=data,
        viz=channel_model.viz.model_copy(deep=True),
        cache_path=channel_model.cache_path,
        force_remaking_files=channel_model.force_remaking_files,
        metadata=copy(channel_model.metadata),
        file_constructors=copy(channel_model.file_constructors),
    )


def _stride_rescale(data, axes_order, rescale_xyz):
    slices = []
    for axis in axes_order:
        if axis in "xyz":
            step = int(rescale_xyz["xyz".find(axis)])
            slices.append(slice(None, None, max(step, 1)))
        else:
            slices.append(slice(None))
    return data[tuple(slices)]


def _rescale_affine(affine, rescale_xyz):
    matrix = np.array(affine, dtype=float)
    for ix, factor in enumerate(rescale_xyz):
        matrix[ix, ix] *= float(factor)
    return matrix.tolist()


def _rescale_from_target_shape(dataset_model, target_shape_xyz):
    target_shape_xyz = normalize_rescale_xyz(target_shape_xyz)
    channel_data = dataset_model.channels[0].data
    shape_xyz = [
        channel_data.data_shape[channel_data.axes_order.find(axis)]
        if axis in channel_data.axes_order else 1
        for axis in "xyz"
    ]
    return tuple(
        max(int(np.ceil(source / target)), 1)
        for source, target in zip(shape_xyz, target_shape_xyz)
    )


def _rescaled_name(name, rescale_xyz):
    suffix = f"downsample x{rescale_xyz[0]} y{rescale_xyz[1]} z{rescale_xyz[2]}"
    if name:
        return f"{name} {suffix}"
    return suffix


def _dataset_size_gib(dataset_model):
    return sum(_channel_size_bytes(channel) for channel in dataset_model.channels) / 2**30


def _channel_size_bytes(channel_model):
    dtype_size = getattr(channel_model.data.data_dtype, "itemsize", 4)
    size = dtype_size
    for dim in channel_model.data.data_shape:
        size *= dim
    return size
