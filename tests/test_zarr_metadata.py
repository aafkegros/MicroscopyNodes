import bpy
import numpy as np
import pytest
import zarr
from mathutils import Vector

from microscopynodes.blender_state import Dataset
from microscopynodes.ui.gui_to_data_model import parse_channellist
from microscopynodes.ui.preferences import addon_preferences

from .utils import do_load, prep_load


@pytest.fixture(autouse=True)
def default_channel_preferences():
    prefs = addon_preferences(bpy.context)
    if len(prefs.channels) == 0:
        prefs.set_channels(bpy.context)


def axis(name, kind="space", unit=None):
    metadata = {"name": name, "type": kind}
    if unit is not None:
        metadata["unit"] = unit
    return metadata


ZYX_AXES = [axis(name, unit="micrometer") for name in "zyx"]
CZYX_AXES = [axis("c", "channel"), *ZYX_AXES]


def level(path, shape, scale, translation=None):
    transformations = [{"type": "scale", "scale": scale}]
    if translation is not None:
        transformations.append({"type": "translation", "translation": translation})
    return path, shape, transformations


def level_0_6(path, transformations, output):
    transform = transformations[0]
    if len(transformations) > 1:
        transform = {"type": "sequence", "transformations": transformations}
    return {
        "path": path,
        "coordinateTransformations": [
            {**transform, "input": {"path": path}, "output": {"name": output}},
        ],
    }


def write_multiscale(
    path, axes, levels, *, version="0.4", omero=None, additional_systems=(), additional_transformations=()
):
    if version == "0.6":
        output = "physical"
        multiscale = {
            "coordinateSystems": [{"name": output, "axes": axes}, *additional_systems],
            "datasets": [level_0_6(key, transforms, output) for key, _, transforms in levels],
        }
        if additional_transformations:
            multiscale["coordinateTransformations"] = additional_transformations
    else:
        multiscale = {
            "axes": axes,
            "datasets": [{"path": key, "coordinateTransformations": transforms} for key, _, transforms in levels],
        }

    metadata = {"multiscales": [multiscale]}
    if omero is not None:
        metadata["omero"] = omero
    if version == "0.4":
        multiscale["version"] = version
        attrs = metadata
    else:
        attrs = {"ome": {"version": version, **metadata}}

    group = zarr.open_group(path, mode="w", zarr_format=2 if version == "0.4" else 3)
    for key, shape, _ in levels:
        group.create_array(key, shape=shape, dtype="uint16", chunks=shape)
    group.attrs.update(attrs)
    return path


def load(path):
    scene = bpy.context.scene
    scene.MiN_input_file = str(path)
    return scene


def imported_affine():
    return parse_channellist()[0].data.affine_matrix


@pytest.mark.parametrize("version", ["0.4", "0.5"])
def test_zarr_scales_unit_and_channel_names(tmp_path, version):
    window = {"min": 0, "max": 65535, "start": 0, "end": 65535}
    omero = {
        "channels": [
            {"label": "DAPI", "color": "0000FF", "window": window},
            {"label": "GFP", "color": "00FF00", "window": window},
        ],
    }
    levels = [
        level("0", (2, 8, 64, 64), [1, 2.0, 0.5, 0.5]),
        level("1", (2, 8, 32, 32), [1, 2.0, 1.0, 1.0]),
    ]
    scene = load(write_multiscale(tmp_path / "image.zarr", CZYX_AXES, levels, version=version, omero=omero))

    assert scene.MiN_enable_ui
    assert scene.MiN_axes_order == "czyx"
    assert scene.MiN_unit == "MICROMETER"
    assert [channel.name for channel in scene.MiN_channelList] == ["DAPI", "GFP"]
    assert [(option.x_size, option.z_size) for option in scene.MiN_array_options] == [(0.5, 2.0), (1.0, 2.0)]
    assert (scene.MiN_x_size, scene.MiN_z_size) == (1.0, 2.0), "the last level is selected by default"
    assert scene.MiN_y_size == 1.0
    scene.MiN_x_size = 0.75
    assert imported_affine().diagonal()[:3] == pytest.approx([0.75, 1.0, 2.0])
    scene.MiN_ui_xy_size = 0.75
    assert imported_affine().diagonal()[:3] == pytest.approx([0.75, 0.75, 2.0])


