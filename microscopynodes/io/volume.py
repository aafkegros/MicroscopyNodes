from pathlib import Path
import numpy as np

from .base import DataIO
from ..handle_blender_structs.array_handling import len_axis, to_xyz
from ..handle_blender_structs.progress_handling import log
from ..handle_blender_structs.min_keys import min_keys


NR_HIST_BINS = 2**16


def get_leading_trailing_zero_float(arr):
    min_val = max(np.argmax(arr > 0) - 1, 0) / len(arr)
    max_val = min(len(arr) - (np.argmax(arr[::-1] > 0) - 1), len(arr)) / len(arr)
    return min_val, max_val


class VolumeIO(DataIO):
    min_type = min_keys.VOLUME
    VDB_TEMPLATE = Path("{cache_dir}") / "{dataset_hash}" / "{scale}" / "mask_{masked}_c{channel_ix}_t{t}.vdb"

    def generate_file_constructors(self, ch):
        file_constructors = []
        for t in range(ch.data.frame_start, min(ch.data.frame_end + 1, len_axis("t", ch.data.axes_order, ch.data.data.shape))):
            file_constructors.append({
                **self.base_constructor(ch),
                "scale": ch.data.dataset_resolution,
                "masked": False,
                "t": t,
                "channel_ix": ch.data.ix,
                "template_str": str(self.VDB_TEMPLATE),
            })
        return file_constructors

    def export_ch(self, ch, file_constructors):
        if np.issubdtype(ch.data.data.dtype, np.floating):
            max_val = float(ch.data.data.max().compute())
        else:
            max_val = float(min(np.iinfo(ch.data.data.dtype).max, np.iinfo(np.int32).max))
        for constructor in file_constructors:
            vdbfname = Path(str(self.VDB_TEMPLATE).format(**constructor))
            histfname = vdbfname.with_suffix(".npz")
            vdbfname.parent.mkdir(parents=True, exist_ok=True)

            if (not vdbfname.exists() or not histfname.exists()) or ch.force_remaking_files:
                vdbfname.unlink(missing_ok=True)
                histfname.unlink(missing_ok=True)
                log(f"loading volume {Path(vdbfname).stem}")
                arr = ch.data.data[tuple(
                    slice(constructor["t"], constructor["t"] + 1) if dim == "t" else slice(None)
                    for dim in ch.data.axes_order
                )].compute()

                arr = to_xyz(arr, ch.data.axes_order)
                arr = arr.astype(np.float32) / max_val
                histogram = np.histogram(arr, bins=NR_HIST_BINS, range=(0.0, 1.0))[0]
                histogram[0] = 0
                np.savez(histfname, data=histogram, data_max=np.array(max_val, dtype=np.float64), allow_pickle=False)
                log(f"write vdb {vdbfname.name}")
                self.make_vdb(vdbfname, arr)
        return []

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
                with np.load(histfname, allow_pickle=False) as histfile:
                    hist += histfile["data"]
                    if "data_max" in histfile:
                        data_max = float(histfile["data_max"].item())
                    else:
                        with np.load(histfname, allow_pickle=True) as legacy_histfile:
                            data_max = legacy_histfile["metadata"].item()["data_max"]
            except Exception as e:
                print(e, " in reading histogram, skipping chunk")
                hist += np.zeros(NR_HIST_BINS)
        if not np.any(hist):
            return {"range": (0, 1), "vdb_min": 0, "vdb_max": 1, "histogram": np.zeros(NR_HIST_BINS), "threshold": 0, "threshold_upper": 1.0}

        r0, r1 = get_leading_trailing_zero_float(hist)
        cropped = hist[int(r0 * NR_HIST_BINS): int(r1 * NR_HIST_BINS)]
        nonzero_bins = np.flatnonzero(cropped > 0)
        if len(nonzero_bins) ==1:
            return {
                "range": (r0, r1),
                "vdb_min": r0,
                "vdb_max": r1,
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
