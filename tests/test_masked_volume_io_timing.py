import os
from pathlib import Path
from types import SimpleNamespace
from time import perf_counter

import dask.array as da
import numpy as np
import pytest

from microscopynodes.io.volume import VolumeIO


def _procedural_data(shape, chunks):
    def block_values(block, block_info=None):
        loc = block_info[None]["array-location"]
        starts = [axis_loc[0] for axis_loc in loc]
        grids = np.indices(block.shape, dtype=np.float32)
        return (
            grids[0]
            + starts[0]
            + (grids[1] + starts[1]) * 0.01
            + (grids[2] + starts[2]) * 0.0001
        ).astype(np.float32)

    empty = da.empty(shape, chunks=chunks, dtype=np.float32)
    return empty.map_blocks(block_values, dtype=np.float32)


def _mask_from_box(mask_shape, box_offset, box_shape):
    mask = np.zeros(mask_shape, dtype=bool)
    box_slices = tuple(
        slice(offset, min(offset + size, axis_size))
        for offset, size, axis_size in zip(box_offset, box_shape, mask_shape)
    )
    mask[box_slices] = True
    return mask


def _channel(data, mask):
    return SimpleNamespace(
        data=SimpleNamespace(
            axes_order="xyz",
            data=data,
            mask=mask,
        )
    )


def _gib(shape, dtype=np.float32):
    return np.prod(shape) * np.dtype(dtype).itemsize / 1024**3


def _region_voxel_count(io, ch):
    data_shape = io.data_shape_xyz(ch)
    mask = np.asarray(ch.data.mask, dtype=bool)
    active = np.argwhere(mask)
    if len(active) == 0:
        return 0

    axis_counts = []
    for axis in range(3):
        mask_shape = mask.shape[axis]
        data_length = data_shape[axis]
        starts = np.floor(np.arange(mask_shape) * data_length / mask_shape).astype(int)
        stops = np.floor(np.arange(1, mask_shape + 1) * data_length / mask_shape).astype(int)
        axis_counts.append(stops - starts)

    return int(sum(np.prod([axis_counts[axis][index] for axis, index in enumerate(mask_index)]) for mask_index in active))


