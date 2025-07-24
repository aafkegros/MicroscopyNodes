# Preferences / Customization

The {{ svg("microscopy_nodes") }} Microscopy Nodes addon has {{ svg("preferences") }} **Preferences** to allow for a custom experience and defaults. 

You can find these under `Edit > Preferences > Add-ons > Microscopy Nodes`.

![alt text](<../figures/Screenshot 2025-07-24 at 13.00.10.png>)

Here we get multiple options for defaults and settings:

- Default "Path"
  > The cache path that is set if the [load option](./2_loading_data.md#5-extra-import-settings-optional) `Path` is selected   
- Default "Temporary"
  > The cache path that is generated when [load option](./2_loading_data.md#5-extra-import-settings-optional) `Temporary` is selected   
- Default channels + channel number
  > This defines the default settings for the [channel interface](./2_loading_data.md#4-set-channels) when a new dataset is loaded. If more channels are present in the data than defaults, the list revolves. 
- Invert Color
  > Inverts all colormaps on load and replace
- Overwrite local files (debug)
  > If reloading fails for some reason, this is useful to check, but is usually only used for development.

   