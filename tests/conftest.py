import pytest
import bpy
import microscopynodes

microscopynodes._test_register()

@pytest.hookimpl(trylast=True)
def pytest_sessionfinish(session, exitstatus):
    import microscopynodes
    # regrettably necessary, pytest segfaults if properties
    # with callback functions stay alive

    UPDATE_PROPS = [
        'MiN_input_file',
        'MiN_explicit_cache_dir',
        'MiN_selected_cache_option',
        'MiN_axes_order',
        'MiN_selected_zarr_level',
        'MiN_channel_nr',
        'MiN_reload',
    ]
    deleted = 0
    for prop in UPDATE_PROPS:
        try:
            delattr(bpy.types.Scene, prop)
            deleted += 1
        except:
            print(f"{prop} not found")

    microscopynodes.unregister()
    print(f'called session finish, {deleted} properties deleted')
    # raise ValueError