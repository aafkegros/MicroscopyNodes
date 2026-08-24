import sys
from pathlib import Path

import numpy as np
import pytest

from microscopynodes.data_model import (
    ChannelDataModel,
    ChannelModel,
    ChannelVizModel,
    DatasetModel,
    FORBIDDEN_CHANNEL_NAME_CHARACTERS,
    sanitize_channel_name,
)
from microscopynodes.handle_blender_structs.min_keys import min_keys
from microscopynodes.handle_blender_structs.progress_handling import set_progress_path
from microscopynodes.io.local_file_process import LocalFileProcess
from microscopynodes.io.local_file_worker import main as run_local_file_worker


@pytest.mark.parametrize(
    ("axes_order", "source_axes_order"),
    [
        ("", None),
        ("xxz", None),
        ("xyq", None),
        ("xyz", "zyx"),
        ("xyz", "ccxyz"),
    ],
)
def test_channel_data_rejects_invalid_axis_orders(axes_order, source_axes_order):
    with pytest.raises(ValueError):
        ChannelDataModel(
            dataset_resolution=0,
            ix=0,
            axes_order=axes_order,
            source_axes_order=source_axes_order,
            source="unused.tif",
            unit="MICROMETER",
        )


def test_source_axis_channel_is_removed_from_data_axes():
    channel_data = ChannelDataModel(
        dataset_resolution=0,
        ix=0,
        axes_order="zyx",
        source_axes_order="czyx",
        source="unused.tif",
        unit="MICROMETER",
    )

    assert channel_data.source_axes_order.replace("c", "") == channel_data.axes_order


@pytest.mark.parametrize("character", FORBIDDEN_CHANNEL_NAME_CHARACTERS)
def test_channel_viz_rejects_names_with_invalid_blender_bundle_keys(character):
    with pytest.raises(ValueError, match="Channel names cannot contain"):
        ChannelVizModel(name=f"Channel {character}0")


def test_channel_name_sanitizer_replaces_invalid_blender_bundle_keys():
    invalid_name = "Channel" + "".join(FORBIDDEN_CHANNEL_NAME_CHARACTERS)

    assert sanitize_channel_name(invalid_name) == "Channel" + "_" * len(
        FORBIDDEN_CHANNEL_NAME_CHARACTERS
    )


def test_dataset_model_round_trips_generated_files_and_file_backed_mask(tmp_path):
    channel = ChannelModel(
        cache_path=str(tmp_path),
        data=ChannelDataModel(
            dataset_resolution=0,
            ix=0,
            axes_order="xyz",
            source_axes_order="xyz",
            source="input.tif",
            unit="MICROMETER",
        ),
        viz=ChannelVizModel(ix=0, volume=True),
    )
    mask = np.zeros((2, 3, 4), dtype=bool)
    mask[1, 2, 3] = True
    channel.store_mask(mask)

    volume_files = channel.files_for(min_keys.VOLUME)
    volume_files.constructors = [{"template_str": "cache/{t}.vdb", "t": 0}]
    volume_files.metadata = {
        "histogram": np.array([0, 2, 1]),
        "threshold": np.float64(0.25),
    }
    dataset = DatasetModel(name="round trip", channels=[channel])

    restored = DatasetModel.model_validate_json(dataset.model_dump_json())

    assert restored.local_files_exist
    assert restored.channels[0].files_for(min_keys.VOLUME).constructors == volume_files.constructors
    assert restored.channels[0].files_for(min_keys.VOLUME).metadata == {
        "histogram": [0, 2, 1],
        "threshold": 0.25,
    }
    assert restored.channels[0].viz.cmap.name == channel.viz.cmap.name
    assert restored.channels[0].viz.cmap.color_stops == channel.viz.cmap.color_stops
    assert np.array_equal(restored.channels[0].data.mask, mask)


def test_local_file_worker_round_trips_a_json_job(tmp_path, monkeypatch):
    channel = ChannelModel(
        cache_path=str(tmp_path / "cache"),
        data=ChannelDataModel(
            dataset_resolution=0,
            ix=0,
            axes_order="xyz",
            source_axes_order="xyz",
            source="unused.tif",
            unit="MICROMETER",
        ),
        viz=ChannelVizModel(
            ix=0,
            volume=False,
            surface=False,
            labelmask=False,
        ),
    )
    dataset = DatasetModel(name="worker round trip", channels=[channel])
    job_dir = tmp_path / "job"
    job_dir.mkdir()
    (job_dir / "request.json").write_text(dataset.model_dump_json(), encoding="utf-8")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "blender",
            "--",
            "--job-dir",
            str(job_dir),
            "--package",
            "microscopynodes",
        ],
    )

    run_local_file_worker()
    set_progress_path(None)

    restored = DatasetModel.model_validate_json(
        (job_dir / "result.json").read_text(encoding="utf-8")
    )
    assert restored.name == dataset.name
    assert restored.local_files_exist


def test_local_file_process_owns_command_protocol_and_cleanup(tmp_path, monkeypatch):
    channel = ChannelModel(
        cache_path=str(tmp_path / "cache"),
        data=ChannelDataModel(
            dataset_resolution=0,
            ix=0,
            axes_order="xyz",
            source_axes_order="xyz",
            source="unused.tif",
            unit="MICROMETER",
        ),
        viz=ChannelVizModel(
            ix=0,
            volume=False,
            surface=False,
            labelmask=False,
        ),
    )
    dataset = DatasetModel(name="controller round trip", channels=[channel])
    launched = {}

    class CompletedProcess:
        returncode = 0

        def poll(self):
            return self.returncode

    def fake_popen(command, stdout, stderr):
        launched["command"] = command
        job_dir = Path(command[command.index("--job-dir") + 1])
        request = job_dir / "request.json"
        (job_dir / "result.json").write_text(
            request.read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        (job_dir / "progress.txt").write_text("working", encoding="utf-8")
        return CompletedProcess()

    monkeypatch.setattr(
        "microscopynodes.io.local_file_process.subprocess.Popen",
        fake_popen,
    )

    controller = LocalFileProcess(dataset, "/path/to/blender", "microscopynodes")
    job_dir = controller.job_dir

    assert launched["command"][0] == "/path/to/blender"
    assert "--background" in launched["command"]
    assert controller.progress() == "working"
    assert controller.result().name == dataset.name

    controller.close()
    assert not job_dir.exists()
