try:
    from . import ops
    from . import channel_list
    from . import panel
    from . import preferences
except Exception as e:
    print(e)
    raise(e)

CLASSES = ops.CLASSES + channel_list.CLASSES + panel.CLASSES + preferences.CLASSES
