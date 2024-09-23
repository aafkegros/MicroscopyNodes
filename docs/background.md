# Replace data in background

Blender can run and render as a background job without a UI. This is very advantageous if you have very large pyramidal stack sizes you want to render your data at, and access to some form of HPC cluster. 
To replace your data with a different size, you set up all the [Microscopy Nodes settings](./settings.md) to [reload](./settings.md#reload) at the right scale, and run a headless python script that looks like this:
```
import bpy
bpy.ops.microscopynodes.load_background()
bpy.ops.wm.save_mainfile()
```
by running:
`/path/to/Blender/executable -b /path/to/blendfile.blend -P /path/to/reload_script.py`

This will then load the data according to the Microscopy Nodes settings, and resave the .blend file. 

You can subsequently render headlessly as well, here you can follow the [Blender documentation on this](https://docs.blender.org/manual/en/latest/advanced/command_line/render.html).