import bpy
import pytest
import zarr

from microscopynodes.ui.preferences import addon_preferences


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


def level(path, shape, scale):
    return path, shape, [{"type": "scale", "scale": scale}]


def level_0_6(path, transformations, output):
    transform = transformations[0]
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
    assert [(option.xy_size, option.z_size) for option in scene.MiN_array_options] == [(0.5, 2.0), (1.0, 2.0)]
    assert (scene.MiN_xy_size, scene.MiN_z_size) == (1.0, 2.0), "the last level is selected by default"


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
    assert (scene.MiN_xy_size, scene.MiN_z_size) == (0.5, 2.0)


def test_zarr_xy_anisotropy_uses_x_size(tmp_path):
    levels = [
        level("0", (2, 8, 64, 64), [1, 2.0, 0.5, 0.25]),
        level("1", (2, 8, 32, 32), [1, 2.0, 1.0, 0.5]),
    ]
    scene = load(write_multiscale(tmp_path / "aniso.zarr", CZYX_AXES, levels))

    assert scene.MiN_array_options[0].xy_size == 0.25


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
    assert scene.MiN_xy_size == 0.5
