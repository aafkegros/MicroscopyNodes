import bpy
import itertools
from pathlib import Path
import time
import numpy as np

from .base import DataIO
from ..handle_blender_structs.array_handling import len_axis, to_xyz
from ..handle_blender_structs.progress_handling import log
from ..handle_blender_structs.min_keys import min_keys


NR_HIST_BINS = 2**16
MIN_MASKED_CHUNK_SIZE_XYZ = (256, 256, 128)


def get_leading_trailing_zero_float(arr):
    min_val = max(np.argmax(arr > 0) - 1, 0) / len(arr)
    max_val = min(len(arr) - (np.argmax(arr[::-1] > 0) - 1), len(arr)) / len(arr)
    return min_val, max_val


def lerp(left, right, amount):
    return left + (right - left) * amount


class VolumeIO(DataIO):
    min_type = min_keys.VOLUME
    VDB_TEMPLATE = Path("{cache_dir}") / "{dataset_hash}" / "{scale}" / "mask_{masked}_c{channel_ix}_t{t}.vdb"

    def generate_file_constructors(self, ch):
        file_constructors = []
        masked = str(time.time_ns()) if ch.data.mask is not None else "False"
        for t in range(ch.data.frame_start, min(ch.data.frame_end + 1, len_axis("t", ch.data.axes_order, ch.data.data.shape))):
            file_constructors.append({
                **self.base_constructor(ch),
                "scale": ch.data.dataset_resolution,
                "masked": masked,
                "t": t,
                "channel_ix": ch.data.ix,
                "template_str": str(self.VDB_TEMPLATE),
            })
        return file_constructors

    def export_ch(self, ch, file_constructors):
        data_min, data_max = self.get_data_range(ch)
        scale = max(abs(data_min), abs(data_max))
        if scale == 0:
            scale = 1.0
        hist_range = (-1.0, 1.0) if data_min < 0 else (0.0, 1.0)

        original_max = scale
        for constructor in file_constructors:
            vdbfname = Path(str(self.VDB_TEMPLATE).format(**constructor))
            histfname = vdbfname.with_suffix(".npz")
            vdbfname.parent.mkdir(parents=True, exist_ok=True)

            if (not vdbfname.exists() or not histfname.exists()) or ch.force_remaking_files:
                vdbfname.unlink(missing_ok=True)
                histfname.unlink(missing_ok=True)
                log(f"loading volume {Path(vdbfname).stem}")
                if ch.data.mask is None:
                    arr = ch.data.data[tuple(
                        slice(constructor["t"], constructor["t"] + 1) if dim == "t" else slice(None)
                        for dim in ch.data.axes_order
                    )].compute()
                    arr = to_xyz(arr, ch.data.axes_order)
                    arr = arr.astype(np.float32) / original_max
                    self.make_vdb(vdbfname, arr)
                    histogram_values = arr
                else:
                    histogram_values = self.make_masked_vdb(vdbfname, ch, constructor, original_max)

                histogram = np.histogram(histogram_values, bins=NR_HIST_BINS, range=hist_range)[0]
                zero_bin = int(np.searchsorted(np.linspace(*hist_range, NR_HIST_BINS + 1), 0.0, side="right") - 1)
                histogram[max(zero_bin, 0)] = 0
                np.savez(
                    histfname,
                    data=histogram,
                    data_max=np.array(original_max, dtype=np.float64),
                    hist_min=np.array(hist_range[0], dtype=np.float64),
                    hist_max=np.array(hist_range[1], dtype=np.float64),
                    allow_pickle=False,
                )
                log(f"write vdb {vdbfname.name}")
        return []

    def get_data_range(self, ch):
        if np.issubdtype(ch.data.data.dtype, np.floating):
            data_min = float(ch.data.data.min().compute())
            data_max = float(ch.data.data.max().compute())
            return data_min, data_max

        info = np.iinfo(ch.data.data.dtype)
        return float(info.min), float(info.max)

    def make_vdb(self, vdbfname, arr):
        try:
            import openvdb as vdb
        except Exception:
            bpy.utils.expose_bundled_modules()
            import openvdb as vdb
        grid = vdb.FloatGrid()
        grid.name = "data"
        grid.copyFromArray(arr)
        vdb.write(str(vdbfname), grids=[grid])
        return

    def make_masked_vdb(self, vdbfname, ch, constructor, scale):
        try:
            import openvdb as vdb
        except Exception:
            bpy.utils.expose_bundled_modules()
            import openvdb as vdb

        grid = vdb.FloatGrid()
        grid.name = "data"
        acc = grid.getAccessor()
        histogram_values = []
        for xyz_start, data_region, mask_region in self.iter_masked_data_blocks(ch, constructor):
            data_block = data_region.compute()
            data_block = to_xyz(data_block, ch.data.axes_order)
            arr = data_block.astype(np.float32) / scale
            values = arr[mask_region]
            nonzero_values = values[values != 0]
            if len(nonzero_values) > 0:
                histogram_values.append(nonzero_values)

            xs, ys, zs = np.nonzero(mask_region)
            for dx, dy, dz in zip(xs, ys, zs):
                acc.setValueOn(
                    (int(xyz_start[0] + dx), int(xyz_start[1] + dy), int(xyz_start[2] + dz)),
                    float(arr[dx, dy, dz]),
                )
                # print(f"setting { (int(xyz_start[0] + dx), int(xyz_start[1] + dy), int(xyz_start[2] + dz))} to {float(arr[dx, dy, dz]),}")
        vdb.write(str(vdbfname), grids=[grid])
        if not histogram_values:
            return np.array([], dtype=np.float32)
        return np.concatenate(histogram_values)

    def iter_masked_data_blocks(self, ch, constructor):
        mask = ch.data.mask
        if hasattr(mask, "compute"):
            mask = mask.compute()
        mask = np.asarray(mask, dtype=bool)
        if not np.any(mask):
            return

        data = self.rechunk_masked_data(ch.data.data, ch.data.axes_order)
        data_shape = self.data_shape_xyz(ch)
        mask_shape = np.array(mask.shape, dtype=int)
        active_bounds = self.mask_data_bounds(mask, data_shape)
        spatial_slices = {
            dim: self.slices_overlapping_bounds(
                self.chunks_to_slices(data.chunks[ch.data.axes_order.index(dim)]),
                active_bounds[dim_ix],
            )
            for dim_ix, dim in enumerate("xyz")
            if dim in ch.data.axes_order
        }
        missing_spatial_slices = {
            dim: [slice(0, 1)]
            for dim in "xyz"
            if dim not in spatial_slices
        }
        spatial_slices = {**spatial_slices, **missing_spatial_slices}
        for region_slices in itertools.product(*(spatial_slices[dim] for dim in "xyz")):
            slices_by_dim = dict(zip("xyz", region_slices))
            xyz_start = np.array([
                slices_by_dim[dim].start if dim in slices_by_dim else 0
                for dim in "xyz"
            ], dtype=int)
            xyz_stop = np.array([
                slices_by_dim[dim].stop if dim in slices_by_dim else 1
                for dim in "xyz"
            ], dtype=int)
            mask_axis_indices = [
                np.minimum(
                    np.floor(np.arange(start, stop) * mask_length / data_length).astype(int),
                    mask_length - 1,
                )
                for start, stop, mask_length, data_length
                in zip(xyz_start, xyz_stop, mask_shape, data_shape)
            ]
            mask_region = mask[np.ix_(*mask_axis_indices)]
            if not np.any(mask_region):
                continue

            data_slices = tuple(
                slice(constructor["t"], constructor["t"] + 1)
                if dim == "t"
                else slices_by_dim[dim]
                for dim in ch.data.axes_order
            )
            yield xyz_start, data[data_slices], mask_region

    def rechunk_masked_data(self, data, axes_order):
        if not hasattr(data, "rechunk") or not hasattr(data, "chunks"):
            return data

        rechunk = {}
        for dim, target in zip("xyz", MIN_MASKED_CHUNK_SIZE_XYZ):
            if dim not in axes_order:
                continue
            axis = axes_order.index(dim)
            chunks = data.chunks[axis]
            if max(chunks) < target:
                rechunk[axis] = min(target, data.shape[axis])

        if not rechunk:
            return data

        return data.rechunk(rechunk)

    def mask_data_bounds(self, mask, data_shape):
        active = np.argwhere(mask)
        mask_start = active.min(axis=0)
        mask_stop = active.max(axis=0) + 1
        mask_shape = np.array(mask.shape, dtype=int)
        data_start = np.floor(mask_start * data_shape / mask_shape).astype(int)
        data_stop = np.ceil(mask_stop * data_shape / mask_shape).astype(int)
        data_start = np.clip(data_start, 0, data_shape)
        data_stop = np.clip(data_stop, data_start + 1, data_shape)
        return tuple(slice(int(start), int(stop)) for start, stop in zip(data_start, data_stop))

    def slices_overlapping_bounds(self, slices, bounds):
        overlapping = [
            region
            for region in slices
            if region.stop > bounds.start and region.start < bounds.stop
        ]
        return overlapping

    def data_shape_xyz(self, ch):
        return np.array([
            len_axis(dim, ch.data.axes_order, ch.data.data.shape)
            for dim in "xyz"
        ], dtype=int)

    def chunks_to_slices(self, chunks):
        starts = np.cumsum((0, *chunks[:-1]))
        return [slice(int(start), int(start + size)) for start, size in zip(starts, chunks)]

    def get_metadata(self, file_constructors):
        hist = np.zeros(NR_HIST_BINS)
        data_max = 1.0
        hist_min = 0.0
        hist_max = 1.0
        for constructor in file_constructors:
            histfname = Path(str(constructor["template_str"]).format(**constructor)).with_suffix(".npz")
            try:
                with np.load(histfname, allow_pickle=False) as histfile:
                    hist += histfile["data"]
                    if "hist_min" in histfile:
                        hist_min = min(hist_min, float(histfile["hist_min"].item()))
                    if "hist_max" in histfile:
                        hist_max = max(hist_max, float(histfile["hist_max"].item()))
                    if "data_max" in histfile:
                        data_max = float(histfile["data_max"].item())
                    else:
                        with np.load(histfname, allow_pickle=True) as legacy_histfile:
                            data_max = legacy_histfile["metadata"].item()["data_max"]
            except Exception as e:
                print(e, " in reading histogram, skipping chunk")
                hist += np.zeros(NR_HIST_BINS)
        if not np.any(hist):
            return {
                "range": (hist_min, hist_max),
                "vdb_min": hist_min,
                "vdb_max": hist_max,
                "zero": (0.0 - hist_min) / (hist_max - hist_min),
                "histogram": np.zeros(NR_HIST_BINS),
                "threshold": 0,
                "threshold_upper": 1.0,
                "data_max": data_max,
            }

        r0, r1 = get_leading_trailing_zero_float(hist)
        cropped = hist[int(r0 * NR_HIST_BINS): int(r1 * NR_HIST_BINS)]
        vdb_min = lerp(hist_min, hist_max, r0)
        vdb_max = lerp(hist_min, hist_max, r1)
        zero = (0.0 - vdb_min) / (vdb_max - vdb_min) if vdb_max != vdb_min else 0.0
        nonzero_bins = np.flatnonzero(cropped > 0)
        if len(nonzero_bins) ==1:
            return {
                "range": (vdb_min, vdb_max),
                "vdb_min": vdb_min,
                "vdb_max": vdb_max,
                "zero": zero,
                "histogram": cropped,
                "threshold": 0.01,
                "threshold_upper": 0.1,
                "data_max": data_max,
            }

        threshold = threshold_isodata(hist=cropped)

        cs = np.cumsum(cropped)
        threshold_upper = max(threshold + 2, np.searchsorted(cs, np.percentile(cs, 70)))

        if threshold < 30:
            threshold = 1
            threshold_upper = len(cropped)

        return {
            "range": (vdb_min, vdb_max),
            "vdb_min": vdb_min,
            "vdb_max": vdb_max,
            "zero": zero,
            "histogram": cropped,
            "threshold": threshold / len(cropped),
            "threshold_upper": threshold_upper / len(cropped),
            "data_max": data_max,
        }


