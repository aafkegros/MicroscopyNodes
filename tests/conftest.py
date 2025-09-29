import pytest
import bpy
import microscopynodes
import shutil, os
import gc, time

microscopynodes._test_register()

@pytest.hookimpl(trylast=True)
def pytest_sessionfinish(session, exitstatus):
    import microscopynodes
    # regrettably necessary, pytest segfaults if properties
    # with callback functions stay alive

    UPDATE_PROPS = [
        'MiN_input_file',
        'MiN_axes_order',
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
    test_folder = os.path.join(os.path.dirname(os.path.realpath(__file__)), "tmp_test_data")
    if os.path.isdir(test_folder):
        gc.collect()
        time.sleep(0.1)  # give Windows a moment
        shutil.rmtree(test_folder, ignore_errors=True)
    # print(f'called session finish, {deleted} properties deleted')
    # raise ValueError