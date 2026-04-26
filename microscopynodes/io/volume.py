import bpy
from pathlib import Path
import numpy as np
import math
import itertools

from .base import DataIO
from ..handle_blender_structs import len_axis, log, to_xyz
from ..handle_blender_structs.props import min_keys


NR_HIST_BINS = 2**16


def get_leading_trailing_zero_float(arr):
    min_val = max(np.argmax(arr > 0) - 1, 0) / len(arr)
    max_val = min(len(arr) - (np.argmax(arr[::-1] > 0) - 1), len(arr)) / len(arr)
    return min_val, max_val


class VolumeIO(DataIO):
    min_type = min_keys.VOLUME
    VDB_TEMPLATE = Path("{cache_dir}") / "{dataset_hash}" / "{scale}" / "x{x}y{y}z{z}_c{channel_ix}_t{t}.vdb"

    def generate_file_constructors(self, ch):
        file_constructors = []
        xyz_shape = [len_axis(dim, ch.axes_order, ch.data.shape) for dim in "xyz"]
        maxlen = np.inf
        if bpy.context.scene.MiN_chunk:
            maxlen = 2048
        slices_xyz = [self.split_axis_to_chunks(dimshape, ch.ix, maxlen) for dimshape in xyz_shape]
        time_slices = [slice(t, t + 1) for t in range(ch.frame_start, min(ch.frame_end + 1, len_axis("t", ch.axes_order, ch.data.shape)))]
        slices_xyzt = slices_xyz + [time_slices]

        for block in itertools.product(*slices_xyzt):
            file_constructors.append({
                **self.base_constructor(ch),
                "scale": ch.dataset_resolution,
                "x": block[0].start,
                "y": block[1].start,
                "z": block[2].start,
                "x_end": block[0].stop,
                "y_end": block[1].stop,
                "z_end": block[2].stop,
                "t": block[3].start,
                "t_end": block[3].stop,
                "channel_ix": ch.ix,
                "template_str": str(self.VDB_TEMPLATE),
            })
        return file_constructors

    def export_ch(self, ch, file_constructors):
        if np.issubdtype(ch.data.dtype, np.floating):
            max_val = ch.data.max()
        else:
            max_val = min(np.iinfo(ch.data.dtype).max, np.iinfo(np.int32).max)
        for constructor in file_constructors:
            vdbfname = Path(str(self.VDB_TEMPLATE).format(**constructor))
            histfname = vdbfname.with_suffix(".npz")
            vdbfname.parent.mkdir(parents=True, exist_ok=True)

            if (not vdbfname.exists() or not histfname.exists()) or ch.force_remaking_files:
                vdbfname.unlink(missing_ok=True)
                histfname.unlink(missing_ok=True)
                log(f"loading chunk {Path(vdbfname).stem}")
                arr = ch.data[tuple(
                    slice(constructor[dim], constructor[f"{dim}_end"]) for dim in ch.axes_order
                )].compute()

                arr = to_xyz(arr, ch.axes_order)
                arr = arr.astype(np.float32) / max_val
                histogram = np.histogram(arr, bins=NR_HIST_BINS, range=(0.0, 1.0))[0]
                histogram[0] = 0
                np.savez(histfname, data=histogram, metadata={"data_max": max_val}, allow_pickle=False)
                log(f"write vdb {vdbfname.name}")
                self.make_vdb(vdbfname, arr)
        return []

    def split_axis_to_chunks(self, length, ch_ix, maxlen):
        offset = 0
        if length > maxlen:
            offset = (300 * ch_ix) % 2048
        n_splits = int((length // (maxlen + 1)) + 1)
        splits = [length / n_splits * split for split in range(n_splits + 1)]
        splits[-1] = math.ceil(splits[-1])
        splits = [math.floor(split) + offset for split in splits]
        if offset > 0:
            splits.insert(0, 0)
        while splits[-2] > length:
            del splits[-1]
        splits[-1] = length
        return [slice(start, end) for start, end in zip(splits[:-1], splits[1:])]

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

    def get_metadata(self, file_constructors):
        hist = np.zeros(NR_HIST_BINS)
        data_max = 1.0
        for constructor in file_constructors:
            histfname = Path(str(constructor["template_str"]).format(**constructor)).with_suffix(".npz")
            try:
                hist += np.load(histfname, allow_pickle=False)["data"]
                data_max = np.load(histfname, allow_pickle=True)["metadata"].item()["data_max"]
            except Exception as e:
                print(e, " in reading histogram, skipping chunk")
                hist += np.zeros(NR_HIST_BINS)
        if not np.any(hist):
            return {"range": (0, 1), "vdb_min": 0, "vdb_max": 1, "histogram": np.zeros(NR_HIST_BINS), "threshold": 0, "threshold_upper": 1.0}

        r0, r1 = get_leading_trailing_zero_float(hist)
        cropped = hist[int(r0 * NR_HIST_BINS): int(r1 * NR_HIST_BINS)]
        threshold = threshold_isodata(hist=cropped)

        cs = np.cumsum(cropped)
        threshold_upper = max(threshold + 2, np.searchsorted(cs, np.percentile(cs, 70)))

        if threshold < 30:
            threshold = 1
            threshold_upper = len(cropped)

        return {
            "range": (r0, r1),
            "vdb_min": r0,
            "vdb_max": r1,
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
    lower = csum_intensity[:-1] / csuml[:-1]
    higher = (csum_intensity[-1] - csum_intensity[:-1]) / csumh[:-1]
    all_mean = (lower + higher) / 2.0
    bin_width = bin_centers[1] - bin_centers[0]
    distances = all_mean - bin_centers[:-1]
    thresholds = bin_centers[:-1][(distances >= 0) & (distances < bin_width)]
    return thresholds if return_all else thresholds[0]