def test_zarr_0_6_multiscale_loads(tmp_path):
    path = write_multiscale(
        tmp_path / "v06.zarr",
        ZYX_AXES,
        [level("s0", (8, 64, 64), [2.0, 0.5, 0.5])],
        version="0.6",
        additional_systems=[{"name": "stage", "axes": ZYX_AXES}],
        additional_transformations=[
            {
                "type": "translation",
                "input": {"name": "physical"},
                "output": {"name": "stage"},
                "translation": [100.0, 250.0, 250.0],
            },
        ],
    )
    scene = load(path)

    assert scene.MiN_enable_ui
    assert scene.MiN_axes_order == "zyx"
    assert (scene.MiN_x_size, scene.MiN_z_size) == (0.5, 2.0)


@pytest.mark.parametrize("version", ["0.4", "0.6"])
def test_zarr_anisotropic_xy_pixel_sizes(tmp_path, version):
    levels = [
        level("0", (2, 8, 64, 64), [1, 2.0, 0.5, 0.25]),
        level("1", (2, 8, 32, 32), [1, 2.0, 1.0, 0.5]),
    ]
    scene = load(write_multiscale(tmp_path / "aniso.zarr", CZYX_AXES, levels, version=version))

    assert [(option.x_size, option.y_size) for option in scene.MiN_array_options] == [(0.25, 0.5), (0.5, 1.0)]
    assert scene.MiN_y_size == pytest.approx(1.0)
    assert imported_affine().diagonal()[:3] == pytest.approx([0.5, 1.0, 2.0]), "x, y and z of the selected level"

    scene.MiN_x_size = 0.1
    assert imported_affine().diagonal()[:3] == pytest.approx([0.1, 1.0, 2.0])
    scene.MiN_y_size = 0.8
    assert imported_affine().diagonal()[:3] == pytest.approx([0.1, 0.8, 2.0])

    scene.MiN_selected_array_option = "0"
    assert imported_affine().diagonal()[:3] == pytest.approx([0.25, 0.5, 2.0])


def test_zarr_anisotropic_dataset_has_physical_extents(tmp_path):
    prep_load()
    levels = [level("0", (8, 16, 16), [1.0, 2.0, 0.5])]
    load(write_multiscale(tmp_path / "aniso.zarr", ZYX_AXES, levels))
    do_load()

    holder = Dataset(holder=bpy.context.scene.MiN_reload).holder
    assert holder.dataset_extents == pytest.approx([16 * 0.5, 16 * 2.0, 8 * 1.0])


@pytest.mark.parametrize("version", ["0.4", "0.6"])
def test_zarr_space_axes_in_different_units_are_converted(tmp_path, version):
    axes = [axis("z", unit="micrometer"), axis("y", unit="nanometer"), axis("x", unit="nanometer")]
    levels = [level("0", (4, 8, 8), [2.0, 500.0, 250.0])]
    scene = load(write_multiscale(tmp_path / "mixed_units.zarr", axes, levels, version=version))

    assert scene.MiN_unit == "MICROMETER", "the unit of the first space axis"
    assert (scene.MiN_x_size, scene.MiN_y_size, scene.MiN_z_size) == pytest.approx((0.25, 0.5, 2.0))


def test_zarr_space_axes_with_unspecified_unit_are_not_converted(tmp_path):
    axes = [axis("z", unit="micrometer"), axis("y"), axis("x", unit="micrometer")]
    levels = [level("0", (4, 8, 8), [2.0, 0.5, 0.25])]
    scene = load(write_multiscale(tmp_path / "unspecified_unit.zarr", axes, levels))

    assert scene.MiN_enable_ui
    assert scene.MiN_unit == "MICROMETER"
    assert (scene.MiN_x_size, scene.MiN_y_size, scene.MiN_z_size) == pytest.approx((0.25, 0.5, 2.0))


@pytest.mark.parametrize("version", ["0.4", "0.6"])
def test_zarr_each_level_keeps_its_own_translation(tmp_path, version):
    levels = [
        level("0", (4, 16, 16), [1.0, 0.5, 0.5], translation=[10.0, 20.0, 30.0]),
        level("1", (4, 8, 8), [1.0, 1.0, 1.0], translation=[10.0, 20.25, 30.25]),
    ]
    scene = load(write_multiscale(tmp_path / "translated.zarr", ZYX_AXES, levels, version=version))

    scene.MiN_x_size = 0.75
    affine = imported_affine()
    assert affine.diagonal()[:3] == pytest.approx([0.75, 1.0, 1.0])
    assert affine[:3, 3] == pytest.approx([30.25, 20.25, 10.0])

    scene.MiN_selected_array_option = "0"
    assert imported_affine()[:3, 3] == pytest.approx([30.0, 20.0, 10.0])