def threshold_isodata(image=None, nbins=256, return_all=False, hist=None):
    if hist is None:
        hist, edges = np.histogram(image.ravel(), bins=nbins)
        bin_centers = (edges[:-1] + edges[1:]) / 2
    else:
        if isinstance(hist, tuple):
            hist, bin_centers = hist
        else:
            bin_centers = np.arange(len(hist))
    if len(bin_centers) == 1:
        return bin_centers if return_all else bin_centers[0]

    counts = hist.astype(float)
    csuml = np.cumsum(counts)
    csumh = csuml[-1] - csuml
    intensity_sum = counts * bin_centers
    csum_intensity = np.cumsum(intensity_sum)

    lower = np.divide(
        csum_intensity[:-1],
        csuml[:-1],
        out=np.full_like(csum_intensity[:-1], np.nan, dtype=float),
        where=csuml[:-1] != 0,
    )
    higher = np.divide(
        csum_intensity[-1] - csum_intensity[:-1],
        csumh[:-1],
        out=np.full_like(csumh[:-1], np.nan, dtype=float),
        where=csumh[:-1] != 0,
    )

    all_mean = (lower + higher) / 2.0
    bin_width = bin_centers[1] - bin_centers[0]
    distances = all_mean - bin_centers[:-1]
    valid = np.isfinite(distances)
    thresholds = bin_centers[:-1][valid & (distances >= 0) & (distances < bin_width)]

    if len(thresholds) == 0:
        return bin_centers if return_all else bin_centers[0]
    return thresholds if return_all else thresholds[0]
