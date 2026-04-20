from .import_microscopy_volume import import_microscopy_volume_node_group


NODE_GROUPS = {
    "Import Microscopy Volume": import_microscopy_volume_node_group,
}


def geometry_node_group(name):
    builder = NODE_GROUPS.get(name)
    if builder is None:
        return None
    return builder()
