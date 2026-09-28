import numpy as np
import tifffile
import bpy

from microscopynodes.file_to_array import gui_adapter


def test_invalid_source_axes_can_be_corrected_in_scene(tmp_path, monkeypatch):
    path = tmp_path / "invalid_axes.tif"
    tifffile.imwrite(path, np.zeros((3, 4, 5), dtype=np.uint8), photometric="minisblack")
    original_metadata = gui_adapter.TifLoader.metadata

    def invalid_metadata(loader, input_file):
        return {**original_metadata(loader, input_file), "axes_order": "zyy"}

    monkeypatch.setattr(gui_adapter.TifLoader, "metadata", invalid_metadata)
    scene = bpy.context.scene
    scene.MiN_input_file = str(path)
    assert scene.MiN_axes_order == "zyy"
    assert not scene.MiN_enable_ui

    # Neither edit moves a channel axis: both must still trigger validation.
    scene.MiN_axes_order = "zyq"
    assert not scene.MiN_enable_ui
    assert not scene.get("_MiN_syncing_input_file")

    scene.MiN_axes_order = "zyx"
    assert scene.MiN_enable_ui
    assert len(scene.MiN_array_options) > 0
    assert gui_adapter.selected_dataset_model().channels[0].data.axes_order == "zyx"

    scene.MiN_axes_order = "zyy"
    assert not scene.MiN_enable_ui
    scene.MiN_axes_order = "xyz"
    assert scene.MiN_enable_ui
    assert gui_adapter.selected_dataset_model().channels[0].data.axes_order == "xyz"
