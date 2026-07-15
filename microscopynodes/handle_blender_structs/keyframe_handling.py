import bpy


def action_fcurves(action):
    return getattr(action, "fcurves", ())


def timesequence_action(holder_obj):
    action = bpy.data.actions.get(f"Time Sequence {holder_obj.name}")
    if action is None:
        action = bpy.data.actions.new(f"Time Sequence {holder_obj.name}")

    holder_obj.animation_data_create()
    holder_obj.animation_data.action = action
    return action


def set_keyframes_in_action(action_name, obj, data_path, keyframes, group_name="Default"):
    # Get or create the Action
    action = bpy.data.actions.get(action_name)
    if action is None:
        action = bpy.data.actions.new(action_name)

    obj.animation_data_create()
    obj.animation_data.action = action 

    # Now it's safe to create or reuse the F-Curve
    fcurve = action.fcurve_ensure_for_datablock(
        obj,
        data_path=data_path,
        group_name=group_name
    )

    # Replace existing keyframes
    fcurve.keyframe_points.clear()
    for frame, value in keyframes:
        fcurve.keyframe_points.insert(frame=frame, value=value)

    for kp in fcurve.keyframe_points:
        kp.interpolation = 'LINEAR'

    return fcurve

def get_keyframes(obj, target_data_path):
    anim_data = getattr(obj, "animation_data", None)
    if not anim_data:
        return []

    all_actions = []
    if anim_data.action:
        all_actions.append(anim_data.action)
    if anim_data.nla_tracks:
        for track in anim_data.nla_tracks:
            for strip in track.strips:
                if strip.action:
                    all_actions.append(strip.action)

    keyframes = []
    for action in all_actions:
        for fcurve in action_fcurves(action):
            # Match the target data path exactly or inside a nested property
            if fcurve.data_path == target_data_path or target_data_path in fcurve.data_path:
                keyframes.extend((kp.co.x, kp.co.y) for kp in fcurve.keyframe_points)

    return keyframes

def clear_keyframes(obj, data_path):
    anim_data = getattr(obj, "animation_data", None)
    if not anim_data or not anim_data.action:
        return

    action = anim_data.action
    fcurves = [fc for fc in action_fcurves(action) if fc.data_path == data_path]

    for fc in fcurves:
        action.fcurves.remove(fc)


def dataset_frame_bounds(dataset_model):
    frame_starts = [ch.data.frame_start or 0 for ch in dataset_model.channels]
    frame_ends = [ch.data.frame_end or 0 for ch in dataset_model.channels]
    return min(frame_starts, default=0), max(frame_ends, default=0)


def holder_frame_socket(holder_obj):
    modifier = next(
        mod
        for mod in holder_obj.modifiers
        if mod.type == "NODES" and mod.node_group is not None
        and frame_socket_identifier(mod.node_group) is not None
    )
    socket_identifier = frame_socket_identifier(modifier.node_group)
    return modifier, getattr(modifier.properties.inputs, socket_identifier)


def holder_frame_data_path(holder_obj):
    modifier, _ = holder_frame_socket(holder_obj)
    socket_identifier = frame_socket_identifier(modifier.node_group)
    return f"{modifier.path_from_id()}.properties.inputs.{socket_identifier}.value"


def ensure_dataset_frame_animation(holder_obj, dataset_model):
    frame_start, frame_end = dataset_frame_bounds(dataset_model)
    frame_offset_end = max(frame_end - frame_start, 0)
    _, frame_socket = holder_frame_socket(holder_obj)
    data_path = holder_frame_data_path(holder_obj)

    clear_keyframes(holder_obj, data_path)

    if frame_offset_end <= 0:
        frame_socket.value = 0
        return data_path

    timesequence_action(holder_obj)
    frame_socket.value = 0
    holder_obj.keyframe_insert(data_path=data_path, frame=frame_start)
    frame_socket.value = frame_offset_end
    holder_obj.keyframe_insert(data_path=data_path, frame=frame_end)

    action = holder_obj.animation_data.action
    for fcurve in action_fcurves(action):
        if fcurve.data_path == data_path:
            for kp in fcurve.keyframe_points:
                kp.interpolation = 'LINEAR'
    return data_path


def frame_socket_identifier(node_group):
    for item in node_group.interface.items_tree:
        if (
            getattr(item, "item_type", None) == 'SOCKET'
            and getattr(item, "in_out", None) == 'INPUT'
            and item.name == "Frame"
        ):
            return item.identifier
    return None


def drive_modifier_frame_from_holder(modifier, holder_obj, socket_identifier):
    data_path = f"properties.inputs.{socket_identifier}.value"
    try:
        modifier.driver_remove(data_path)
    except (TypeError, RuntimeError):
        pass

    fcurve = modifier.driver_add(data_path)
    driver = fcurve.driver
    driver.type = "SCRIPTED"
    driver.expression = "frame"
    while driver.variables:
        driver.variables.remove(driver.variables[0])

    var = driver.variables.new()
    var.name = "frame"
    var.targets[0].id = holder_obj
    var.targets[0].data_path = holder_frame_data_path(holder_obj)
    return fcurve


def ensure_dataset_frame_driver(holder_obj, min_obj):
    modifier = min_obj.min_gn
    node_group = min_obj.node_group
    if modifier is None or node_group is None:
        return None

    socket_identifier = frame_socket_identifier(node_group)
    if socket_identifier is None:
        return None

    return drive_modifier_frame_from_holder(modifier, holder_obj, socket_identifier)
