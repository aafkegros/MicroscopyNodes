from pathlib import Path

import bpy
import dask.array as da
import numpy as np
import pytest
import json
from cmap import Colormap

import microscopynodes
from microscopynodes.data_model import ChannelModel, DatasetModel

from ..utils import prep_load


def _set_import_scale(scale_name):
    pref_path = Path(bpy.context.scene.MiN_json_preferences)
    with open(pref_path) as f:
        prefs = json.load(f)
    prefs["import_scale"] = scale_name
    with open(pref_path, "w") as f:
        json.dump(prefs, f)


def _make_channel(name="Channel 0", affine=None):
    if affine is None:
        affine = np.eye(4).tolist()
    return ChannelModel(
        name=name,
        cache_path="/tmp/example",
        data={
            "dataset_resolution": 0,
            "ix": 0,
            "data": da.zeros((4, 6, 8), dtype=np.uint16),
            "axes_order": "xyz",
            "affine": affine,
            "unit": 1e-6,
            "source": "test",
        },
        viz={
            "volume": True,
            "surface": False,
            "labelmask": False,
            "emission": True,
            "cmap": Colormap([(1.0, 1.0, 1.0, 1.0)]),
            "surf_resolution": 0,
        },
    )


def test_parse_default_scale_mode_uses_pixel_unit_label():
    prep_load("5D_5cube")
    _set_import_scale("DEFAULT")

    dataset_model = microscopynodes.parse_inputs.parse_blender_ui()

    assert dataset_model.explicit_scale == pytest.approx(1e-2)
    assert dataset_model.unit_label == "px"
    assert dataset_model.channels[0].data.affine[0][0] == pytest.approx(1.0)
    assert dataset_model.channels[0].data.affine[1][1] == pytest.approx(1.0)


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
    np.testing.assert_allclose(mins, np.array([0.0, 0.0, 0.0]))
    np.testing.assert_allclose(maxs, np.array([4.0, 6.0, 8.0]))
    np.testing.assert_allclose(extent, np.array([4.0, 6.0, 8.0]))
    np.testing.assert_allclose(dataset_model.dataset_origin_world, np.array([-2.0, -3.0, 0.0]))
    np.testing.assert_allclose(dataset_model.dataset_center_world, np.array([0.0, 0.0, 4.0]))
