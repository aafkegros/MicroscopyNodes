import bpy

def set_linear_keyframes(obj, data_path, start_frame, end_frame, start_value, end_value):
    # Set initial value
    setattr(obj, data_path, start_value)
    obj.keyframe_insert(data_path=data_path, frame=start_frame)

    # Set final value
    setattr(obj, data_path, end_value)
    obj.keyframe_insert(data_path=data_path, frame=end_frame)

    # Make interpolation linear
    fcurve = obj.animation_data.action.fcurves.find(data_path)
    if fcurve:
        for keyframe in fcurve.keyframe_points:
            keyframe.interpolation = 'LINEAR'

def get_keyframes(obj, data_path):
    anim_data = obj.animation_data
    if not anim_data or not anim_data.action:
        return []

    fcurve = anim_data.action.fcurves.find(data_path)
    if not fcurve:
        return []

    return [(kp.co.x, kp.co.y) for kp in fcurve.keyframe_points]  # (frame, value)

import bpy

def clear_keyframes(obj, data_path):
    anim_data = obj.animation_data
    if not anim_data or not anim_data.action:
        return

    action = anim_data.action
    fcurves = [fc for fc in action.fcurves if fc.data_path == data_path]

    for fc in fcurves:
        action.fcurves.remove(fc)
