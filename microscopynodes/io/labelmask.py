import zmesh
from pathlib import Path

from .base import DataIO
from ..handle_blender_structs.array_handling import len_axis, take_index, to_xyz
from ..handle_blender_structs.progress_handling import log
from ..handle_blender_structs.min_keys import min_keys


class LabelmaskIO(DataIO):
    min_type = min_keys.LABELMASK
    MASK_TEMPLATE = Path("{cache_dir}") / "{dataset_hash}" / "{scale}" / "mask_{resolution}" / "c{channel_ix}_t{t}"

    def generate_file_constructors(self, ch):
        file_constructors = []
        for t in range(ch.data.frame_start, ch.data.frame_end + 1):
            if t >= len_axis("t", ch.data.axes_order, ch.data.data.shape):
                break
            file_constructors.append({
                **self.base_constructor(ch),
                "scale": ch.data.dataset_resolution,
                "resolution": ch.viz.surf_resolution,
                "t": t,
                "channel_ix": ch.data.ix,
                "template_str": str(self.MASK_TEMPLATE),
            })
        return file_constructors

    def export_ch(self, ch, file_constructors):
        mesher = zmesh.Mesher((1, 1, 1))
        for constructor in file_constructors:
            fname = Path(str(self.MASK_TEMPLATE).format(**constructor)).with_suffix(".obj")
            fname_ids = fname.with_suffix(".csv")
            fname.parent.mkdir(parents=True, exist_ok=True)

            if Path(fname).exists():
                if ch.force_remaking_files:
                    Path(fname).unlink()
                else:
                    continue
            with open(str(fname_ids), "ab+") as ofs:
                ofs.write("oid\n".encode("utf-8"))

            timeframe_arr = take_index(ch.data.data, constructor["t"], "t", ch.data.axes_order).compute()
            timeframe_arr = to_xyz(timeframe_arr, ch.data.axes_order.replace("t", ""))

            log(f"Meshing timepoint {constructor['t']}")
            mesher.mesh(timeframe_arr, close=True)

            vertex_offset = 0
            for obj_id in mesher.ids():
                log(f"Writing object {obj_id} at time {constructor['t']}")
                zmeshed = mesher.get(
                    obj_id,
                    normals=False,
                    reduction_factor=ch.viz.surf_resolution * 30,
                    max_error=ch.viz.surf_resolution * 3,
                    voxel_centered=False,
                )

                obj_str = f"\no {obj_id}\n"
                for v in zmeshed.vertices:
                    obj_str += "v {:.5f} {:.5f} {:.5f}\n".format(v[0] - 1, v[1] - 1, v[2] - 1)
                for f in zmeshed.faces:
                    obj_str += "f {} {} {}\n".format(*(i + 1 + vertex_offset for i in f))
                vertex_offset += len(zmeshed.vertices)
                with open(str(fname), "ab+") as ofs:
                    ofs.write(obj_str.encode("utf-8"))
                with open(str(fname_ids), "ab+") as ofs:
                    ofs.write(f"{obj_id}\n".encode("utf-8"))
                mesher.erase(obj_id)
            mesher.clear()
        return

    def get_metadata(self, file_constructors):
        files = [Path(str(self.MASK_TEMPLATE).format(**constructor)).with_suffix(".csv") for constructor in file_constructors]
        max_oid = max(
            (
                int(line)
                for filepath in files
                if filepath.exists()
                for i, line in enumerate(open(filepath))
                if i > 0
            ),
            default=0,
        )
        return {"max": max_oid}