def surface_center_and_size(path, level):
    prep_load()
    scene = load(path)
    scene.MiN_selected_array_option = str(scene.MiN_array_options[level].identifier)
    for channel in scene.MiN_channelList:
        channel.surface = True
    do_load()
    surface = Dataset(holder=bpy.context.scene.MiN_reload).surface.object
    depsgraph = bpy.context.evaluated_depsgraph_get()
    corners = np.array([surface.matrix_world @ Vector(corner) for corner in surface.evaluated_get(depsgraph).bound_box])
    return (corners.min(axis=0) + corners.max(axis=0)) / 2, corners.max(axis=0) - corners.min(axis=0)


def test_zarr_levels_line_up_with_translation(tmp_path):
    # Pixel centers are at index * scale + translation, so a block of 8 pixels at level 0 covers the same space as the
    # block of 4 pixels of the 2x coarser level 1, whose first pixel center lies half a level 0 pixel further.
    # Only the centers are compared: where the surface is drawn around the block depends on the pixel size.
    levels = [
        level("0", (16, 16, 16), [1.0, 1.0, 1.0], translation=[0.0, 0.0, 0.0]),
        level("1", (8, 8, 8), [2.0, 2.0, 2.0], translation=[0.5, 0.5, 0.5]),
    ]
    path = write_multiscale(tmp_path / "pyramid.zarr", ZYX_AXES, levels)
    group = zarr.open_group(path, mode="a")
    group["0"][4:12, 4:12, 4:12] = 60000
    group["1"][2:6, 2:6, 2:6] = 60000

    center0, size0 = surface_center_and_size(path, level=0)
    center1, size1 = surface_center_and_size(path, level=1)

    assert np.all(size0 > 0.1) and np.all(size1 > 0.1), "the surfaces exist"
    assert center1 == pytest.approx(center0, abs=2e-3)


def test_zarr_with_invalid_axis_order_is_rejected(tmp_path):
    axes = [axis("t", "time", "second"), axis("z"), axis("c", "channel"), axis("y"), axis("x")]
    levels = [level("0", (2, 3, 2, 8, 8), [1.0] * 5)]
    scene = load(write_multiscale(tmp_path / "tzcyx.zarr", axes, levels))

    assert not scene.MiN_enable_ui
    assert len(scene.MiN_array_options) == 0
    assert scene.MiN_progress_str.startswith("Found invalid or unsupported OME-Zarr")


def test_zarr_scene_group_points_to_its_images(tmp_path):
    import clearscale as cs

    def tile():
        return cs.Multiscale.from_single(cs.Scale(shape=cs.Shape(y=16, x=16), pixel_size=cs.PixelSize(y=0.5, x=0.5)))

    tile1, tile2 = tile(), tile()
    scene_metadata = cs.Scene.from_shared_coordinate_system(
        coordinate_system="stage",
        connections=[
            cs.Scene.Connection(tile1, to_shared=cs.Translation(y=0.0, x=0.0), path="tiles/t1"),
            cs.Scene.Connection(tile2, to_shared=cs.Translation(y=0.0, x=8.0), path="tiles/t2"),
        ],
    )
    root = zarr.open_group(tmp_path / "scene.zarr", mode="w", zarr_format=3)
    root.attrs.update(cs.OmeZarrGroup.from_single(scene_metadata).to_attrs(version="0.6"))
    for child_path, child in scene_metadata.multiscale_paths.items():
        child_group = root.require_group(child_path)
        child_group.attrs.update(cs.OmeZarrGroup.from_single(child).to_attrs(version="0.6"))
        for key in child:
            child_group.create_array(key, shape=(16, 16), dtype="uint16", chunks=(16, 16))

    scene = load(tmp_path / "scene.zarr")
    assert not scene.MiN_enable_ui
    assert "tiles/t1" in scene.MiN_progress_str

    scene = load(tmp_path / "scene.zarr" / "tiles" / "t1")
    assert scene.MiN_enable_ui
    assert scene.MiN_axes_order == "yx"
    assert scene.MiN_x_size == 0.5
