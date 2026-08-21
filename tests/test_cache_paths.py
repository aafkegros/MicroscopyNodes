from types import SimpleNamespace

from microscopynodes.blender_objects.base import ChannelObject


class ImportObject:
    def update_import_affine(self, import_node, channel):
        pass


def _cache_dir_written_to_import_node(cache_dir):
    socket = SimpleNamespace(type="STRING", default_value=None)
    import_node = SimpleNamespace(
        inputs={"cache_dir": socket},
        label=None,
    )
    channel = SimpleNamespace(
        name="Channel 0",
    )
    constructor = {"cache_dir": cache_dir}

    ChannelObject.update_import_node(
        ImportObject(),
        import_node,
        [constructor],
        channel,
    )
    return socket.default_value, constructor


def test_project_root_cache_dir_is_stored_as_blender_relative(monkeypatch):
    monkeypatch.setattr(
        "microscopynodes.blender_objects.base.bpy.path.relpath",
        lambda path: "//." if path == "/project" else "//../cache",
    )
    value, constructor = _cache_dir_written_to_import_node("/project")

    assert value == "/"
    assert constructor["cache_dir"] == "/project"


def test_non_project_cache_dir_remains_absolute(monkeypatch):
    monkeypatch.setattr(
        "microscopynodes.blender_objects.base.bpy.path.relpath",
        lambda path: "//../cache",
    )
    value, _ = _cache_dir_written_to_import_node("/cache")

    assert value == "/cache"
