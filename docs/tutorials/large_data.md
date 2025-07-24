# Large data

Microscopy data is often very large, {{ svg("microscopy_nodes") }} Microscopy Nodes has some strategies to deal with this. These depend on the size of the data, the shape of the data, and your computational resources (and skills). The key of this is working at a smaller scale, and then **reloading** to larger data.

Here it is relevant to distinguish between two types of large data: 

- Time sequence/few channels (not loading all data in the same timeframe)
    
    > This mostly has issues in storage, and is more a point of only loading the data you need at a certain point, but will always just work.

- Large data that's all concurrently loaded
    
    > This becomes a bigger issue, especially with the current **4 GiB limit of EEVEE**.

!!! warning "EEVEE cannot handle large data" 
    EEVEE currently **cannot handle** [volumetric data over 4 GiB](https://projects.blender.org/blender/blender/issues/136263). This means that scaling up our data will be easier in Cycles. By default after loading, the render engine is set to Cycles. 
    
    **Cycles is only applied** to the view if the shading preview is set to {{ svg("shading_rendered", 'small-icon') }} Rendered preview.

There are a few strategies:

## Working at large scale

You can actually work at large scales, as long as you have enough and take care to work **only in Cycles**:

Some {{ svg("workspace") }} workspaces will **automatically** be in {{ svg("shading_texture") }} Material preview mode. It is convenient to first go through the different {{ svg("workspace") }} workspaces and switch them all to {{ svg("shading_rendered") }} Rendered preview.

## **Reloading**

The **reloading** workflow means that you first work on a smaller version of the data and later replace this with a larger one. 

This is controlled mainly by the {{ svg("file_refresh") }} Reload field in the {{ svg("microscopy_nodes") }} Microscopy Nodes load panel:
![alt text](<../figures/Screenshot 2025-07-24 at 10.45.50.png>)

This can be pointed to a previously loaded Microscopy Nodes [holder object](./3_objects.md#holder):
![alt text](<../figures/Screenshot 2025-07-24 at 10.45.36.png>)

Which will make a new action **Reload** the data in the holder. This has two extra options:

- {{ svg("file") }} Overwrite data
   
    > Changes out the underlying data (labelmasks are currently always regenerated)

- {{ svg("material") }} Overwrite settings
  
    > Overwrites all settings from the load panel, but retains anything set by the user, this includes input location/transform, emission, and color

For reloading to deal with large data, it is usually best to reload only updating {{ svg("file") }} the underlying data to the higher resolution.

### Reloading on workstation or cluster

It is possible to make a project on a less capable computer, and then transfer it to a workstation or an HPC cluster. This can be done in multiple ways:

- Transfering with data
  > Easiest to do with your data loaded 'With Project' in the [extra import settings](./2_loading_data.md#5-extra-import-settings-optional), then it is an easy matter of transferring the .blend file and the data folder next to it to this computer.
-  Reloading from a GUI
-  Reloading from the command line

### Reloading from the command line

To replace your data from the command line interface, you set up all the {{ svg("file_refresh") }} reloading and import settings in the GUI (this currently works best with {{ svg("material") }} Overwrite settings off) and run a headless python script that looks like this:
```
import bpy
bpy.ops.microscopynodes.load_background()
bpy.ops.wm.save_mainfile()
```
by running:
`/path/to/Blender/executable -b /path/to/blendfile.blend -P /path/to/reload_script.py`

This will then load the data according to the Microscopy Nodes settings, and resave the .blend file. 

You can subsequently render headlessly as well, here you can follow the {{ svg('blender') }} [Blender documentation on this](https://docs.blender.org/manual/en/latest/advanced/command_line/render.html).