@pytest.mark.parametrize(
    ("data_shape", "data_chunks", "mask_shape", "mask_chunks", "box_offset", "box_shape"),
    [
        ((32, 32, 32), (16, 16, 16), (16, 16, 16), (8, 8, 8), (0, 0, 0), (3, 4, 5)),
        ((32, 32, 32), (16, 16, 16), (16, 16, 16), (8, 8, 8), (5, 6, 7), (4, 3, 2)),
        ((64, 64, 32), (16, 16, 16), (32, 32, 16), (8, 8, 8), (12, 9, 4), (5, 6, 4)),
    ],
)
def test_masked_volume_writer_timing_for_sizes_and_offsets(
    tmp_path,
    data_shape,
    data_chunks,
    mask_shape,
    mask_chunks,
    box_offset,
    box_shape,
):
    data = _procedural_data(data_shape, data_chunks)
    mask = _mask_from_box(mask_shape, box_offset, box_shape)
    ch = _channel(data, mask)
    constructor = {"t": 0}
    vdb_path = Path(tmp_path) / (
        f"masked_{'x'.join(map(str, data_shape))}_"
        f"offset_{'_'.join(map(str, box_offset))}.vdb"
    )

    io = VolumeIO()
    started = perf_counter()
    histogram_values = io.make_masked_vdb(vdb_path, ch, constructor, scale=1.0)
    elapsed = perf_counter() - started

    active_mask_voxels = int(np.count_nonzero(mask))
    data_per_mask_voxel = int(np.prod(np.array(data_shape) // np.array(mask_shape)))
    expected_max_values = active_mask_voxels * data_per_mask_voxel
    region_voxels = _region_voxel_count(io, ch)

    print(
        "masked_vdb_timing",
        f"data_shape={data_shape}",
        f"mask_shape={mask_shape}",
        f"box_offset={box_offset}",
        f"written_values={len(histogram_values)}",
        f"expected_max_values={expected_max_values}",
        f"region_voxels={region_voxels}",
        f"elapsed={elapsed:.4f}s",
    )

    assert vdb_path.exists()
    assert vdb_path.stat().st_size > 0
    assert len(histogram_values) > 0


@pytest.mark.skipif(
    os.environ.get("MIN_RUN_MILLION_VALUE_VDB_TIMING") != "1",
    reason="set MIN_RUN_MILLION_VALUE_VDB_TIMING=1 to run million-value masked VDB timing",
)
@pytest.mark.parametrize(
    ("data_shape", "data_chunks", "mask_shape", "mask_chunks", "box_offset", "box_shape"),
    [
        ((256, 256, 256), (32, 32, 32), (128, 128, 128), (16, 16, 16), (0, 0, 0), (50, 50, 50)),
        ((256, 256, 256), (32, 32, 32), (128, 128, 128), (16, 16, 16), (60, 40, 20), (50, 50, 50)),
    ],
)
def test_masked_volume_writer_timing_millions_of_values(
    tmp_path,
    data_shape,
    data_chunks,
    mask_shape,
    mask_chunks,
    box_offset,
    box_shape,
):
    data = _procedural_data(data_shape, data_chunks)
    mask = _mask_from_box(mask_shape, box_offset, box_shape)
    ch = _channel(data, mask)
    constructor = {"t": 0}
    vdb_path = Path(tmp_path) / (
        f"masked_million_{'x'.join(map(str, data_shape))}_"
        f"offset_{'_'.join(map(str, box_offset))}.vdb"
    )

    io = VolumeIO()
    started = perf_counter()
    histogram_values = io.make_masked_vdb(vdb_path, ch, constructor, scale=1.0)
    elapsed = perf_counter() - started

    active_mask_voxels = int(np.count_nonzero(mask))
    data_per_mask_voxel = int(np.prod(np.array(data_shape) // np.array(mask_shape)))
    expected_max_values = active_mask_voxels * data_per_mask_voxel
    region_voxels = _region_voxel_count(io, ch)

    print(
        "masked_vdb_timing_millions",
        f"data_shape={data_shape}",
        f"mask_shape={mask_shape}",
        f"box_offset={box_offset}",
        f"written_values={len(histogram_values)}",
        f"expected_max_values={expected_max_values}",
        f"region_voxels={region_voxels}",
        f"elapsed={elapsed:.4f}s",
        f"values_per_second={len(histogram_values) / max(elapsed, 1e-9):.0f}",
    )

    assert expected_max_values >= 1_000_000
    assert vdb_path.exists()
    assert vdb_path.stat().st_size > 0
    assert 0 < len(histogram_values) <= region_voxels
    assert len(histogram_values) >= region_voxels - 1


@pytest.mark.skipif(
    os.environ.get("MIN_RUN_10GIB_VDB_TIMING") != "1",
    reason="set MIN_RUN_10GIB_VDB_TIMING=1 to run logical 10 GiB masked VDB timing",
)
@pytest.mark.parametrize(
    ("data_shape", "data_chunks", "mask_shape", "mask_chunks", "box_offset", "box_shape"),
    [
        ((2048, 2048, 640), (64, 64, 64), (1024, 1024, 320), (32, 32, 32), (0, 0, 0), (50, 50, 50)),
        ((2048, 2048, 640), (64, 64, 64), (1024, 1024, 320), (32, 32, 32), (400, 300, 100), (50, 50, 50)),
    ],
)
def test_masked_volume_writer_timing_logical_10gib_data(
    tmp_path,
    data_shape,
    data_chunks,
    mask_shape,
    mask_chunks,
    box_offset,
    box_shape,
):
    data = _procedural_data(data_shape, data_chunks)
    mask = _mask_from_box(mask_shape, box_offset, box_shape)
    ch = _channel(data, mask)
    constructor = {"t": 0}
    vdb_path = Path(tmp_path) / (
        f"masked_10gib_{'x'.join(map(str, data_shape))}_"
        f"offset_{'_'.join(map(str, box_offset))}.vdb"
    )

    io = VolumeIO()
    started = perf_counter()
    histogram_values = io.make_masked_vdb(vdb_path, ch, constructor, scale=1.0)
    elapsed = perf_counter() - started

    active_mask_voxels = int(np.count_nonzero(mask))
    data_per_mask_voxel = int(np.prod(np.array(data_shape) // np.array(mask_shape)))
    expected_max_values = active_mask_voxels * data_per_mask_voxel
    region_voxels = _region_voxel_count(io, ch)

    print(
        "masked_vdb_timing_10gib",
        f"logical_gib={_gib(data_shape):.2f}",
        f"data_shape={data_shape}",
        f"mask_shape={mask_shape}",
        f"box_offset={box_offset}",
        f"written_values={len(histogram_values)}",
        f"expected_max_values={expected_max_values}",
        f"region_voxels={region_voxels}",
        f"elapsed={elapsed:.4f}s",
        f"values_per_second={len(histogram_values) / max(elapsed, 1e-9):.0f}",
    )

    assert _gib(data_shape) >= 10.0
    assert expected_max_values >= 1_000_000
    assert vdb_path.exists()
    assert vdb_path.stat().st_size > 0
    assert 0 < len(histogram_values) <= region_voxels
    assert len(histogram_values) >= region_voxels - 1
