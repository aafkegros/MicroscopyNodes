from pathlib import Path

import bpy
import dask.array as da
import numpy as np
import pytest
import yaml

import microscopynodes
from microscopynodes.data_model import ChannelModel, DatasetModel
from microscopynodes.handle_blender_structs.props import min_keys

from ..utils import prep_load


def _set_import_scale(scale_name):
    pref_path = Path(bpy.context.scene.MiN_yaml_preferences)
    with open(pref_path) as f:
        prefs = yaml.safe_load(f)
    prefs["import_scale"] = scale_name
    with open(pref_path, "w") as f:
        yaml.safe_dump(prefs, f)


def _make_channel(name="Channel 0", affine=None):
    if affine is None:
        affine = np.eye(4).tolist()
    return ChannelModel(
        name=name,
        dataset_resolution=0,
        cache_path="/tmp/example",
        ix=0,
        data=da.zeros((4, 6, 8), dtype=np.uint16),
        axes_order="xyz",
        affine=affine,
        unit=1e-6,
        visible_as={
            min_keys.VOLUME: True,
            min_keys.SURFACE: False,
            min_keys.LABELMASK: False,
        },
        emission=True,
        cmap=[(1.0, 1.0, 1.0, 1.0)],
        source="test",
        surf_resolution=0,
    )


def test_parse_default_scale_mode_uses_pixel_unit_label():
    prep_load("5D_5cube")
    _set_import_scale("DEFAULT")

    dataset_model = microscopynodes.parse_inputs.parse_blender_ui()

    assert dataset_model.explicit_scale == pytest.approx(1e-2)
    assert dataset_model.unit_label == "px"
    assert dataset_model.channels[0].affine[0][0] == pytest.approx(1.0)
    assert dataset_model.channels[0].affine[1][1] == pytest.approx(1.0)


def test_parse_physical_scale_mode_uses_physical_unit_label():
    prep_load("5D_5cube")
    _set_import_scale("MICROMETER_SCALE")

    dataset_model = microscopynodes.parse_inputs.parse_blender_ui()

    assert dataset_model.explicit_scale is None
    assert dataset_model.output_unit == pytest.approx(1e-6)
    assert dataset_model.unit_label == "µm"


def test_dataset_bbox_and_center_properties():
    dataset_model = DatasetModel(
        name="bbox-test",
        channels=[_make_channel()],
        output_unit=1e-6,
        relative_loc=(-0.5, -0.5, 0.0),
    )

    mins, maxs, extent = dataset_model.intermediate_bbox
    final_mins, final_maxs, final_extent = dataset_model.final_bbox
    final_center = dataset_model.final_center

    np.testing.assert_allclose(mins, np.array([0.0, 0.0, 0.0]))
    np.testing.assert_allclose(maxs, np.array([4.0, 6.0, 8.0]))
    np.testing.assert_allclose(extent, np.array([4.0, 6.0, 8.0]))
    np.testing.assert_allclose(final_mins, np.array([0.0, 0.0, 0.0]))
    np.testing.assert_allclose(final_maxs, np.array([4.0, 6.0, 8.0]))
    np.testing.assert_allclose(final_extent, np.array([4.0, 6.0, 8.0]))
    np.testing.assert_allclose(final_center, np.array([0.0, 0.0, 4.0]))
