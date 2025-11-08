import bpy

def timesequence_action(holder_obj):
    action = bpy.data.actions.get(f"Time Sequence {holder.name}")
    if action is None:
        action = bpy.data.actions.new(f"Time Sequence {holder.name}")

    obj.animation_data_create()
    obj.animation_data.action = action 
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
        for fcurve in action.fcurves:
            # Match the target data path exactly or inside a nested property
            if fcurve.data_path == target_data_path or target_data_path in fcurve.data_path:
                keyframes.extend((kp.co.x, kp.co.y) for kp in fcurve.keyframe_points)

    return keyframes

def clear_keyframes(obj, data_path):
    anim_data = obj.animation_data
    if not anim_data or not anim_data.action:
        return

    action = anim_data.action
    fcurves = [fc for fc in action.fcurves if fc.data_path == data_path]

    for fc in fcurves:
        action.fcurves.remove(fc)
